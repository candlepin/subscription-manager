from __future__ import print_function, division, absolute_import

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
import logging
import re
import socket
import sys
import threading

from six.moves import queue

from subscription_manager import ga_loader
ga_loader.init_ga()

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.ga import GObject as ga_GObject

import rhsm.config as base_config
from rhsm.utils import ServerUrlParseError
from rhsm.connection import GoneException, RestlibException, UEPConnection, \
        ProxyException

from subscription_manager.branding import get_branding
from subscription_manager.action_client import ActionClient
from subscription_manager.gui import networkConfig
from subscription_manager.gui import widgets
from subscription_manager.injection import IDENTITY, PLUGIN_MANAGER, require, \
        INSTALLED_PRODUCTS_MANAGER, PROFILE_MANAGER, FACTS, ENT_DIR
from subscription_manager import managerlib
from subscription_manager.utils import is_valid_server_info, MissingCaCertException, \
        parse_server_info, restart_virt_who

from subscription_manager.gui import utils as gui_utils
from subscription_manager.gui.autobind import DryRunResult, \
        ServiceLevelNotSupportedException, AllProductsCoveredException, \
        NoProductsException
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.gui.networkConfig import reset_resolver

from subscription_manager import syspurposelib

from subscription_manager.i18n import ugettext as _

from subscription_manager import logutil

logutil.init_logger()
log = logging.getLogger(__name__)

from rhsmlib.services import config, attach
conf = config.Config(base_config.initConfig())


class RegisterState(object):
    REGISTERING = 0
    SUBSCRIBING = 1


ERROR_SCREEN = -3
DONT_CHANGE = -2
PROGRESS_PAGE = -1
CHOOSE_SERVER_PAGE = 0
VALIDATE_SERVER_PAGE = 1
ACTIVATION_KEY_PAGE = 2
CREDENTIALS_PAGE = 3
PERFORM_UNREGISTER_PAGE = 4
OWNER_SELECT_PAGE = 5
ENVIRONMENT_SELECT_PAGE = 6
PERFORM_REGISTER_PAGE = 7
UPLOAD_PACKAGE_PROFILE_PAGE = 8
FIND_SUBSCRIPTIONS = 9
CONFIRM_SUBS_PAGE = 10
PERFORM_SUBSCRIBE_PAGE = 11
REFRESH_SUBSCRIPTIONS_PAGE = 12
INFO_PAGE = 13
DONE_PAGE = 14
REGISTERED_UNATTACHED = 15
FINISH = 100

REGISTER_ERROR = _("<b>Unable to register the system.</b>") + \
    "\n%s\n" + \
    _("Please see /var/log/rhsm/rhsm.log for more information.")


class RemoteUnregisterException(Exception):
    """
    This exception is to be used when we are unable to unregister from the server.
    """
    pass


def server_info_from_config(config):
    return {
            "host": conf['server']['hostname'],
            "ssl_port": conf['server'].get_int('port'),
            "handler": conf['server']['prefix'],
            "proxy_hostname": conf['server']['proxy_hostname'],
            "proxy_port": conf['server'].get_int('proxy_port'),
            "proxy_user": conf['server']['proxy_user'],
            "proxy_password": conf['server']['proxy_password']
           }


# FIXME: TODO: subclass collections.MutableSequence
class UniqueList(object):
    def __init__(self):
        self._list = []

    def append(self, item):
        if item in self._list:
            self._list.remove(item)
        return self._list.append(item)

    def __repr__(self):
        list_buf = ','.join([repr(a) for a in self._list])
        buf = "<UniqueList [%s] >" % list_buf
        return buf

    def remove(self, value):
        return self._list.remove(value)

    def last(self):
        return self._list[-1]

    def pop(self, index=None):
        # list.pop() has a odd not quite a keyword optional arg
        if index:
            p = self._list.pop(index)
        p = self._list.pop()
        return p

    def is_empty(self):
        return len(self._list) == 0


class RegisterInfo(ga_GObject.GObject):
    """GObject holding registration info and state.

    Used primarily as a way to share this info, while also supporting
    connecting handlers to the 'notify' signals from RegisterInfos GObject
    properties."""

    username = ga_GObject.property(type=str, default='')
    password = ga_GObject.property(type=str, default='')

    # server info
    hostname = ga_GObject.property(type=str, default='')
    port = ga_GObject.property(type=str, default='')
    prefix = ga_GObject.property(type=str, default='')
    use_activation_keys = ga_GObject.property(type=bool, default=False)

    server_info = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)

    # Used to control whether or not we should use the PerformUnregisterScreen
    enable_unregister = ga_GObject.property(type=bool, default=False)

    # rhsm model info
    environment = ga_GObject.property(type=str, default='')
    consumername = ga_GObject.property(type=str, default='')
    owner_key = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)
    activation_keys = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)

    # split into AttachInfo or FindSlaInfo?
    current_sla = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)
    preferred_sla = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)
    dry_run_result = ga_GObject.property(type=ga_GObject.TYPE_PYOBJECT, default=None)

    # register behaviour options
    skip_auto_bind = ga_GObject.property(type=bool, default=False)
    force = ga_GObject.property(type=bool, default=False)

    # registergui state info
    details_label_txt = ga_GObject.property(type=str, default='')
    register_state = ga_GObject.property(type=int, default=RegisterState.REGISTERING)

    register_status = ga_GObject.property(type=str, default='')

    # TODO: make a gobj prop as well, with custom set/get, so we can be notified
    @property
    def identity(self):
        id = require(IDENTITY)
        return id

    def __init__(self):
        ga_GObject.GObject.__init__(self)
        self._defaults_from_config()
        self._initial_registration_status()

    def _defaults_from_config(self):
        """Load the current server values from configuration (rhsm.conf)."""
        self.set_property('hostname', conf['server']['hostname'])
        self.set_property('port', conf['server']['port'])
        self.set_property('prefix', conf['server']['prefix'])

    def _initial_registration_status(self):
        msg = _("This system is currently not registered.")
        if self.identity and self.identity.is_valid():
            msg = _("System Already Registered")
        self.set_property('register-status', msg)


class RegisterWidget(widgets.SubmanBaseWidget):
    gui_file = "registration"
    widget_names = ['register_widget', 'register_notebook',
                    'register_details_label', 'register_progressbar',
                    'progress_label']

    __gsignals__ = {'proceed': (ga_GObject.SignalFlags.RUN_FIRST,
                                None, []),
                    'back': (ga_GObject.SignalFlags.RUN_FIRST,
                             None, []),
                    'register-message': (ga_GObject.SignalFlags.RUN_FIRST,
                                         None, (ga_GObject.TYPE_PYOBJECT,
                                                ga_GObject.TYPE_PYOBJECT)),
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

    screen_ready = ga_GObject.property(type=bool, default=True)
    register_button_label = ga_GObject.property(type=str)
    # TODO: a prop equivalent to initial-setups 'completed' and 'status' props

    def __init__(self, backend, reg_info=None, parent_window=None):
        super(RegisterWidget, self).__init__()

        self.set_property('register-button-label',
                          _('Register'))

        self.backend = backend

        self.async_backend = AsyncBackend(self.backend)

        # TODO: should be able to get rid of this soon, the
        #       only thing that uses it is the NetworkConfigDialog in
        #       chooseServerScreen and we can replace that with an embedded
        #       widget
        self.parent_window = parent_window

        # self.info = reg_info or RegisterInfo()
        self.info = reg_info

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
        self.proceed_handler = self.connect('proceed',
                                            self._on_proceed)
        self.back_handler = self.connect('back',
                                         self._on_back)

        # FIXME: change glade name
        self.details_label = self.register_details_label

        # To update the 'next/register' button in the parent dialog based on the new page
        self.register_notebook.connect('switch-page',
                                       self._on_switch_page)

        screen_classes = [ChooseServerScreen, ValidateServerScreen, ActivationKeyScreen,
                          CredentialsScreen, PerformUnregisterScreen,
                          OrganizationScreen, EnvironmentScreen,
                          PerformRegisterScreen,
                          PerformPackageProfileSyncScreen, FindSuitableSubscriptions,
                          ConfirmSubscriptionsScreen, PerformSubscribeScreen,
                          RefreshSubscriptionsScreen, InfoScreen,
                          DoneScreen]

        self._screens = []

        # TODO: current_screen as a gobject property
        for idx, screen_class in enumerate(screen_classes):
            self.add_screen(idx, screen_class)

        self._current_screen = self.initial_screen

        # Track screens we "show" so we can choose a reasonable error screen
        self.screen_history = []

        self.uniq_screen_history = UniqueList()
        self.applied_screen_history = UniqueList()
        # FIXME: modify property instead
        self.callbacks = []

        self.register_widget.show()

    def add_screen(self, idx, screen_class):
        screen = screen_class(reg_info=self.info,
                              async_backend=self.async_backend,
                              parent_window=self.parent_window)

        # add the index of the screen in self._screens to the class itself
        screen.screens_index = idx

        # connect handlers to various screen signals. The screens are
        # Gobjects not gtk widgets, so they can't propagate normally.
        screen.connect('move-to-screen', self._on_move_to_screen)
        screen.connect('stay-on-screen', self._on_stay_on_screen)
        screen.connect('register-error', self._on_screen_register_error)
        screen.connect('register-message', self._on_screen_register_message)
        screen.connect('register-finished',
                       self._on_screen_register_finished)
        screen.connect('attach-finished',
                       self._on_screen_attach_finished)
        screen.connect('notify::ready', self._on_screen_ready_change)

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
        self.populate_screens()

    @property
    def current_screen(self):
        return self._screens[self._current_screen]

    # Class closure signal handlers that are invoked first if this GObject
    # emits a signal they are connected to.
    def do_register_error(self, msg, exc_info):
        """Class closure signal handler for 'register-error'.

        This should always get run first, when this widget emits a
        'register-error', then it's emitted to other handlers (set up by
        any parent dialogs for example)."""

        # return to the last gui screen we showed.
        self._pop_last_screen()
        # We have more info here, but we need a good 'blurb'
        # for the status message of initial-setup.
        if exc_info == REGISTERED_UNATTACHED:
            self.show_success_message()
        else:
            msg = _("Error during registration.")
            self.info.set_property('register-status', msg)

    def do_register_message(self, msg, msg_type=None):
        # NOTE: we ignore msg_type here
        self._pop_last_screen()
        self.info.set_property('register-status', msg)

    def show_success_message(self):
        msg = _("System '%s' successfully registered.\n") % self.info.identity.name
        self.info.set_property('register-status', msg)

    def do_register_finished(self):
        self.show_success_message()
        conf.persist()
        last_server_info = server_info_from_config(conf)
        last_server_info['cert_file'] = self.backend.cp_provider.cert_file
        last_server_info['key_file'] = self.backend.cp_provider.key_file
        self.info.set_property('server-info', last_server_info)

    def do_finished(self):
        """Class closure signal handler for the 'finished' signal.

        Ran first before the any other signal handlers attach to 'finished'"""
        if self.progress_timer:
            ga_GObject.source_remove(self.progress_timer)

        # Switch to the 'done' screen before telling other signal handlers we
        # are done. This way, parent widgets like initial-setup that don't just
        # close the window have something to display.
        self.done()

    def _pop_last_screen(self):
        try:
            last = self.applied_screen_history.pop()
            self._set_screen(last)
            self._screens[last].back_handler()
        except IndexError:
            pass

    # methods for moving around between screens and tracking the state

    # On showing the widget, it could start at initial_screen, but with something
    # in the background checking if registered and updating RegisterInfo, and notify
    # on it's properties could trigger a move to 'AttachScreen' for example. Or perhaps
    # a "This is already registered, are you sure?" register screen.
    #
    def set_initial_screen(self):
        ga_GObject.idle_add(self.choose_initial_screen)

    def choose_initial_screen(self):
        try:
            self.info.identity.reload()
        except Exception as e:
            log.exception(e)
            self.emit('register-error',
                      'Error detecting if we were registered:',
                      sys.exc_info())
            return False

        if self.info.identity.is_valid():
            self.emit('register-finished')
            msg = _("System '%s' successfully registered.\n") % self.info.identity.name
            self.info.set_property('register-status', msg.rstrip())
            # We are done if auto bind is being skipped ("Manually attach
            # to subscriptions" is clicked in the gui)
            if self.info.get_property('skip-auto-bind'):
                self.emit('finished')
            self.current_screen.emit('move-to-screen', FIND_SUBSCRIPTIONS)
            self.register_widget.show_all()
            return False
        msg = _("This system is currently not registered.")
        self.info.set_property('register-status', msg)
        self.current_screen.stay()
        self.register_widget.show_all()
        return False

    def _on_stay_on_screen(self, current_screen):
        """A 'stay-on-screen' handler, for errors that need to be corrected before proceeding.

        The current_screen is a Screen() subclass instance, the screen that emitted
        the 'stay-on-screen'.

        A screen has been shown, and error handling emits this to indicate the
        widget should not move to a different screen.

        This also represents screens that allow the user to potentially correct
        an error, so we track the history of these screens so errors can go to
        a useful screen."""
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

        self.current_screen.set_property('ready', False)

        is_async = next_screen.pre()
        if is_async:
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

    def apply_current_screen(self):
        """Extract any info from the widgets and call the screens apply()."""
        #self._screen_history_append(self.current_screen.screens_index)

        # The apply can emit a move to page signal, changing current_page
        # So save current screen index first.
        current_screen_index = self.current_screen.screens_index
        self.applied_screen_history.append(current_screen_index)

        self.current_screen.apply()

    # FIXME: figure out to determine we are on first screen, then this
    # could just be 'move-to-screen', next screen
    # Go to the next screen/state
    def _on_proceed(self, obj):
        self.apply_current_screen()

    def _on_back(self, obj):
        self._pop_last_screen()

    # switch-page should be after the current screen is reset
    def _on_switch_page(self, notebook, page, page_num):
        if self.current_screen.button_label:
            self.set_property('register-button-label',
                              self.current_screen.button_label)

    def done(self):
        self.change_screen(DONE_PAGE)

    def clear_screens(self):
        for screen in self._screens:
            screen.clear()

    # Handlers conntected to signals emitted from our Screens() in self._screens
    # Mostly just so they can then raise a RegisterWidget version of the signal
    # ie, any Screen() widget can emit a 'register-error', and we handle it here
    # and then emit a 'register-error' from RegisterWidget.

    def _on_screen_register_error(self, obj, msg, exc_info):
        """Handler for 'register-error' signals emitted from the Screens.

        Then emit one ourselves. Now emit a new signal for parent widget and
        self.do_register_error() to handle"""

        self.emit('register-error', msg, exc_info)

        # do_register_error handles it for this widget, so stop emission
        return False

    def _on_screen_register_message(self, obj, msg, msg_type=None):
        """Handler for 'register-message' signals emitted from the Screens.

        Then emit one ourselves. Now emit a new signal for parent widget and
        self.do_register_message() to handle"""
        self.emit('register-message', msg, msg_type)

        # do_register_error handles it for this widget, so stop emission
        return False

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

    def _on_screen_ready_change(self, obj, param):
        # This could potentially be self.current_sceen.get_property('ready')

        ready = obj.get_property('ready')

        # property for parent dialog to use for nav button sensitivity
        self.set_property('screen-ready', ready)

        if ready:
            self.handler_unblock(self.proceed_handler)
            self.handler_unblock(self.back_handler)
        else:
            self.handler_block(self.proceed_handler)
            self.handler_block(self.back_handler)

    # HMMM: If the connect/backend/async, and the auth info is composited into
    #       the same GObject, these could be class closure handlers
    def _on_username_password_change(self, *args):
        self.async_backend.set_user_pass(self.info.username, self.info.password)

    def _on_connection_info_change(self, *args):
        self.async_backend.update()

    def _on_activation_keys_change(self, obj, param):
        activation_keys = obj.get_property('activation-keys')

        # Unset backend from attempting to use basic auth
        if activation_keys:
            self.async_backend.set_user_pass()
            self.async_backend.update()

    def _on_details_label_txt_change(self, obj, value):
        """Update the label under the progress bar on progress page."""
        self.details_label.set_label("<small>%s</small>" %
                                     obj.get_property('details-label-txt'))

    def _on_register_state_change(self, obj, value):
        """Handler for the signal indicating we moved from registering to attaching.

        (the 'register-state' property changed), so update the
        related label on progress page."""
        state = obj.get_property('register-state')
        if state == RegisterState.REGISTERING:
            self.progress_label.set_markup(_("<b>Registering</b>"))
        elif state == RegisterState.SUBSCRIBING:
            self.progress_label.set_markup(_("<b>Attaching</b>"))

    # Various bits for starting/stopping the timer used to pulse the progress bar

    def start_progress_timer(self):
        if not self.progress_timer:
            self.progress_timer = ga_GObject.timeout_add(100, self._timeout_callback)

    def stop_progress_timer(self):
        if self.progress_timer:
            ga_GObject.source_remove(self.progress_timer)
            self.progress_timer = None

    def populate_screens(self):
        for screen in self._screens:
            screen.populate()

    def _timeout_callback(self):
        """Callback used to drive the progress bar 'pulse'."""
        self.register_progressbar.pulse()
        # return true to keep it pulsing
        return True


class RegisterDialog(widgets.SubmanBaseWidget):

    widget_names = ['register_dialog', 'register_dialog_main_vbox',
                    'register_details_label',
                    'back_button', 'register_button',
                    'close_button', 'progress_label']

    gui_file = "register_dialog"
    __gtype_name__ = 'RegisterDialog'

    def __init__(self, backend, callbacks=None):
        """
        Callbacks will be executed when registration status changes.
        """
        super(RegisterDialog, self).__init__()

        self.register_dialog.connect('hide', self.close)

        self.reg_info = RegisterInfo()

        # RegisterWidget is a oect, but not a Gtk.Widget
        self.register_widget = self.create_wizard_widget(backend, self.reg_info,
                                                         self.register_dialog)

        # But RegisterWidget.register_widget is a Gtk.Widget, so add it to
        # out container
        self.register_dialog_main_vbox.pack_start(self.register_widget.register_widget,
                                                  True, True, 0)

        # initial-setup will likely handle these itself
        self.register_widget.connect('finished', self.close)
        self.register_widget.connect('register-error', self.on_register_error)
        self.register_widget.connect('register-message', self.on_register_message)

        # update the 'next/register button on page change'
        self.register_widget.connect('notify::register-button-label',
                                self._on_register_button_label_change)
        self.register_widget.connect('notify::screen-ready',
                                     self._on_register_screen_ready_change)

        # reset/clear/setup
        #self.register_widget.initialize()

        self.register_button.connect('clicked', self._on_register_button_clicked)
        self.back_button.connect('clicked', self._on_back_button_clicked)

        # TODO: Hook this up to a RegisterWidget 'cancel' handler, when there is one
        self.close_button.connect('clicked', self.close)

        # update window title on register state changes
        self.reg_info.connect('notify::register-state',
                               self._on_register_state_change)

        self.window = self.register_dialog
        self.back_button.set_sensitive(False)

    def create_wizard_widget(self, backend, reg_info, parent_window):
        """Create a RegisterWidget or subclass and use it for our content."""

        # FIXME: Need better error handling in general, but it's kind of
        # annoying to have to pass the top level widget all over the place
        register_widget = RegisterWidget(backend=backend,
                                         reg_info=reg_info,
                                         parent_window=parent_window)

        return register_widget

    def initialize(self):
        self.register_widget.initialize()

    def show(self):
        # initial-setup module skips this, since it results in a
        # new top level window that isn't reparented to the initial-setup
        # screen.
        self.register_dialog.show()

    def close(self, button):
        self.register_dialog.destroy()
        return False

    def on_register_message(self, obj, msg, msg_type=None):
        # NOTE: We ignore the message type here, but initial-setup wont.
        gui_utils.show_info_window(msg)

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
        message = gui_utils.format_exception(exc_info, msg)
        self.error_dialog(obj, message)

    def error_dialog(self, obj, msg):
        gui_utils.show_error_window(msg)

    def _on_back_button_clicked(self, obj):
        self.register_widget.emit('back')
        self.back_button.set_sensitive(not self.register_widget.applied_screen_history.is_empty())

    def _on_register_screen_ready_change(self, obj, value):
        ready = self.register_widget.current_screen.get_property('ready')
        self.register_button.set_sensitive(ready)
        self.back_button.set_sensitive(ready and not self.register_widget.applied_screen_history.is_empty())

    def _on_register_button_clicked(self, button):
        self.register_widget.emit('proceed')

    def _on_register_state_change(self, obj, value):
        state = obj.get_property('register-state')
        if state == RegisterState.REGISTERING:
            self.register_dialog.set_title(_("System Registration"))
        elif state == RegisterState.SUBSCRIBING:
            self.register_dialog.set_title(_("Subscription Attachment"))

    def _on_register_button_label_change(self, obj, value):
        register_label = obj.get_property('register-button-label')
        if register_label:
            self.register_button.set_label(register_label)


class AutoBindWidget(RegisterWidget):
    __gtype_name__ = "AutobindWidget"

    initial_screen = FIND_SUBSCRIPTIONS

    def __init__(self, backend, reg_info=None,
                 parent_window=None):
        super(AutoBindWidget, self).__init__(backend, reg_info,
                                             parent_window)

    def choose_initial_screen(self):
        self.current_screen.emit('move-to-screen', FIND_SUBSCRIPTIONS)
        self.register_widget.show_all()
        return False


class FirstbootWidget(RegisterWidget):
    # A RegisterWidget for use in firstboot.
    # This widget, along with the PerformUnregisterScreen, will ensure that
    # all screens are shown, and the user is allowed to register again.
    __gtype_name__ = "FirstbootWidget"

    initial_screen = CHOOSE_SERVER_PAGE

    def choose_initial_screen(self):
        self.current_screen.emit('move-to-screen', self.initial_screen)
        self.register_widget.show_all()
        return False


class AutobindWizardDialog(RegisterDialog):
    __gtype_name__ = "AutobindWizardDialog"

    def __init__(self, backend):
        super(AutobindWizardDialog, self).__init__(backend)

    def create_wizard_widget(self, backend, reg_info, parent_window):

        # FIXME: Need better error handling in general, but it's kind of
        # annoying to have to pass the top level widget all over the place
        autobind_widget = AutoBindWidget(backend=backend,
                                         reg_info=reg_info,
                                         parent_window=parent_window)

        return autobind_widget


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

    __gsignals__ = {'stay-on-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, []),
                    'register-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                          None, []),
                    'attach-finished': (ga_GObject.SignalFlags.RUN_FIRST,
                                        None, []),
                    'register-message': (ga_GObject.SignalFlags.RUN_FIRST,
                                         None, (ga_GObject.TYPE_PYOBJECT,
                                                ga_GObject.TYPE_PYOBJECT)),
                    'register-error': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, (ga_GObject.TYPE_PYOBJECT,
                                              ga_GObject.TYPE_PYOBJECT)),
                    'move-to-screen': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, (int,))}

    ready = ga_GObject.property(type=bool, default=True)

    def __init__(self, reg_info, async_backend, parent_window):
        super(Screen, self).__init__()

        self.pre_message = ""
        self.button_label = _("_Register")
        self.needs_gui = True
        self.index = -1
        # REMOVE self._error_screen = self.index

        self.parent_window = parent_window
        self.info = reg_info
        self.async_backend = async_backend

    def stay(self):
        self.emit('stay-on-screen')
        self.set_properties('ready', True)

    def pre(self):
        self.pre_done()
        return False

    def back_handler(self):
        return

    def pre_done(self):
        self.set_property('ready', True)

    # do whatever the screen indicates, and emit any signals indicating where
    # to move to next. apply() should not return anything.
    def apply(self):
        return True

    def post(self):
        pass

    def clear(self):
        pass

    def populate(self):
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
                    'register-message': (ga_GObject.SignalFlags.RUN_FIRST,
                                         None, (ga_GObject.TYPE_PYOBJECT,
                                                ga_GObject.TYPE_PYOBJECT)),
                    'register-error': (ga_GObject.SignalFlags.RUN_FIRST,
                                       None, (ga_GObject.TYPE_PYOBJECT,
                                              ga_GObject.TYPE_PYOBJECT)),
                    'certs-updated': (ga_GObject.SignalFlags.RUN_FIRST,
                                      None, [])}

    ready = ga_GObject.property(type=bool, default=True)

    def __init__(self, reg_info, async_backend, parent_window):
        ga_GObject.GObject.__init__(self)

        self.parent_window = parent_window
        self.info = reg_info
        self.async_backend = async_backend

        self.button_label = None
        self.needs_gui = False
        self.pre_message = "Default Pre Message"

    # FIXME: a do_register_error could be used for logging?
    #        Otherwise it's up to the parent dialog to do the logging.

    def pre(self):
        self.pre_done()
        return True

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)

    def pre_done(self):
        self.set_property('ready', True)

    def apply(self):
        self.emit('move-to-screen')
        return True

    def post(self):
        pass

    def clear(self):
        pass

    def populate(self):
        pass

    def stay(self):
        self.emit('stay-on-screen')
        self.set_property('ready', True)


class PerformRegisterScreen(NoGuiScreen):
    screen_enum = PERFORM_REGISTER_PAGE

    def __init__(self, reg_info, async_backend, parent_window):
        super(PerformRegisterScreen, self).__init__(reg_info, async_backend, parent_window)

    def _on_registration_finished_cb(self, new_account, error=None):
        if error is not None:
            self.emit('register-error', REGISTER_ERROR, error)
            # TODO: register state
            self.pre_done()
            return

        # trigger a id cert reload
        self.emit('identity-updated')

        # NOTE: Assume we want to try to upload package profile even with
        # activation keys
        self.emit('move-to-screen', UPLOAD_PACKAGE_PROFILE_PAGE)
        # Done with the registration stuff, now on to attach
        # NOTE: the signal register-finished should come after any
        # move-to-screen signals to ensure we end up at the done screen if we
        # end up skipping the attach step. See bz 1372673
        self.emit('register-finished')
        # TODO: After register-finished, there is still a whole
        # series of steps before we start attaching, most of which
        # would be useful to have async...
        #  - persisting consumer certs
        #  - reloading the new identity
        #  - uploading package profile
        #  - potentially getting/setting SLA
        #  - reset'ing cert sorter and friends
        self.pre_done()
        return

    def pre(self):
        msg = _("Registering to owner: %s environment: %s") % \
                 (self.info.get_property('owner-key'),
                  self.info.get_property('environment'))
        self.info.set_property('register-status', msg)

        self.async_backend.register_consumer(self.info.get_property('consumername'),
                                     self.info.get_property('owner-key'),
                                     self.info.get_property('environment'),
                                     self.info.get_property('activation-keys'),
                                     self._on_registration_finished_cb)

        return True

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)


class PerformUnregisterScreen(NoGuiScreen):

    screen_enum = PERFORM_UNREGISTER_PAGE

    def _on_unregistration_finished_cb(self, retval, error=None):
        if error is not None:
            self.emit('register-error',
                      _('Unable to unregister'),
                      error)

        # clean all local data regardless of the success of the network unregister
        managerlib.clean_all_data(backup=False)

        self.emit('move-to-screen', OWNER_SELECT_PAGE)

        self.pre_done()
        return

    def pre(self):
        msg = _("Unregistering")
        self.info.set_property('register-status', msg)
        self.info.set_property('details-label-txt', msg)
        self.info.set_property('register-state', RegisterState.REGISTERING)

        # Unregister if we have gotten here with a valid identity and have old server info
        if self.info.identity.is_valid() and self.info.get_property('server-info') and self.info.get_property('enable-unregister'):
            self.async_backend.unregister_consumer(self.info.identity.uuid,
                                           self.info.get_property('server-info'),
                                           self._on_unregistration_finished_cb)
            return True

        self.emit('move-to-screen', OWNER_SELECT_PAGE)
        self.pre_done()
        return False

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)


# After registering, we can upload package profiles.
# But... we don't have to do it immed after registering, it could
# be in a later screen or a back ground task (user flow isn't
# altered by results of package profile, and it's kind of slow, it
# could happen in it's own thread while we go through other screens
class PerformPackageProfileSyncScreen(NoGuiScreen):
    screen_enum = UPLOAD_PACKAGE_PROFILE_PAGE

    def __init__(self, reg_info, async_backend, parent_window):
        super(PerformPackageProfileSyncScreen, self).__init__(reg_info, async_backend, parent_window)
        self.pre_message = _("Uploading package profile")

    def _on_update_package_profile_finished_cb(self, result, error=None):
        if error is not None:
            self.emit('register-error',
                      REGISTER_ERROR,
                      error)

            # Allow failure on package profile uploads
            self.emit('move-to-screen', FIND_SUBSCRIPTIONS)
            self.pre_done()
            return

        try:
            if self.info.get_property('activation-keys'):
                self.emit('move-to-screen', REFRESH_SUBSCRIPTIONS_PAGE)
            # could/should we rely on RegisterWidgets register-finished to handle this?
            # ie, detecting when we are 'done' registering
            elif self.info.get_property('skip-auto-bind'):
                pass
            # Or more likely, the server doesn't support package profile updates
            # so we got a result of 0 and no error
            else:
                self.emit('move-to-screen', FIND_SUBSCRIPTIONS)
        except Exception as e:
            self.emit('register-error', REGISTER_ERROR, e)

        self.pre_done()
        return

    def pre(self):
        self.async_backend.update_package_profile(self.info.identity.uuid,
                                          self._on_update_package_profile_finished_cb)
        return True


class PerformSubscribeScreen(NoGuiScreen):
    screen_enum = PERFORM_SUBSCRIBE_PAGE

    def __init__(self, reg_info, async_backend, parent_window):
        super(PerformSubscribeScreen, self).__init__(reg_info, async_backend, parent_window)
        self.pre_message = _("Attaching subscriptions")

    def _on_subscribing_finished_cb(self, unused, error=None):
        if error is not None:
            message = _("Error subscribing: %s")
            self.emit('register-error', message, error)
            self.pre_done()
            return

        self.emit('certs-updated')
        self.emit('attach-finished')
        self.pre_done()

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.info.set_property('register-state', RegisterState.SUBSCRIBING)
        self.async_backend.subscribe(self.info.identity.uuid,
                             self.info.get_property('current-sla'),
                             self.info.get_property('dry-run-result'),
                             self._on_subscribing_finished_cb)

        return True


class ConfirmSubscriptionsScreen(Screen):
    """ Confirm Subscriptions GUI Window """
    screen_enum = CONFIRM_SUBS_PAGE
    widget_names = Screen.widget_names + ['subs_treeview', 'back_button']

    gui_file = "confirmsubs"

    def __init__(self, reg_info, async_backend, parent_window):
        super(ConfirmSubscriptionsScreen, self).__init__(reg_info, async_backend, parent_window)
        self.button_label = _("_Attach")

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
        return True

    def set_model(self):
        dry_run_result = self.info.get_property('dry-run-result')

        # Make sure that the store is cleared each time
        # the data is loaded into the screen.
        self.store.clear()

        if not dry_run_result:
            return

        for pool_quantity in dry_run_result.json:
            self.store.append([pool_quantity['pool']['productName'],
                              PoolWrapper(pool_quantity['pool']).is_virt_only(),
                              str(pool_quantity['quantity'])])

    def pre(self):
        self.set_model()
        self.pre_done()
        return False


class FindSuitableSubscriptions(NoGuiScreen):
    """
    A brief panel that finds suitable subscriptions based on the specified SLA.
    """
    screen_enum = FIND_SUBSCRIPTIONS

    def __init__(self, reg_info, async_backend, parent_window):
        super(FindSuitableSubscriptions, self).__init__(reg_info, async_backend, parent_window)
        self.pre_message = _("Finding suitable subscriptions")

    def apply(self):
        self.emit('move-to-screen', CONFIRM_SUBS_PAGE)
        return True

    def _on_find_subscriptions_cb(self, result, error=None):
        if error is not None:
            if isinstance(error[1], ServiceLevelNotSupportedException):
                msg = _("Unable to auto-attach, server does not support service levels.")
                self.emit('register-error', msg, None)
                # HMM: if we make the ok a register-error as well, we may get
                # wacky ordering if the register-error is followed immed by a
                # register-finished?
                self.emit('attach-finished')
                self.pre_done()
                return
            elif isinstance(error[1], NoProductsException):
                msg = _("No installed products on system. No need to attach subscriptions at this time.")
                self.emit('register-message', msg, ga_Gtk.MessageType.INFO)
                self.emit('attach-finished')
                self.pre_done()
                return
            elif isinstance(error[1], AllProductsCoveredException):
                msg = _("All installed products are covered by valid entitlements. "
                        "No need to attach subscriptions at this time.")
                self.emit('register-message', msg, ga_Gtk.MessageType.INFO)
                self.emit('attach-finished')
                self.pre_done()
                return
            elif isinstance(error[1], GoneException):
                # FIXME: shoudl we log here about deleted consumer or
                #        did we do that when we created GoneException?
                msg = _("Consumer has been deleted.")
                self.emit('register-error', msg, None)
                self.emit('attach-finished')
                self.pre_done()
                return
            elif isinstance(error[1], RestlibException) and error[1].code == "401":
                # If we get here with a 401, we are using consumer cert auth
                # so that means we are likely connecting to the wrong server
                # url, since unregistered consumers talking to the correct
                # serverurl would 410. Short of changing serverurl or re-registering
                # there isn't much we can do to fix that.
                msg = error[1].error_msg
                # TODO: Provide a better error message reflecting above comment
                self.emit('register-error', msg, None)
                self.emit('attach-finished')
                self.pre_done()
                return
            else:
                log.exception(error)
                self.emit('register-error', _("Error subscribing: %s"), error)
                self.emit('attach-finished')
                self.pre_done()
                return

        # We have a lot of SLA options.
        # current_sla = the sla that the Consumer from candlepin has
        #               set in its 'serviceLevel' attribute
        # info.preferred_sla is a ks info provided SLA that we should use if
        #  available.

        (current_sla, unentitled_products, dry_run_data) = result

        self.info.set_property('current-sla', current_sla)

        if dry_run_data is not None:
            # If system already had a service level, we can hit this point
            # when we cannot fix any unentitled products:
            if current_sla is not None and not self._can_add_more_subs(current_sla, dry_run_data):
                # Provide different messages for initial-setup and
                # subscription-manager-gui
                if self.parent_window.__class__.__name__ == 'SpokeWindow':
                    msg = _("You will need to use Red Hat Subscription "
                            "Manager to manually attach subscriptions to this "
                            "system after completing setup.")
                else:
                    msg = _("No available subscriptions at "
                            "the current service level: %s. "
                            "Please use the \"All Available "
                            "Subscriptions\" tab to manually "
                            "attach subscriptions.") % current_sla
                # TODO: add 'attach' state
                self.emit('register-error', msg, REGISTERED_UNATTACHED)
                self.emit('attach-finished')
                self.pre_done()
                return

            self.info.set_property('dry-run-result', dry_run_data)

            self.emit('move-to-screen', CONFIRM_SUBS_PAGE)
            self.pre_done()
            return
        else:
            log.debug("No suitable subscriptions found.")
            if self.parent_window.__class__.__name__ == 'SpokeWindow':
                msg = _("You will need to use Red Hat Subscription "
                        "Manager to manually attach subscriptions to this "
                        "system after completing setup.")
            else:
                msg = _("No service level will cover all "
                        "installed products. Please manually "
                        "subscribe using multiple service levels "
                        "via the \"All Available Subscriptions\" "
                        "tab or purchase additional subscriptions.")
            # TODO: add 'registering/attaching' state info
            self.emit('register-error', msg, REGISTERED_UNATTACHED)
            self.emit('attach-finished')
            self.pre_done()

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.info.set_property('register-state', RegisterState.SUBSCRIBING)
        self.info.identity.reload()

        self.async_backend.find_subscriptions(self.info.identity.uuid,
                                              self._on_find_subscriptions_cb)
        return True

    @staticmethod
    def _can_add_more_subs(current_sla, dry_run_data):
        """
        Check if a system that already has a selected sla can get more
        entitlements at their sla level
        """
        if current_sla is not None:
            return len(dry_run_data.json) > 0
        return False


class EnvironmentScreen(Screen):
    widget_names = Screen.widget_names + ['environment_treeview']
    gui_file = "environment"

    def __init__(self, reg_info, async_backend, parent_window):
        super(EnvironmentScreen, self).__init__(reg_info, async_backend, parent_window)

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
            self.pre_done()
            return

        if not environments:
            self.set_environment(None)
            self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
            self.pre_done()
            return

        envs = [(env['id'], env['name']) for env in environments]
        if len(envs) == 1:
            self.set_environment(envs[0][0])
            self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
            self.pre_done()
            return

        else:
            self.set_model(envs)
            self.stay()
            self.pre_done()
            return

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async_backend.get_environment_list(self.info.get_property('owner-key'),
                                                self._on_get_environment_list_cb)
        return True

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)

    def apply(self):
        model, tree_iter = self.environment_treeview.get_selection().get_selected()
        self.set_environment(model.get_value(tree_iter, 0))
        self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
        return True

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

    def __init__(self, reg_info, async_backend, parent_window):
        super(OrganizationScreen, self).__init__(reg_info, async_backend, parent_window)

        self.pre_message = _("Fetching list of possible organizations")

        renderer = ga_Gtk.CellRendererText()
        column = ga_Gtk.TreeViewColumn(_("Organization"), renderer, text=1)
        self.owner_treeview.set_property("headers-visible", False)
        self.owner_treeview.append_column(column)

    def _on_get_owner_list_cb(self, owners, error=None):
        if error is not None:
            self.emit('register-error', REGISTER_ERROR, error)
            self.pre_done()
            return

        owners = [(owner['key'], owner['displayName']) for owner in owners]
        # Sort by display name so the list doesn't randomly change.
        owners = sorted(owners, key=lambda item: item[1])

        if len(owners) == 0:
            msg = _("<b>User %s is not able to register with any orgs.</b>") % \
                    self.info.get_property('username')
            self.emit('register-error', msg, None)
            self.pre_done()
            return

        if len(owners) == 1:
            owner_key = owners[0][0]
            self.info.set_property('owner-key', owner_key)
            # only one org, use it and skip the org selection screen
            self.emit('move-to-screen', ENVIRONMENT_SELECT_PAGE)
            self.pre_done()
            return

        else:
            self.set_model(owners)
            self.stay()
            self.pre_done()
            return

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.async_backend.get_owner_list(self.info.get_property('username'),
                                          self._on_get_owner_list_cb)
        return True

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)

    def apply(self):
        # check for selection exists
        model, tree_iter = self.owner_treeview.get_selection().get_selected()
        owner_key = model.get_value(tree_iter, 0)
        self.info.set_property('owner-key', owner_key)
        self.emit('move-to-screen', ENVIRONMENT_SELECT_PAGE)
        return True

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
    screen_enum = CREDENTIALS_PAGE

    def __init__(self, reg_info, async_backend, parent_window):
        super(CredentialsScreen, self).__init__(reg_info, async_backend, parent_window)

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
                      ga_Gtk.MessageType.ERROR)

            self.consumer_name.grab_focus()
            return False
        return True

    def _validate_account(self):
        # validate / check user name
        if self.account_login.get_text().strip() == "":
            self.emit('register-error',
                      _("You must enter a login."),
                      ga_Gtk.MessageType.ERROR)

            self.account_login.grab_focus()
            return False

        if self.account_password.get_text().strip() == "":
            self.emit('register-error',
                      _("You must enter a password."),
                      ga_Gtk.MessageType.ERROR)

            self.account_password.grab_focus()
            return False
        return True

    def populate(self):
        if self.info.get_property('username'):
            self.account_login.set_text(self.info.get_property('username'))

        if self.info.get_property('password'):
            self.account_password.set_text(self.info.get_property('password'))

        if self.info.get_property('consumername'):
            self.consumer_name.set_text(self.info.get_property('consumername'))

        if self.info.get_property('skip-auto-bind'):
            self.skip_auto_bind.set_active(self.info.get_property('skip-auto-bind'))

    def pre(self):
        msg = _("This system is currently not registered.")
        self.info.set_property('register-status', msg)
        self.info.set_property('details-label-txt', self.pre_message)
        self.account_login.grab_focus()
        self.pre_done()
        return False

    def apply(self):
        self.stay()

        username = self.account_login.get_text().strip()
        password = self.account_password.get_text().strip()
        consumername = self.consumer_name.get_text()
        skip_auto_bind = self.skip_auto_bind.get_active()

        if not self._validate_consumername(consumername):
            return False

        if not self._validate_account():
            return False

        self.info.set_property('username', username)
        self.info.set_property('password', password)
        self.info.set_property('skip-auto-bind', skip_auto_bind)
        self.info.set_property('consumername', consumername)
        self.emit('move-to-screen', PERFORM_UNREGISTER_PAGE)
        return True

    def clear(self):
        self.account_login.set_text("")
        self.account_password.set_text("")
        self.consumer_name.set_text("")
        self._initialize_consumer_name()
        self.skip_auto_bind.set_active(False)

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)


class ActivationKeyScreen(Screen):
    screen_enum = ACTIVATION_KEY_PAGE
    widget_names = Screen.widget_names + [
        'activation_key_entry',
        'organization_entry',
        'consumer_entry',
    ]
    gui_file = "activation_key"

    def __init__(self, reg_info, async_backend, parent_window):
        super(ActivationKeyScreen, self).__init__(reg_info, async_backend, parent_window)
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
            return False

        if not self._validate_activation_keys(activation_keys):
            return False

        if not self._validate_consumername(consumername):
            return False

        self.info.set_property('consumername', consumername)
        self.info.set_property('owner-key', owner_key)
        self.info.set_property('activation-keys', activation_keys)

        self.emit('move-to-screen', PERFORM_REGISTER_PAGE)
        return True

    def _split_activation_keys(self, entry):
        keys = re.split(',\s*|\s+', entry)
        return [x for x in keys if x]

    def _validate_owner_key(self, owner_key):
        if not owner_key:
            self.emit('register-error',
                      _("You must enter an organization."),
                      ga_Gtk.MessageType.ERROR)

            self.organization_entry.grab_focus()
            return False
        return True

    def _validate_activation_keys(self, activation_keys):
        if not activation_keys:
            self.emit('register-error',
                      _("You must enter an activation key."),
                      ga_Gtk.MessageType.ERROR)

            self.activation_key_entry.grab_focus()
            return False
        return True

    def _validate_consumername(self, consumername):
        if not consumername:
            self.emit('register-error',
                      _("You must enter a system name."),
                      ga_Gtk.MessageType.ERROR)

            self.consumer_entry.grab_focus()
            return False
        return True

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.organization_entry.grab_focus()
        self.pre_done()
        return False

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)


class RefreshSubscriptionsScreen(NoGuiScreen):

    def __init__(self, reg_info, async_backend, parent_window):
        super(RefreshSubscriptionsScreen, self).__init__(reg_info, async_backend, parent_window)
        self.pre_message = _("Attaching subscriptions")

    def _on_refresh_cb(self, msg, error=None):
        if error is not None:
            self.emit('register-error',
                      _("Error subscribing: %s"),
                      error)
            # TODO: register state
            self.pre_done()
            return

        self.emit('attach-finished')
        self.pre_done()

    def pre(self):
        self.info.set_property('details-label-txt', self.pre_message)
        self.info.set_property('register-state', RegisterState.SUBSCRIBING)
        self.async_backend.refresh(self._on_refresh_cb)
        return True


class ChooseServerScreen(Screen):
    widget_names = Screen.widget_names + ['server_entry', 'proxy_frame',
                                          'default_button', 'choose_server_label',
                                          'activation_key_checkbox']
    gui_file = "choose_server"

    def __init__(self, reg_info, async_backend, parent_window):
        super(ChooseServerScreen, self).__init__(reg_info, async_backend, parent_window)

        self.button_label = _("_Next")

        callbacks = {
            "on_default_button_clicked": self._on_default_button_clicked,
            "on_proxy_button_clicked": self._on_proxy_button_clicked,
        }

        self.connect_signals(callbacks)

        self.network_config_dialog = networkConfig.NetworkConfigDialog()

    def _on_default_button_clicked(self, widget):
        # Default port and prefix are fine, so we can be concise and just
        # put the hostname for RHN:
        self.server_entry.set_text("%s:%s%s" % (base_config.DEFAULT_HOSTNAME,
            base_config.DEFAULT_PORT,
            base_config.DEFAULT_PREFIX))

    def _on_proxy_button_clicked(self, widget):
        # proxy dialog may attempt to resolve proxy and server names, so
        # bump the resolver as well.
        self.reset_resolver()

        self.network_config_dialog.show()

    def reset_resolver(self):
        try:
            reset_resolver()
        except Exception as e:
            log.warn("Error from reset_resolver: %s", e)

    def populate(self):
        self.set_server_entry(self.info.get_property('hostname'),
                              self.info.get_property('port'),
                              self.info.get_property('prefix'))

        activation_keys = self.info.get_property('activation_keys')

        if activation_keys:
            self.activation_key_checkbox.set_active(True)
        else:
            self.activation_key_checkbox.set_active(False)

        return False

    def clear(self):
        pass

    def apply(self):
        self.stay()
        server = self.server_entry.get_text()
        try:
            (hostname, port, prefix) = parse_server_info(server, conf)
            self.info.set_property('hostname', hostname)
            self.info.set_property('port', port)
            self.info.set_property('prefix', prefix)
            self.info.set_property('use_activation_keys', self.activation_key_checkbox.get_active())
        except ServerUrlParseError:
            self.emit('register-error',
                      _("Please provide a hostname with optional port and/or prefix: "
                        "hostname[:port][/prefix]"),
                      None)
            return False
        self.emit('move-to-screen', VALIDATE_SERVER_PAGE)
        return True

    def set_server_entry(self, hostname, port, prefix):
        # No need to show port and prefix for hosted:
        if hostname == base_config.DEFAULT_HOSTNAME:
            self.server_entry.set_text(base_config.DEFAULT_HOSTNAME)
        else:
            self.server_entry.set_text("%s:%s%s" % (hostname,
                                       port, prefix))

    def pre(self):
        self.pre_done()
        return False


class ValidateServerScreen(NoGuiScreen):
    screen_enum = VALIDATE_SERVER_PAGE

    def _on_validate_server(self, info, error=None):
        if info:
            hostname, port, prefix, is_valid = info
        if error is not None:
            if isinstance(error, tuple):
                if isinstance(error[1], MissingCaCertException):
                    self.emit('register-error',
                      _("CA certificate for subscription service has not been installed."),
                      None)
                if isinstance(error[1], ProxyException):
                    self.emit('register-error',
                      _("Proxy connection failed, please check your settings."),
                      None)
            else:
                self.emit('register-error',
                          _("Error validating server: %s"),
                          error)
            self.pre_done()
            return
        elif not is_valid:
            self.emit('register-error',
                      _("Unable to reach the server at %s:%s%s") %
                      (hostname, port, prefix),
                      None)
            self.pre_done()
            return
        conf['server']['hostname'] = hostname
        conf['server']['port'] = port
        conf['server']['prefix'] = prefix

        self.pre_done()
        if self.info.get_property('use_activation_keys'):
            self.emit('move-to-screen', ACTIVATION_KEY_PAGE)
            return

        else:
            self.emit('move-to-screen', CREDENTIALS_PAGE)
            self.info.set_property('activation-keys', None)
            return

    def pre(self):
        msg = _("Validating connection")
        self.info.set_property('register-status', msg)
        self.info.set_property('details-label-txt', msg)
        self.info.set_property('register-state', RegisterState.REGISTERING)

        hostname = self.info.get_property('hostname')
        port = self.info.get_property('port')
        prefix = self.info.get_property('prefix')
        self.async_backend.validate_server(hostname, port=port, prefix=prefix, callback=self._on_validate_server)
        return True

    def back_handler(self):
        self.info.set_property('register-state', RegisterState.REGISTERING)


class AsyncBackend(object):

    def __init__(self, backend):
        self.backend = backend
        self.plugin_manager = require(PLUGIN_MANAGER)
        self.ent_dir = require(ENT_DIR)
        self.queue = queue.Queue()
        self._threads = []

    def block_until_complete(self):
        """Complete outstanding requests."""
        for thread in self._threads:
            thread.join()

    def _start_thread(self, thread):
        thread.start()
        self._threads.append(thread)

    def update(self):
        self.backend.update()

    def set_user_pass(self, username=None, password=None):
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
        except queue.Empty:
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
                log.debug("Server supports environments, checking for "
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

    def _register_consumer(self, name, owner, env, activation_keys, callback):
        """
        method run in the worker thread.
        """
        try:
            # We've got several steps here that all happen in this thread
            #
            # Behing a 'gather system info' screen?
            #  get installed prods
            #  get facts (local collection or facts service)
            #
            # run pre_register plugin (in main?)
            # ACTUALLY REGISTER (the network call)
            # run post_register plugin (in main?)
            #
            # persist identity
            #  # These could move to call back
            # reload identity
            # persist new installed products info ?
            # persist facts cache (for now)
            # persist new consumer cert
            # # already branch to make this a seperate page/thread
            # update package profile (ie, read rpmdb, slow...)
            #   which can make a package profile upload request
            # restart virt-who   (wat?)
            #
            # We should probably split that up some.
            #
            installed_mgr = require(INSTALLED_PRODUCTS_MANAGER)

            facts = require(FACTS)

            # Note: for now, this is blocking. Maybe we should do it
            #       in the gui mainthread async and pass it in?

            facts_dict = facts.get_facts()

            # TODO: We end up calling plugins from threads, which is a little weird.
            #       Seems like a reasonable place to go back to main thread, run the
            #       plugin, run the network request in a thread, come back to main, run post
            #       plugin, etc.

            self.plugin_manager.run("pre_register_consumer", name=name,
                                    facts=facts_dict)

            syspurpose = syspurposelib.read_syspurpose()

            cp = self.backend.cp_provider.get_basic_auth_cp()
            retval = cp.registerConsumer(name=name, facts=facts_dict,
                                         owner=owner, environment=env,
                                         keys=activation_keys,
                                         installed_products=installed_mgr.format_for_server(),
                                         role=syspurpose.get('role'),
                                         addons=syspurpose.get('addons') or [],
                                         service_level=syspurpose.get('service_level_agreement') or '',
                                         usage=syspurpose.get('usage')
                                         )

            self.plugin_manager.run("post_register_consumer", consumer=retval,
                                    facts=facts_dict)

            # TODO: split persisting info into it's own thread
            require(IDENTITY).reload()

            # Facts and installed products went out with the registration
            # request, manually write caches to disk:
            facts.write_cache()
            installed_mgr.write_cache()

            # Write the identity cert to disk
            managerlib.persist_consumer_cert(retval)
            self.backend.update()

            # FIXME: I don't think we need this at all
            # We have new credentials, restart virt-who
            restart_virt_who()

            # Force all the cert dir backends to update, but mostly
            # force the identity cert monitor to run, which will
            # also update Backend. It also blocks until the new
            # identity is reloaded, so we don't start the findsubscriptions
            # screen before it.
            self.backend.cs.force_cert_check()

            self.queue.put((callback, retval, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _update_package_profile(self, uuid, callback):
        try:
            cp = self.backend.cp_provider.get_consumer_auth_cp()

            # NOTE: profile update is using consumer auth with the
            # new_consumer identity cert, not basic auth as before.
            profile_mgr = require(PROFILE_MANAGER)
            retval = profile_mgr.update_check(cp, uuid)

            self.queue.put((callback, retval, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _subscribe(self, uuid, current_sla, dry_run_result, callback):
        """
        Subscribe to the selected pools.
        """
        try:
            log.debug("Binding to subscriptions at service level: %s" %
                    dry_run_result.service_level)
            expected_pool_ids = set()
            for pool_quantity in dry_run_result.json:
                pool_id = pool_quantity['pool']['id']
                expected_pool_ids.add(pool_id)
                quantity = pool_quantity['quantity']

                log.debug("  pool %s quantity %s" % (pool_id, quantity))

                try:
                    attach_service = attach.AttachService(self.backend.cp_provider.get_consumer_auth_cp())
                    attach_service.attach_pool(pool_id, quantity)
                except RestlibException as e:
                    # TODO when candlepin emits error codes, only continue for "already subscribed"
                    log.warn("Error while attaching subscription: %s", e)

            # FIXME: this should be a different asyncBackend task
            managerlib.fetch_certificates(self.backend.certlib)

            attached_pool_ids = [ent.pool.id for ent in self.ent_dir.list_with_content_access()]
            for pool_id in expected_pool_ids:
                if pool_id not in attached_pool_ids:
                    raise Exception(_("Not all expected subscriptions were attached, see /var/log/rhsm/rhsm.log for more details."))

            # make GUI aware of updated certs (instead of waiting for periodic task to detect it)
            self.backend.cs.force_cert_check()

        except Exception:
            # Going to try to update certificates just in case we errored out
            # mid-way through a bunch of binds:
            # FIXME: emit update-ent-certs signal
            try:
                managerlib.fetch_certificates(self.backend.certlib)
            except Exception as cert_update_ex:
                log.error("Error updating certificates after error:")
                log.exception(cert_update_ex)
            self.queue.put((callback, None, sys.exc_info()))
            return
        self.queue.put((callback, None, None))

    # This guy is really ugly to run in a thread, can we run it
    # in the main thread with just the network stuff threaded?

    # get_consumer
    # update_consumer
    #  action_client
    #    update_installed_products
    #    update_facts
    #    update_other_action_client_stuff
    # get_dry_run_bind for sla
    def _find_suitable_subscriptions(self, consumer_uuid):

        # FIXME:
        self.backend.update()

        consumer_json = self.backend.cp_provider.get_consumer_auth_cp().getConsumer(
                consumer_uuid)

        if 'serviceLevel' not in consumer_json:
            raise ServiceLevelNotSupportedException()

        # This is often "", set to None in that case:
        current_sla = consumer_json['serviceLevel'] or None

        if len(self.backend.cs.installed_products) == 0:
            raise NoProductsException()

        if len(self.backend.cs.valid_products) == len(self.backend.cs.installed_products) and \
                len(self.backend.cs.partial_stacks) == 0 and self.backend.cs.system_status != 'partial':
            raise AllProductsCoveredException()

        dry_run_response = None

        # eek, in a thread
        action_client = ActionClient()
        action_client.update()

        if current_sla:
            log.debug("Using system's current service level: %s" % current_sla)
            # TODO: what kind of madness would happen if we did a couple of
            # these in parallel in seperate threads?
            dry_run_json = self.backend.cp_provider.get_consumer_auth_cp().dryRunBind(consumer_uuid, current_sla)

            # FIXME: are we modifying cert_sorter (self.backend.cs) state here?
            # FIXME: it's only to get the unentitled products list, can pass
            #        that in
            dry_run = DryRunResult(current_sla, dry_run_json, self.backend.cs)

            # If we have a current SLA for this system, we do not need
            # all products to be covered by the SLA to proceed through
            # this wizard:
            dry_run_response = dry_run
        else:
            log.debug("No service level was specified")
            dry_run_json = self.backend.cp_provider.get_consumer_auth_cp().dryRunBind(consumer_uuid, None)
            dry_run = DryRunResult(None, dry_run_json, self.backend.cs)

            if dry_run.covers_required_products():
                dry_run_response = dry_run

        # why do we call cert_sorter stuff in the return?
        return current_sla, list(self.backend.cs.unentitled_products.values()), dry_run_response

    def _find_subscriptions(self, consumer_uuid, callback):
        """
        method run in the worker thread.
        """
        try:
            suitable_subscriptions = self._find_suitable_subscriptions(consumer_uuid)
            self.queue.put((callback, suitable_subscriptions, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _refresh(self, callback):
        try:
            managerlib.fetch_certificates(self.backend.certlib)
            self.queue.put((callback, None, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def __unregister_consumer(self, consumer_uuid, server_info):
        # Method to actually do the unregister bits from the server
        try:
            old_cp = UEPConnection(**server_info)
            old_cp.unregisterConsumer(consumer_uuid)
        except Exception as e:
            log.exception(e)
            # Reraise any exception as a RemoteUnregisterException
            # This will be passed all the way back to the parent window
            raise RemoteUnregisterException

    def _unregister_consumer(self, consumer_uuid, server_info, callback):
        try:
            self.__unregister_consumer(consumer_uuid, server_info)
            self.queue.put((callback, None, None))
        except Exception:
            self.queue.put((callback, None, sys.exc_info()))

    def _validate_server(self, hostname, port, prefix, callback):
        try:
            reset_resolver()
        except Exception as e:
            log.warn("Error from reset_resolver: %s", e)
        try:
            conn = UEPConnection(hostname, int(port), prefix)
            is_valid = is_valid_server_info(conn)
            self.queue.put((callback, (hostname, port, prefix, is_valid), None))
        except (MissingCaCertException, ProxyException):
            self.queue.put((callback, None, sys.exc_info()))

    def get_owner_list(self, username, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(target=self._get_owner_list,
                                            name="GetOwnerListThread",
                                            args=(username, callback)))

    def get_environment_list(self, owner_key, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(target=self._get_environment_list,
                                            name="GetEnvironmentListThread",
                                            args=(owner_key, callback)))

    def register_consumer(self, name, owner, env, activation_keys, callback):
        """
        Run consumer registration asyncronously
        """
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(
            target=self._register_consumer,
            name="RegisterConsumerThread",
            args=(name, owner, env, activation_keys, callback)))

    def update_package_profile(self, uuid, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(
            target=self._update_package_profile,
            name="UpdatePackageProfileThread",
            args=(uuid, callback)))

    def subscribe(self, uuid, current_sla, dry_run_result, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(
            target=self._subscribe,
            name="SubscribeThread",
            args=(uuid, current_sla, dry_run_result, callback)))

    def find_subscriptions(self, consumer_uuid, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(
            target=self._find_subscriptions,
            name="FindSubscriptionsThread",
            args=(consumer_uuid, callback)))

    def refresh(self, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(target=self._refresh,
                                            name="RefreshThread",
                                            args=(callback,)))

    def unregister_consumer(self, consumer_uuid, server_info, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(target=self._unregister_consumer,
                                            name="UnregisterThread",
                                            args=(consumer_uuid,
                                                  server_info,
                                                  callback)))

    def validate_server(self, hostname, port, prefix, callback):
        ga_GObject.idle_add(self._watch_thread)
        self._start_thread(threading.Thread(target=self._validate_server,
                                            name="ValidateServerThread",
                                            args=(hostname, port, prefix, callback)))


# TODO: make this a more informative 'summary' page.
class DoneScreen(Screen):
    gui_file = "done_box"

    def __init__(self, reg_info, async_backend, parent_window):
        super(DoneScreen, self).__init__(reg_info, async_backend, parent_window)
        self.pre_message = "We are done."

    def pre(self):
        # TODO: We could start cleanup tasks here.
        self.pre_done()
        return False


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

    def __init__(self, reg_info, async_backend, parent_window):
        super(InfoScreen, self).__init__(reg_info, async_backend, parent_window)
        self.button_label = _("_Next")
        callbacks = {"on_why_register_button_clicked":
                     self._on_why_register_button_clicked,
                     "on_back_to_reg_button_clicked":
                     self._on_back_to_reg_button_clicked
                     }

        self.connect_signals(callbacks)

    def pre(self):
        self.pre_done()
        return False

    def apply(self):
        self.stay()
        if self.register_radio.get_active():
            self.emit('move-to-screen', CHOOSE_SERVER_PAGE)
            return True

        else:
            self.emit('move-to-screen', FINISH)
            return True

    def _on_why_register_button_clicked(self, button):
        self.why_register_dialog.show()

    def _on_back_to_reg_button_clicked(self, button):
        self.why_register_dialog.hide()
