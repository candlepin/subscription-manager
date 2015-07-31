#
# Registration dialog/wizard
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import gettext
import logging
import Queue
import re
import socket
import sys
import threading

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.ga import GObject as ga_GObject

import rhsm.config as config
from rhsm.utils import ServerUrlParseError
from rhsm.connection import GoneException

from subscription_manager.branding import get_branding
from subscription_manager.action_client import ActionClient
from subscription_manager.gui import networkConfig
from subscription_manager.gui import widgets
from subscription_manager.injection import IDENTITY, PLUGIN_MANAGER, require, \
        INSTALLED_PRODUCTS_MANAGER, PROFILE_MANAGER
from subscription_manager import managerlib
from subscription_manager.utils import is_valid_server_info, MissingCaCertException, \
        parse_server_info, restart_virt_who

from subscription_manager.gui.utils import format_exception, show_error_window
from subscription_manager.gui.autobind import DryRunResult, \
        ServiceLevelNotSupportedException, AllProductsCoveredException, \
        NoProductsException
from subscription_manager.jsonwrapper import PoolWrapper

_ = lambda x: gettext.ldgettext("rhsm", x)

gettext.textdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)

CFG = config.initConfig()

REGISTERING = 0
SUBSCRIBING = 1
state = REGISTERING


def get_state():
    global state
    return state


def set_state(new_state):
    global state
    state = new_state

ERROR_SCREEN = -3
DONT_CHANGE = -2
PROGRESS_PAGE = -1
CHOOSE_SERVER_PAGE = 0
ACTIVATION_KEY_PAGE = 1
CREDENTIALS_PAGE = 2
OWNER_SELECT_PAGE = 3
ENVIRONMENT_SELECT_PAGE = 4
PERFORM_REGISTER_PAGE = 5
SELECT_SLA_PAGE = 6
CONFIRM_SUBS_PAGE = 7
PERFORM_SUBSCRIBE_PAGE = 8
REFRESH_SUBSCRIPTIONS_PAGE = 9
INFO_PAGE = 10
DONE_PAGE = 11
FINISH = 100

REGISTER_ERROR = _("<b>Unable to register the system.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")


# from old smolt code.. Force glibc to call res_init()
# to rest the resolv configuration, including reloading
# resolv.conf. This attempt to handle the case where we
# start up with no networking, fail name resolution calls,
# and cache them for the life of the process, even after
# the network starts up, and for dhcp, updates resolv.conf
def reset_resolver():
    """Attempt to reset the system hostname resolver.
    returns 0 on success, or -1 if an error occurs."""
    try:
        import ctypes
        try:
            resolv = ctypes.CDLL("libc.so.6")
            r = resolv.__res_init()
        except (OSError, AttributeError):
            log.warn("could not find __res_init in libc.so.6")
            r = -1
        return r
    except ImportError:
        # If ctypes isn't supported (older versions of python for example)
        # Then just don't do anything
        pass
    except Exception, e:
        log.warning("reset_resolver failed: %s", e)
        pass


class RegisterInfo(ga_GObject.GObject):

    username = ga_GObject.property(type=str, default='')
    password = ga_GObject.property(type=str, default='')

    # server info
    hostname = ga_GObject.property(type=str, default='')
    port = ga_GObject.property(type=str, default='')
    prefix = ga_GObject.property(type=str, default='')

    # rhsm model info
    environment = ga_GObject.property(type=str, default='')
    consumername = ga_GObject.property(type=str, default='')
    owner_key = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)
    activation_keys = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)

    # split into AttachInfo or FindSlaInfo?
    current_sla = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)
    dry_run_result = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)

    # registergui states
    skip_auto_bind = ga_GObject.property(type=bool, default=False)
    details_label_txt = ga_GObject.property(type=str, default='')
    register_state = ga_GObject.property(type=int, default=REGISTERING)

    # TODO: make a gobj prop as well, with custom set/get, so we can be notified
    @property
    def identity(self):
        id = require(IDENTITY)
        return id

    def __init__(self):
        ga_GObject.GObject.__init__(self)


class RegisterWidget(widgets.SubmanBaseWidget):
    gui_file = "registration"
    widget_names = ['register_widget', 'register_notebook',
                    'register_details_label', 'register_progressbar',
                    'progress_label']

    __gsignals__ = {'proceed': (ga_GObject.SignalFlags.RUN_FIRST,
                                None, []),
                    'register-warning': (ga_GObject.SignalFlags.RUN_FIRST,
                                         None, (ga_GObject.TYPE_PYOBJECT,)),
                    'register-error': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, (ga_GObject.TYPE_PYOBJECT,
                                              ga_GObject.TYPE_PYOBJECT)),
                    'finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'attach-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                        None, []),
                    'register-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                          None, [])}

    initial_screen = CHOOSE_SERVER_PAGE

    register_button_label = ga_GObject.property(type=str, default=_('Register'))
    # TODO: a prop equilivent to initial-setups 'completed' and 'status' props

    def __init__(self, backend, facts, reg_info=None, parent_window=None):
        super(RegisterWidget, self).__init__()

        self.backend = backend
        self.identity = require(IDENTITY)
        self.facts = facts

        self.async = AsyncBackend(self.backend)

        # TODO: should be able to get rid of this soon, the
        #       only thing that uses it is the NetworkConfigDialog in
        #       chooseServerScreen and we can replace that with an embedded
        #       widget
        self.parent_window = parent_window

        self.info = reg_info or RegisterInfo()

        self.progress_timer = None

        # TODO: move these handlers into their own class
        self.info.connect("notify::username",
                          self._on_username_password_change)
        self.info.connect("notify::password",
                          self._on_username_password_change)
        self.info.connect("notify::hostname",
                          self._on_connection_info_change)
        self.info.connect("notify::port",
                          self._on_connection_info_change)
        self.info.connect("notify::prefix",
                          self._on_connection_info_change)
        self.info.connect("notify::activation-keys",
                          self._on_activation_keys_change)
        self.info.connect('notify::details-label-txt',
                          self._on_details_label_txt_change)
        self.info.connect('notify::register-state',
                          self._on_register_state_change)

        # expect this to be driving from the parent dialog
        self.connect('proceed',
                     self._on_proceed)

        # FIXME: change glade name
        self.details_label = self.register_details_label

        # To update the 'next/register' button in the parent dialog based on the new page
        self.register_notebook.connect('switch-page',
                                       self._on_switch_page)

        screen_classes = [ChooseServerScreen, ActivationKeyScreen,
                          CredentialsScreen, OrganizationScreen,
                          EnvironmentScreen, PerformRegisterScreen,
                          SelectSLAScreen, ConfirmSubscriptionsScreen,
                          PerformSubscribeScreen, RefreshSubscriptionsScreen,
                          InfoScreen, DoneScreen]
        self._screens = []

        # TODO: current_screen as a gobject property
        for idx, screen_class in enumerate(screen_classes):
            self.add_screen(idx, screen_class)

        self._current_screen = None

        # Track screens we "show" so we can choose a reasonable error screen
        self.screen_history = []

        # FIXME: modify property instead
        self.callbacks = []

        self.register_widget.show()

    def add_screen(self, idx, screen_class):
        screen = screen_class(reg_info=self.info,
                              async_backend=self.async,
                              facts=self.facts,
                              parent_window=self.parent_window)

        # add the index of the screen in self._screens to the class itself
        screen.screens_index = idx

        # connect handlers to various screen signals. The screens are
        # Gobjects not gtk widgets, so they can't propagate normally.
        screen.connect('move-to-screen', self._on_move_to_screen)
        screen.connect('stay-on-screen', self._on_stay_on_screen)
        screen.connect('register-error', self._on_screen_register_error)
        screen.connect('register-finished',
                       self._on_screen_register_finished)
        screen.connect('attach-finished',
                       self._on_screen_attach_finished)

        self._screens.append(screen)

        # Some screens have no gui controls, they just use the
        # PROGRESS_PAGE, so the indexes to the register_notebook's pages and
        # to self._screen differ
        if screen.needs_gui:
            # screen.index is the screens index in self.register_notebook
            screen.index = self.register_notebook.append_page(screen.container,
                                                              tab_label=None)

    def initialize(self):
        self.set_initial_screen()
        self.clear_screens()
        # TODO: move this so it's only running when a progress bar is "active"
        self.register_widget.show_all()

    def start_progress_timer(self):
        if not self.progress_timer:
            self.progress_timer = ga_GObject.timeout_add(100, self._timeout_callback)

    def stop_progress_timer(self):
        if self.progress_timer:
            ga_GObject.source_remove(self.progress_timer)
            self.progress_timer = None

    def set_initial_screen(self):
        self._set_screen(self.initial_screen)
        self._current_screen = self.initial_screen
        self.screen_history = [self.initial_screen]

    # switch-page should be after the current screen is reset
    def _on_switch_page(self, notebook, page, page_num):
        current_screen = self._screens[self._current_screen]
        # NonGuiScreens have a None button label
        if current_screen.button_label:
            self.set_property('register-button-label', current_screen.button_label)

    # HMMM: If the connect/backend/async, and the auth info is composited into
    #       the same GObject, these could be class closure handlers
    def _on_username_password_change(self, *args):
        self.async.set_user_pass(self.info.username, self.info.password)

    def _on_connection_info_change(self, *args):
        self.async.update()

    def _on_activation_keys_change(self, obj, param):
        activation_keys = obj.get_property('activation-keys')

        # Unset backend from attempting to use basic auth
        if activation_keys:
            self.async.cp_provider.set_user_pass()
            self.async.update()

    def _on_details_label_txt_change(self, obj, value):
        """Update the label under the progress bar on progress page."""
        self.details_label.set_label("<small>%s</small>" %
                                     obj.get_property('details-label-txt'))

    def _on_register_state_change(self, obj, value):
        """Handler for the signal indicating we moved from registering to attaching.

        (the 'register-state' property changed), so update the
        related label on progress page."""
        state = obj.get_property('register-state')
        if state == REGISTERING:
            self.progress_label.set_markup(_("<b>Registering</b>"))
        elif state == SUBSCRIBING:
            self.progress_label.set_markup(_("<b>Attaching</b>"))

    def do_register_error(self, msg, exc_info):
        """Class closure signal handler for 'register-error'.

        This should always get run first, when this widget emits a
        'register-error', then it's emitted to other handlers (set up by
        any parent dialogs for example)."""
        # return to the last gui screen we showed.

        self._set_screen(self.screen_history[-1])

    def _on_screen_register_error(self, obj, msg, exc_info):
        """Handler for 'register-error' signals emitted from the Screens.

        Then emit one ourselves. Now emit a new signal for parent widget and
        self.do_register_error() to handle"""

        self.emit('register-error', msg, exc_info)

        # do_register_error handles it for this widget, so stop emission
        return False

    def _on_stay_on_screen(self, current_screen):
        """A 'stay-on-screen' handler, for errors that need to be corrected before proceeding.

        A screen has been shown, and error handling emits this to indicate the
        widget should not move to a different screen.

        This also represents screens that allow the user to potentially correct
        an error, so we track the history of these screens so errors can go to
        a useful screen."""
        self.screen_history.append(current_screen.screens_index)
        self._set_screen(self._current_screen)

    # TODO: replace most of the gui flow logic in the Screen subclasses with
    #       some state machine that drives them, possibly driving via signals
    #       indicating each state

    def _on_move_to_screen(self, current_screen, next_screen_id):
        """Handler for the 'move-to-screen' signal, indicating a jump to another screen.

        This can be used to send the UI to any other screen, including the next screen.
        For example, to skip SLA selection if there is only one SLA."""
        self.change_screen(next_screen_id)

    def change_screen(self, next_screen_id):
        """Move to the next screen and call the next screens .pre().

        If next_screen.pre() indicates it is async (by returning True)and is spinning
        off a thread and we should wait for a callback, then move the screen to the
        PROGRESS_PAGE. The callback passed to AsyncBackend in pre() is then responsible
        for sending the user to the right screen via 'move-to-screen' signal."""
        next_screen = self._screens[next_screen_id]

        self._set_screen(next_screen_id)

        async = next_screen.pre()
        if async:
            self.start_progress_timer()
            next_screen.emit('move-to-screen', PROGRESS_PAGE)

    def _set_screen(self, screen):
        """Handle both updating self._current_screen, and updating register_notebook."""
        next_notebook_page = screen

        if screen > PROGRESS_PAGE:
            self._current_screen = screen
            # FIXME: If we just add ProgressPage in the screen order, we
            # shouldn't need this bookeeping
            if self._screens[screen].needs_gui:
                next_notebook_page = self._screens[screen].index
        else:
            # TODO: replace with a generator
            next_notebook_page = screen + 1

        # set_current_page changes the gui, and also results in the
        # 'switch-page' attribute of the gtk notebook being emitted,
        # indicating the gui has switched to that page.
        self.register_notebook.set_current_page(next_notebook_page)

    # FIXME: figure out to determine we are on first screen, then this
    # could just be 'move-to-screen', next screen
    # Go to the next screen/state
    def _on_proceed(self, obj):
        self.apply_current_screen()

    def apply_current_screen(self):
        """Extract any info from the widgets and call the screens apply()."""
        self._screens[self._current_screen].apply()

    def _on_screen_register_finished(self, obj):
        """Handler for 'register-finished' signal, indicating register is finished.

        The 'register-finished' signal indicates that we are finished with
        registration (either completly, or because it's not needed, etc).
        RegisterWidget then emits it's own 'register-finished' for any parent
        dialogs to handle. Note: 'register-finished' only means the registration
        steps are finished, and not neccasarily that the gui should be close.
        It may need to auto attach, etc. The 'finished' signal indicates register
        and attach are finished, while 'register-finished' is just the first part."""

        self.emit('register-finished')

        # We are done if there is auto bind is being skipped ("Manually attach
        # to subscriptions" is clicked in the gui)
        if self.info.get_property('skip-auto-bind'):
            self.emit('finished')

    def _on_screen_attach_finished(self, obj):
        """Handler for 'attach-finished' signal from our Screens.

        One of our Screens has indicated that subscription attachment is done.
        Note: This doesn't neccasarily indicate success, just that the gui has
        done all the attaching it can. RegisterWidget emits it's own
        'attach-finished' for parent widgets to handle. Again, note that
        attach-finished is not the same as 'finished', even though at the moment,
        'finished' does immediately follow 'attach-finished'"""

        self.emit('attach-finished')

        # If attach is finished, we are done.
        # let RegisterWidget's self.do_finished() handle any self specific
        # shutdown (like detaching self.timer) first.
        self.emit('finished')

    def do_finished(self):
        """Class closure signal handler for the 'finished' signal.

        Ran first before the any other signal handlers attach to 'finished'"""
        if self.progress_timer:
            ga_GObject.source_remove(self.progress_timer)

        # Switch to the 'done' screen before telling other signal handlers we
        # are done. This way, parent widgets like initial-setup that don't just
        # close the window have something to display.
        self.done()

    def done(self):
        self.change_screen(DONE_PAGE)

    def clear_screens(self):
        for screen in self._screens:
            screen.clear()

    def _timeout_callback(self):
        """Callback used to drive the progress bar 'pulse'."""
        self.register_progressbar.pulse()
        # return true to keep it pulsing
        return True


class RegisterDialog(widgets.SubmanBaseWidget):

    widget_names = ['register_dialog', 'register_dialog_main_vbox',
                    'register_details_label',
                    'cancel_button', 'register_button', 'progress_label',
                    'dialog_vbox6']

    gui_file = "register_dialog"
    __gtype_name__ = 'RegisterDialog'

    def __init__(self, backend, facts=None, callbacks=None):
        """
        Callbacks will be executed when registration status changes.
        """
        super(RegisterDialog, self).__init__()

        # dialog
        callbacks = {"on_register_cancel_button_clicked": self.cancel,
                     "on_register_button_clicked": self._on_register_button_clicked,
                     "hide": self.cancel,
                     "on_register_dialog_delete_event": self.cancel}
        self.connect_signals(callbacks)

        self.reg_info = RegisterInfo()
        # FIXME: Need better error handling in general, but it's kind of
        # annoying to have to pass the top level widget all over the place
        self.register_widget = RegisterWidget(backend, facts,
                                              reg_info=self.reg_info,
                                              parent_window=self.register_dialog)

        # Ensure that we start on the first page and that
        # all widgets are cleared.
        self.register_widget.initialize()

        self.register_dialog_main_vbox.pack_start(self.register_widget.register_widget,
                                                  True, True, 0)

        self.register_button.connect('clicked', self._on_register_button_clicked)
        self.cancel_button.connect('clicked', self.cancel)

        # initial-setup will likely handle these itself
        self.register_widget.connect('finished', self.cancel)
        self.register_widget.connect('register-error', self.on_register_error)

        # update window title on register state changes
        self.register_widget.info.connect('notify::register-state',
                                           self._on_register_state_change)

        # update the 'next/register button on page change'
        self.register_widget.connect('notify::register-button-label',
                                     self._on_register_button_label_change)

        self.window = self.register_dialog

        # FIXME: needed by firstboot
        self.password = None

    def initialize(self):
        self.register_widget.clear_screens()
        # self.register_widget.initialize()

    def show(self):
        # initial-setup module skips this, since it results in a
        # new top level window that isn't reparented to the initial-setup
        # screen.
        self.register_dialog.show()

    def cancel(self, button):
        self.register_dialog.hide()
        return True

    def on_register_error(self, obj, msg, exc_list):
        # TODO: we can add the register state, error type (error or exc)
        if exc_list:
            self.handle_register_exception(obj, msg, exc_list)
        else:
            self.handle_register_error(obj, msg)
        return True

    def handle_register_error(self, obj, msg):
        log.error("registration error: %s", msg)
        self.error_dialog(obj, msg)

        # RegisterWidget.do_register_error() will take care of changing screens

    def handle_register_exception(self, obj, msg, exc_info):
        # format_exception ends up logging the exception as well
        message = format_exception(exc_info, msg)
        self.error_dialog(obj, message)

    def error_dialog(self, obj, msg):
        show_error_window(msg)

    def _on_register_button_clicked(self, button):
        self.register_widget.emit('proceed')

    def _on_register_state_change(self, obj, value):
        state = obj.get_property('register-state')
        if state == REGISTERING:
            self.register_dialog.set_title(_("System Registration"))
        elif state == SUBSCRIBING:
            self.register_dialog.set_title(_("Subscription Attachment"))

    def _on_register_button_label_change(self, obj, value):
        register_label = obj.get_property('register-button-label')
        # FIXME: button_label can be None for NonGuiScreens. Seems like
        #
        if register_label:
            self.register_button.set_label(register_label)


class AutobindWizardDialog(RegisterDialog):
    __gtype_name__ = "AutobindWizard"

    initial_screen = SELECT_SLA_PAGE

    def __init__(self, backend, facts):
        super(AutobindWizardDialog, self).__init__(backend, facts)

    def show(self):
        super(AutobindWizardDialog, self).show()
        self.register_widget.change_screen(SELECT_SLA_PAGE)


# TODO: Screen could be a container widget, that has the rest of the gui as
#       a child. That way, we could add the Screen class to the
#       register_notebook directly, and follow up to the parent the normal
#       way. Then we could stop passing 'parent' around. And RegisterInfo
#       could be on the parent register_notebook. I think the various GtkDialogs
#       for error handling (handle_gui_exception, etc) would also find it by
#       default.
class Screen(widgets.SubmanBaseWidget):
    widget_names = ['container']
    gui_file = None
    screen_enum = None

    # TODO: replace page int with class enum
    __gsignals__ = {'stay-on-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'register-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'attach-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'register-error': (ga_GObject.SignalFlags.RUN_FIRST,
                              None, (ga_GObject.TYPE_PYOBJECT,
                                     ga_GObject.TYPE_PYOBJECT)),
                    'move-to-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                     None, (int,))}

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(Screen, self).__init__()

        self.pre_message = ""
        self.button_label = _("Register")
        self.needs_gui = True
        self.index = -1
        # REMOVE self._error_screen = self.index

        self.parent_window = parent_window
        self.info = reg_info
        self.async = async_backend
        self.facts = facts

    def stay(self):
        self.emit('stay-on-screen')

    def pre(self):
        return False

    # do whatever the screen indicates, and emit any signals indicating where
    # to move to next. apply() should not return anything.
    def apply(self):
        pass

    def post(self):
        pass

    def clear(self):
        pass


class NoGuiScreen(ga_GObject.GObject):
    screen_enum = None

    __gsignals__ = {'identity-updated': (ga_GObject.SignalFlags.RUN_FIRST,
                                         None, []),
                    'move-to-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, (int,)),
                    'stay-on-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, []),
                    'register-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'attach-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                 None, []),
                    'register-error': (ga_GObject.SignalFlags.RUN_FIRST,
                              None, (ga_GObject.TYPE_PYOBJECT,
                                     ga_GObject.TYPE_PYOBJECT)),
                    'certs-updated': (ga_GObject.SignalFlags.RUN_FIRST,
                                      None, [])}

    def __init__(self, reg_info, async_backend, facts, parent_window):
        ga_GObject.GObject.__init__(self)

        self.parent_window = parent_window
        self.info = reg_info
        self.async = async_backend
        self.facts = facts

        self.button_label = None
        self.needs_gui = False
        self.pre_message = "Default Pre Message"

    # FIXME: a do_register_error could be used for logging?
    #        Otherwise it's up to the parent dialog to do the logging.

    def pre(self):
        return True

    def apply(self):
        self.emit('move-to-screen')

    def post(self):
        pass

    def clear(self):
        pass


class PerformRegisterScreen(NoGuiScreen):
    screen_enum = PERFORM_REGISTER_PAGE

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(PerformRegisterScreen, self).__init__(reg_info, async_backend, facts, parent_window)

    def _on_registration_finished_cb(self, new_account, error=None):
        if error is not None:
            self.emit('register-error',
                      REGISTER_ERROR,
                      error)
            # TODO: register state
            return

        try:
            managerlib.persist_consumer_cert(new_account)
        except Exception, e:
            # hint: register error, back to creds?
            self.emit('register-error', REGISTER_ERROR, e)
            return

        # trigger a id cert reload
        self.emit('identity-updated')

        # Force all the cert dir backends to update, but mostly
        # force the identity cert monitor to run, which will
        # also update Backend. It also blocks until the new
        # identity is reloaded, so we don't start the selectSLA
        # screen before it.
        self.async.backend.cs.force_cert_check()

        # Done with the registration stuff, now on to attach
        self.emit('register-finished')

        if self.info.get_property('activation-keys'):
            self.emit('move-to-screen', REFRESH_SUBSCRIPTIONS_PAGE)
            return
        elif self.info.get_property('skip-auto-bind'):
            return
        else:
            self.emit('move-to-screen', SELECT_SLA_PAGE)
            return

    def pre(self):
        log.info("Registering to owner: %s environment: %s" %
                 (self.info.get_property('owner-key'),
                  self.info.get_property('environment')))

        self.async.register_consumer(self.info.get_property('consumername'),
                                     self.facts,
                                     self.info.get_property('owner-key'),
                                     self.info.get_property('environment'),
                                     self.info.get_property('activation-keys'),
                                     self._on_registration_finished_cb)

        return True


class PerformSubscribeScreen(NoGuiScreen):
    screen_enum = PERFORM_SUBSCRIBE_PAGE

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(PerformSubscribeScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self.pre_message = _("Attaching subscriptions")

    def _on_subscribing_finished_cb(self, unused, error=None):
        if error is not None:
            message = _("Error subscribing: %s")
            self.emit('register-error', message, error)
            return

        self.emit('certs-updated')
        self.emit('attach-finished')

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async.subscribe(self.info.identity.uuid,
                             self.info.get_property('current-sla'),
                             self.info.get_property('dry-run-result'),
                             self._on_subscribing_finished_cb)

        return True


class ConfirmSubscriptionsScreen(Screen):
    """ Confirm Subscriptions GUI Window """
    screen_enum = CONFIRM_SUBS_PAGE
    widget_names = Screen.widget_names + ['subs_treeview', 'back_button',
                                          'sla_label']

    gui_file = "confirmsubs"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(ConfirmSubscriptionsScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self.button_label = _("Attach")

        self.store = ga_Gtk.ListStore(str, bool, str)
        self.subs_treeview.set_model(self.store)
        self.subs_treeview.get_selection().set_mode(ga_Gtk.SelectionMode.NONE)

        self.add_text_column(_("Subscription"), 0, True)

        column = widgets.MachineTypeColumn(1)
        column.set_sort_column_id(1)
        self.subs_treeview.append_column(column)

        self.add_text_column(_("Quantity"), 2)

    def add_text_column(self, name, index, expand=False):
        text_renderer = ga_Gtk.CellRendererText()
        column = ga_Gtk.TreeViewColumn(name, text_renderer, text=index)
        column.set_expand(expand)

        self.subs_treeview.append_column(column)
        column.set_sort_column_id(index)
        return column

    def apply(self):
        self.emit('move-to-screen', PERFORM_SUBSCRIBE_PAGE)

    def set_model(self):
        dry_run_result = self.info.get_property('dry-run-result')

        # Make sure that the store is cleared each time
        # the data is loaded into the screen.
        self.store.clear()

        if not dry_run_result:
            return

        self.sla_label.set_markup("<b>" + dry_run_result.service_level +
                                  "</b>")

        for pool_quantity in dry_run_result.json:
            self.store.append([pool_quantity['pool']['productName'],
                              PoolWrapper(pool_quantity['pool']).is_virt_only(),
                              str(pool_quantity['quantity'])])

    def pre(self):
        self.set_model()
        return False


class SelectSLAScreen(Screen):
    """
    An wizard screen that displays the available
    SLAs that are provided by the installed products.
    """
    screen_enum = SELECT_SLA_PAGE
    widget_names = Screen.widget_names + ['product_list_label',
                                          'sla_radio_container',
                                          'owner_treeview']
    gui_file = "selectsla"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(SelectSLAScreen, self).__init__(reg_info, async_backend, facts, parent_window)

        self.pre_message = _("Finding suitable service levels")
        self.button_label = _("Next")

    def set_model(self, unentitled_prod_certs, sla_data_map):
        self.product_list_label.set_text(
                self._format_prods(unentitled_prod_certs))
        group = None
        # reverse iterate the list as that will most likely put 'None' last.
        # then pack_start so we don't end up with radio buttons at the bottom
        # of the screen.
        for sla in reversed(sla_data_map.keys()):
            radio = ga_Gtk.RadioButton(group=group, label=sla)
            radio.connect("toggled",
                          self._radio_clicked,
                          (sla, sla_data_map))
            self.sla_radio_container.pack_start(radio, expand=False,
                                                fill=False, padding=0)
            radio.show()
            group = radio

        # set the initial radio button as default selection.
        group.set_active(True)

    def apply(self):
        self.emit('move-to-screen', CONFIRM_SUBS_PAGE)

    def clear(self):
        child_widgets = self.sla_radio_container.get_children()
        for child in child_widgets:
            self.sla_radio_container.remove(child)

    def _radio_clicked(self, button, data):
        sla, sla_data_map = data

        if button.get_active():
            self.info.set_property('dry-run-result',
                                           sla_data_map[sla])

    def _format_prods(self, prod_certs):
        prod_str = ""
        for i, cert in enumerate(prod_certs):
            log.debug(cert)
            prod_str = "%s%s" % (prod_str, cert.products[0].name)
            if i + 1 < len(prod_certs):
                prod_str += ", "
        return prod_str

    # so much for service level simplifying things
    # FIXME: this could be split into 'on_get_all_service_levels_cb' and
    #        and 'on_get_service_levels_cb'
    def _on_get_service_levels_cb(self, result, error=None):
        if error is not None:
            if isinstance(error[1], ServiceLevelNotSupportedException):
                msg = _("Unable to auto-attach, server does not support service levels.")
                self.emit('register-error', msg, None)
                # HMM: if we make the ok a register-error as well, we may get
                # wacky ordering if the register-error is followed immed by a
                # register-finished?
                self.emit('attach-finished')
                return
            elif isinstance(error[1], NoProductsException):
                msg = _("No installed products on system. No need to attach subscriptions at this time.")
                self.emit('register-error', msg, None)
                self.emit('attach-finished')
                return
            elif isinstance(error[1], AllProductsCoveredException):
                msg = _("All installed products are covered by valid entitlements. "
                        "No need to attach subscriptions at this time.")
                self.emit('register-error', msg, None)
                self.emit('attach-finished')
                return
            elif isinstance(error[1], GoneException):
                # FIXME: shoudl we log here about deleted consumer or
                #        did we do that when we created GoneException?
                msg = _("Consumer has been deleted.")
                self.emit('register-error', msg, None)
                return
                # TODO: where we should go from here?
            else:
                log.exception(error)
                self.emit('register-error',
                          _("Error subscribing"),
                          error)
                return

        (current_sla, unentitled_products, sla_data_map) = result

        self.info.set_property('current-sla', current_sla)

        if len(sla_data_map) == 1:
            # If system already had a service level, we can hit this point
            # when we cannot fix any unentitled products:
            if current_sla is not None and \
                    not self._can_add_more_subs(current_sla, sla_data_map):
                msg = _("No available subscriptions at "
                        "the current service level: %s. "
                        "Please use the \"All Available "
                        "Subscriptions\" tab to manually "
                        "attach subscriptions.") % current_sla
                # TODO: add 'attach' state
                self.emit('register-error', msg, None)
                self.emit('attach-finished')
                return

            self.info.set_property('dry-run-result',
                                           sla_data_map.values()[0])
            self.emit('move-to-screen', CONFIRM_SUBS_PAGE)
            return
        elif len(sla_data_map) > 1:
            self.set_model(unentitled_products, sla_data_map)
            self.stay()
            return
        else:
            log.info("No suitable service levels found.")
            msg = _("No service level will cover all "
                    "installed products. Please manually "
                    "subscribe using multiple service levels "
                    "via the \"All Available Subscriptions\" "
                    "tab or purchase additional subscriptions.")
            # TODO: add 'registering/attaching' state info
            self.emit('register-error', msg, None)
            self.emit('attach-finished')

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.info.set_property('register-state', SUBSCRIBING)
        self.info.identity.reload()

        self.async.find_service_levels(self.info.identity.uuid,
                                       self.facts,
                                       self._on_get_service_levels_cb)
        return True

    def _can_add_more_subs(self, current_sla, sla_data_map):
        """
        Check if a system that already has a selected sla can get more
        entitlements at their sla level
        """
        if current_sla is not None:
            result = sla_data_map[current_sla]
            return len(result.json) > 0
        return False


class EnvironmentScreen(Screen):
    widget_names = Screen.widget_names + ['environment_treeview']
    gui_file = "environment"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(EnvironmentScreen, self).__init__(reg_info, async_backend, facts, parent_window)

        self.pre_message = _("Fetching list of possible environments")
        renderer = ga_Gtk.CellRendererText()
        column = ga_Gtk.TreeViewColumn(_("Environment"), renderer, text=1)
        self.environment_treeview.set_property("headers-visible", False)
        self.environment_treeview.append_column(column)

    def _on_get_environment_list_cb(self, result_tuple, error=None):
        environments = result_tuple
        if error is not None:
            # TODO: registering state
            self.emit('register-error', REGISTER_ERROR, error)
            return

        if not environments:
            self.set_environment(None)
            self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
            return

        envs = [(env['id'], env['name']) for env in environments]
        if len(envs) == 1:
            self.set_environement(envs[0][0])
            self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
            return

        else:
            self.set_model(envs)
            self.stay()
            return

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async.get_environment_list(self.info.get_property('owner-key'),
                                        self._on_get_environment_list_cb)
        return True

    def apply(self):
        model, tree_iter = self.environment_treeview.get_selection().get_selected()
        self.set_environment(model.get_value(tree_iter, 0))
        self.emit('move-to-screen', PERFORM_REGISTER_PAGE)

    def set_environment(self, environment):
        self.info.set_property('environment', environment)

    def set_model(self, envs):
        environment_model = ga_Gtk.ListStore(str, str)
        for env in envs:
            environment_model.append(env)

        self.environment_treeview.set_model(environment_model)

        self.environment_treeview.get_selection().select_iter(
                environment_model.get_iter_first())


class OrganizationScreen(Screen):
    widget_names = Screen.widget_names + ['owner_treeview']
    gui_file = "organization"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(OrganizationScreen, self).__init__(reg_info, async_backend, facts, parent_window)

        self.pre_message = _("Fetching list of possible organizations")

        renderer = ga_Gtk.CellRendererText()
        column = ga_Gtk.TreeViewColumn(_("Organization"), renderer, text=1)
        self.owner_treeview.set_property("headers-visible", False)
        self.owner_treeview.append_column(column)

    def _on_get_owner_list_cb(self, owners, error=None):
        if error is not None:
            self.emit('register-error', REGISTER_ERROR, error)
            return

        owners = [(owner['key'], owner['displayName']) for owner in owners]
        # Sort by display name so the list doesn't randomly change.
        owners = sorted(owners, key=lambda item: item[1])

        if len(owners) == 0:
            msg = _("<b>User %s is not able to register with any orgs.</b>") % \
                    self.info.get_property('username')
            self.emit('register-error', msg, None)
            return

        if len(owners) == 1:
            owner_key = owners[0][0]
            self.info.set_property('owner-key', owner_key)
            # only one org, use it and skip the org selection screen
            self.emit('move-to-screen', ENVIRONMENT_SELECT_PAGE)
            return

        else:
            self.set_model(owners)
            self.stay()
            return

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async.get_owner_list(self.info.get_property('username'),
                                  self._on_get_owner_list_cb)
        return True

    def apply(self):
        # check for selection exists
        model, tree_iter = self.owner_treeview.get_selection().get_selected()
        owner_key = model.get_value(tree_iter, 0)
        self.info.set_property('owner-key', owner_key)
        self.emit('move-to-screen', ENVIRONMENT_SELECT_PAGE)

    def set_model(self, owners):
        owner_model = ga_Gtk.ListStore(str, str)
        for owner in owners:
            owner_model.append(owner)

        self.owner_treeview.set_model(owner_model)

        self.owner_treeview.get_selection().select_iter(
                owner_model.get_iter_first())


class CredentialsScreen(Screen):
    widget_names = Screen.widget_names + ['skip_auto_bind', 'consumer_name',
                                          'account_login', 'account_password',
                                          'registration_tip_label',
                                          'registration_header_label']

    gui_file = "credentials"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(CredentialsScreen, self).__init__(reg_info, async_backend, facts, parent_window)

        self._initialize_consumer_name()
        self.registration_tip_label.set_label("<small>%s</small>" %
                                          get_branding().GUI_FORGOT_LOGIN_TIP)

        self.registration_header_label.set_label("<b>%s</b>" %
                                             get_branding().GUI_REGISTRATION_HEADER)

    def _initialize_consumer_name(self):
        if not self.consumer_name.get_text():
            self.consumer_name.set_text(socket.gethostname())

    def _validate_consumername(self, consumername):
        if not consumername:
            # TODO: register state to signal
            self.emit('register-error',
                      _("You must enter a system name."),
                      None)

            self.consumer_name.grab_focus()
            return False
        return True

    def _validate_account(self):
        # validate / check user name
        if self.account_login.get_text().strip() == "":
            self.emit('register-error',
                      _("You must enter a login."),
                      None)

            self.account_login.grab_focus()
            return False

        if self.account_password.get_text().strip() == "":
            self.emit('register-error',
                      _("You must enter a password."),
                      None)

            self.account_password.grab_focus()
            return False
        return True

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.account_login.grab_focus()
        return False

    def apply(self):
        self.stay()
        username = self.account_login.get_text().strip()
        password = self.account_password.get_text().strip()
        consumername = self.consumer_name.get_text()
        skip_auto_bind = self.skip_auto_bind.get_active()

        if not self._validate_consumername(consumername):
            return

        if not self._validate_account():
            return

        self.info.set_property('username', username)
        self.info.set_property('password', password)
        self.info.set_property('skip-auto-bind', skip_auto_bind)
        self.info.set_property('consumername', consumername)

        self.emit('move-to-screen', OWNER_SELECT_PAGE)

    def clear(self):
        self.account_login.set_text("")
        self.account_password.set_text("")
        self.consumer_name.set_text("")
        self._initialize_consumer_name()
        self.skip_auto_bind.set_active(False)


class ActivationKeyScreen(Screen):
    widget_names = Screen.widget_names + [
                'activation_key_entry',
                'organization_entry',
                'consumer_entry',
        ]
    gui_file = "activation_key"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(ActivationKeyScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self._initialize_consumer_name()

    def _initialize_consumer_name(self):
        if not self.consumer_entry.get_text():
            self.consumer_entry.set_text(socket.gethostname())

    def apply(self):
        self.stay()
        activation_keys = self._split_activation_keys(
            self.activation_key_entry.get_text().strip())
        owner_key = self.organization_entry.get_text().strip()
        consumername = self.consumer_entry.get_text().strip()

        if not self._validate_owner_key(owner_key):
            return

        if not self._validate_activation_keys(activation_keys):
            return

        if not self._validate_consumername(consumername):
            return

        self.info.set_property('consumername', consumername)
        self.info.set_property('owner-key', owner_key)
        self.info.set_property('activation-keys', activation_keys)

        self.emit('move-to-screen', PERFORM_REGISTER_PAGE)

    def _split_activation_keys(self, entry):
        keys = re.split(',\s*|\s+', entry)
        return [x for x in keys if x]

    def _validate_owner_key(self, owner_key):
        if not owner_key:
            self.emit('register-error',
                      _("You must enter an organization."),
                      None)

            self.organization_entry.grab_focus()
            return False
        return True

    def _validate_activation_keys(self, activation_keys):
        if not activation_keys:
            self.emit('register-error',
                      _("You must enter an activation key."),
                      None)

            self.activation_key_entry.grab_focus()
            return False
        return True

    def _validate_consumername(self, consumername):
        if not consumername:
            self.emit('register-error',
                      _("You must enter a system name."),
                      None)

            self.consumer_entry.grab_focus()
            return False
        return True

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.organization_entry.grab_focus()
        return False


class RefreshSubscriptionsScreen(NoGuiScreen):

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(RefreshSubscriptionsScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self.pre_message = _("Attaching subscriptions")

    def _on_refresh_cb(self, error=None):
        if error is not None:
            self.emit('register-error',
                      _("Error subscribing: %s"),
                      error)
            # TODO: register state
            return

        self.emit('attach-finished')

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async.refresh(self._on_refresh_cb)
        return True


class ChooseServerScreen(Screen):
    widget_names = Screen.widget_names + ['server_entry', 'proxy_frame',
                                          'default_button', 'choose_server_label',
                                          'activation_key_checkbox']
    gui_file = "choose_server"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(ChooseServerScreen, self).__init__(reg_info, async_backend, facts, parent_window)

        self.button_label = _("Next")

        callbacks = {
                "on_default_button_clicked": self._on_default_button_clicked,
                "on_proxy_button_clicked": self._on_proxy_button_clicked,
            }

        self.connect_signals(callbacks)

        self.network_config_dialog = networkConfig.NetworkConfigDialog()

    def _on_default_button_clicked(self, widget):
        # Default port and prefix are fine, so we can be concise and just
        # put the hostname for RHN:
        self.server_entry.set_text(config.DEFAULT_HOSTNAME)

    def _on_proxy_button_clicked(self, widget):
        # proxy dialog may attempt to resolve proxy and server names, so
        # bump the resolver as well.
        self.reset_resolver()

        self.network_config_dialog.show()

    def reset_resolver(self):
        try:
            reset_resolver()
        except Exception, e:
            log.warn("Error from reset_resolver: %s", e)

    def apply(self):
        self.stay()
        server = self.server_entry.get_text()

        # TODO: test the values before saving, then update
        #       self.info and cfg if it works
        try:
            (hostname, port, prefix) = parse_server_info(server)
            CFG.set('server', 'hostname', hostname)
            CFG.set('server', 'port', port)
            CFG.set('server', 'prefix', prefix)

            self.reset_resolver()

            try:
                if not is_valid_server_info(hostname, port, prefix):
                    self.emit('register-error',
                              _("Unable to reach the server at %s:%s%s") %
                                (hostname, port, prefix),
                              None)
                    return
            except MissingCaCertException:
                self.emit('register-error',
                          _("CA certificate for subscription service has not been installed."),
                          None)
                return

        except ServerUrlParseError:
            self.emit('register-error',
                      _("Please provide a hostname with optional port and/or prefix: "
                        "hostname[:port][/prefix]"),
                      None)
            return

        log.debug("Writing server data to rhsm.conf")
        CFG.save()

        self.info.set_property('hostname', hostname)
        self.info.set_property('port', port)
        self.info.set_property('prefix', prefix)

        if self.activation_key_checkbox.get_active():
            self.emit('move-to-screen', ACTIVATION_KEY_PAGE)
            return

        else:
            self.emit('move-to-screen', CREDENTIALS_PAGE)
            return

    def clear(self):
        # Load the current server values from rhsm.conf:
        current_hostname = CFG.get('server', 'hostname')
        current_port = CFG.get('server', 'port')
        current_prefix = CFG.get('server', 'prefix')

        # No need to show port and prefix for hosted:
        if current_hostname == config.DEFAULT_HOSTNAME:
            self.server_entry.set_text(config.DEFAULT_HOSTNAME)
        else:
            self.server_entry.set_text("%s:%s%s" % (current_hostname,
                    current_port, current_prefix))


class AsyncBackend(object):

    def __init__(self, backend):
        self.backend = backend
        self.plugin_manager = require(PLUGIN_MANAGER)
        self.queue = Queue.Queue()

    def update(self):
        self.backend.update()

    def set_user_pass(self, username, password):
        self.backend.cp_provider.set_user_pass(username, password)
        self.backend.update()

    def _watch_thread(self):
        """
        glib idle method to watch for thread completion.
        runs the provided callback method in the main thread.
        """
        try:
            (callback, retval, error) = self.queue.get(block=False)
            if error:
                callback(retval, error=error)
            else:
                callback(retval)
            return False
        except Queue.Empty:
            return True

    def _get_owner_list(self, username, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = self.backend.cp_provider.get_basic_auth_cp().getOwnerList(username)
            self.queue.put((callback, retval, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _get_environment_list(self, owner_key, callback):
        """
        method run in the worker thread.
        """
        try:
            retval = None
            # If environments aren't supported, don't bother trying to list:
            if self.backend.cp_provider.get_basic_auth_cp().supports_resource('environments'):
                log.info("Server supports environments, checking for "
                         "environment to register with.")
                retval = []
                for env in self.backend.cp_provider.get_basic_auth_cp().getEnvironmentList(owner_key):
                    retval.append(env)
                if len(retval) == 0:
                    raise Exception(_("Server supports environments, but "
                        "none are available."))

            self.queue.put((callback, retval, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _register_consumer(self, name, facts, owner, env, activation_keys, callback):
        """
        method run in the worker thread.
        """
        try:
            installed_mgr = require(INSTALLED_PRODUCTS_MANAGER)

            # TODO: not sure why we pass in a facts.Facts, and call it's
            #       get_facts() three times. The two bracketing plugin calls
            #       are meant to be able to enhance/tweak facts
            self.plugin_manager.run("pre_register_consumer", name=name,
                                    facts=facts.get_facts())

            cp = self.backend.cp_provider.get_basic_auth_cp()
            retval = cp.registerConsumer(name=name, facts=facts.get_facts(),
                                         owner=owner, environment=env,
                                         keys=activation_keys,
                                          installed_products=installed_mgr.format_for_server())

            self.plugin_manager.run("post_register_consumer", consumer=retval,
                                    facts=facts.get_facts())

            require(IDENTITY).reload()
            # Facts and installed products went out with the registration
            # request, manually write caches to disk:
            facts.write_cache()
            installed_mgr.write_cache()

            cp = self.backend.cp_provider.get_basic_auth_cp()

            # In practice, the only time this condition should be true is
            # when we are working with activation keys.  See BZ #888790.
            if not self.backend.cp_provider.get_basic_auth_cp().username and \
                not self.backend.cp_provider.get_basic_auth_cp().password:
                # Write the identity cert to disk
                managerlib.persist_consumer_cert(retval)
                self.backend.update()
                cp = self.backend.cp_provider.get_consumer_auth_cp()

            # FIXME: this looks like we are updating package profile as
            #        basic auth
            profile_mgr = require(PROFILE_MANAGER)
            profile_mgr.update_check(cp, retval['uuid'])

            # We have new credentials, restart virt-who
            restart_virt_who()

            self.queue.put((callback, retval, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _subscribe(self, uuid, current_sla, dry_run_result, callback):
        """
        Subscribe to the selected pools.
        """
        try:
            if not current_sla:
                log.debug("Saving selected service level for this system.")

                self.backend.cp_provider.get_consumer_auth_cp().updateConsumer(uuid,
                        service_level=dry_run_result.service_level)

            log.info("Binding to subscriptions at service level: %s" %
                    dry_run_result.service_level)
            for pool_quantity in dry_run_result.json:
                pool_id = pool_quantity['pool']['id']
                quantity = pool_quantity['quantity']
                log.debug("  pool %s quantity %s" % (pool_id, quantity))
                self.plugin_manager.run("pre_subscribe", consumer_uuid=uuid,
                                        pool_id=pool_id, quantity=quantity)
                ents = self.backend.cp_provider.get_consumer_auth_cp().bindByEntitlementPool(uuid, pool_id, quantity)
                self.plugin_manager.run("post_subscribe", consumer_uuid=uuid, entitlement_data=ents)
            # FIXME: this should be a different asyncBackend task
            managerlib.fetch_certificates(self.backend.certlib)
        except Exception:
            # Going to try to update certificates just in case we errored out
            # mid-way through a bunch of binds:
            # FIXME: emit update-ent-certs signal
            try:
                managerlib.fetch_certificates(self.backend.certlib)
            except Exception, cert_update_ex:
                log.info("Error updating certificates after error:")
                log.exception(cert_update_ex)
            self.queue.put((callback, None, sys.exc_info()))
            return
        self.queue.put((callback, None, None))

    # This guy is really ugly to run in a thread, can we run it
    # in the main thread with just the network stuff threaded?

    # get_consumer
    # get_service_level_list
    # update_consumer
    #  action_client
    #    update_installed_products
    #    update_facts
    #    update_other_action_client_stuff
    # for sla in available_slas:
    #   get_dry_run_bind for sla
    def _find_suitable_service_levels(self, consumer_uuid, facts):

        # FIXME:
        self.backend.update()

        consumer_json = self.backend.cp_provider.get_consumer_auth_cp().getConsumer(
                consumer_uuid)

        if 'serviceLevel' not in consumer_json:
            raise ServiceLevelNotSupportedException()

        owner_key = consumer_json['owner']['key']

        # This is often "", set to None in that case:
        current_sla = consumer_json['serviceLevel'] or None

        if len(self.backend.cs.installed_products) == 0:
            raise NoProductsException()

        if len(self.backend.cs.valid_products) == len(self.backend.cs.installed_products) and \
                len(self.backend.cs.partial_stacks) == 0:
            raise AllProductsCoveredException()

        if current_sla:
            available_slas = [current_sla]
            log.debug("Using system's current service level: %s" %
                    current_sla)
        else:
            available_slas = self.backend.cp_provider.get_consumer_auth_cp().getServiceLevelList(owner_key)
            log.debug("Available service levels: %s" % available_slas)

        # Will map service level (string) to the results of the dry-run
        # autobind results for each SLA that covers all installed products:
        suitable_slas = {}

        # eek, in a thread
        action_client = ActionClient(facts=facts)
        action_client.update()

        for sla in available_slas:

            # TODO: what kind of madness would happen if we did a couple of
            # these in parallel in seperate threads?
            dry_run_json = self.backend.cp_provider.get_consumer_auth_cp().dryRunBind(consumer_uuid, sla)

            # FIXME: are we modifying cert_sorter (self.backend.cs) state here?
            # FIXME: it's only to get the unentitled products list, can pass
            #        that in
            dry_run = DryRunResult(sla, dry_run_json, self.backend.cs)

            # If we have a current SLA for this system, we do not need
            # all products to be covered by the SLA to proceed through
            # this wizard:
            if current_sla or dry_run.covers_required_products():
                suitable_slas[sla] = dry_run

        # why do we call cert_sorter stuff in the return?
        return (current_sla, self.backend.cs.unentitled_products.values(), suitable_slas)

    def _find_service_levels(self, consumer_uuid, facts, callback):
        """
        method run in the worker thread.
        """
        try:
            suitable_slas = self._find_suitable_service_levels(consumer_uuid, facts)
            self.queue.put((callback, suitable_slas, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _refresh(self, callback):
        try:
            managerlib.fetch_certificates(self.backend.certlib)
            self.queue.put((callback, None, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def get_owner_list(self, username, callback):
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._get_owner_list,
                         name="GetOwnerListThread",
                         args=(username, callback)).start()

    def get_environment_list(self, owner_key, callback):
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._get_environment_list,
                         name="GetEnvironmentListThread",
                         args=(owner_key, callback)).start()

    def register_consumer(self, name, facts, owner, env, activation_keys, callback):
        """
        Run consumer registration asyncronously
        """
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._register_consumer,
                         name="RegisterConsumerThread",
                         args=(name, facts, owner,
                               env, activation_keys, callback)).start()

    def subscribe(self, uuid, current_sla, dry_run_result, callback):
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._subscribe,
                         name="SubscribeThread",
                         args=(uuid, current_sla,
                               dry_run_result, callback)).start()

    def find_service_levels(self, consumer_uuid, facts, callback):
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._find_service_levels,
                         name="FindServiceLevelsThread",
                         args=(consumer_uuid, facts, callback)).start()

    def refresh(self, callback):
        ga_GObject.idle_add(self._watch_thread)
        threading.Thread(target=self._refresh,
                         name="RefreshThread",
                         args=(callback,)).start()


# TODO: make this a more informative 'summary' page.
class DoneScreen(Screen):
    gui_file = "done_box"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(DoneScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self.pre_message = "We are done."


class InfoScreen(Screen):
    """
    An informational screen taken from rhn-client-tools and only displayed
    in firstboot when we're not working alongside that package. (i.e.
    Fedora or RHEL 7 and beyond)

    Also allows the user to skip registration if they wish.
    """
    widget_names = Screen.widget_names + [
                'register_radio',
                'skip_radio',
                'why_register_dialog'
        ]
    gui_file = "registration_info"

    def __init__(self, reg_info, async_backend, facts, parent_window):
        super(InfoScreen, self).__init__(reg_info, async_backend, facts, parent_window)
        self.button_label = _("Next")
        callbacks = {"on_why_register_button_clicked":
                     self._on_why_register_button_clicked,
                     "on_back_to_reg_button_clicked":
                     self._on_back_to_reg_button_clicked
                     }

        self.connect_signals(callbacks)

    def pre(self):
        return False

    def apply(self):
        self.stay()
        if self.register_radio.get_active():
            log.debug("Proceeding with registration.")
            self.emit('move-to-screen', CHOOSE_SERVER_PAGE)
            return

        else:
            log.debug("Skipping registration.")
            self.emit('move-to-screen', FINISH)

    def _on_why_register_button_clicked(self, button):
        self.why_register_dialog.show()

    def _on_back_to_reg_button_clicked(self, button):
        self.why_register_dialog.hide()
