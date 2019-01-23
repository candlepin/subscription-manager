from __future__ import print_function, division, absolute_import

#
# Copyright (C) 2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

import logging

from pyanaconda.ui.communication import hubQ
from pyanaconda.ui.gui.spokes import NormalSpoke
from pyanaconda.ui.categories.system import SystemCategory
from pyanaconda.ui.categories.user_settings import UserSettingsCategory
from pyanaconda.ui.gui.utils import really_hide
from pyanaconda.flags import flags
try:
    from pyanaconda.constants import ANACONDA_ENVIRON
except ImportError:
    from pyanaconda.core.constants import ANACONDA_ENVIRON

from subscription_manager import logutil

logutil.init_logger()
log = logging.getLogger(__name__)

from subscription_manager import ga_loader

# initial-setup only works with gtk version 3
ga_loader.init_ga(gtk_version="3")

from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.gui import managergui
from subscription_manager.i18n import configure_gettext
from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.gui import registergui
from subscription_manager import utils
from subscription_manager.gui import utils as gui_utils

ga_GObject.threads_init()

__all__ = ["RHSMSpoke"]

configure_gettext()


class RHSMSpoke(NormalSpoke):
    """
    Spoke used for registration of system in Anaconda or Initial Setup
    """
    buildrObjects = ["RHSMSpokeWindow"]
    mainWidgetName = "RHSMSpokeWindow"
    uiFile = "rhsm_gui.ui"
    helpFile = "SubscriptionManagerSpoke.xml"
    # Display our spoke in second hub for testing purpose. There is also
    # no more space in first hub. See this bug report:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1584160
    if ANACONDA_ENVIRON in flags.environs:
        category = UserSettingsCategory
    else:
        category = SystemCategory
    icon = "subscription-manager"
    title = "_Subscription Manager"

    @classmethod
    def should_run(cls, environment, data):
        """Run this spoke for Anaconda and InitialSetup"""
        return True

    def __init__(self, data, storage, payload, instclass):
        NormalSpoke.__init__(self, data, storage, payload, instclass)
        self._done = False
        self._addon_data = self.data.addons.com_redhat_subscription_manager

    def initialize(self):
        NormalSpoke.initialize(self)
        self._done = False

        init_dep_injection()

        backend = managergui.Backend()
        self.info = registergui.RegisterInfo()
        self.info.connect('notify::register-status', self._on_register_status_change)
        self._status = self.info.get_property('register-status')

        self.register_widget = registergui.RegisterWidget(
            backend,
            reg_info=self.info,
            parent_window=self.main_window
        )

        self.register_box = self.builder.get_object("register_box")
        self.button_box = self.builder.get_object('navigation_button_box')
        self.proceed_button = self.builder.get_object('proceed_button')
        self.back_button = self.builder.get_object('back_button')

        self.register_box.pack_start(self.register_widget.register_widget,
                                     True, True, 0)

        # Hook up the nav buttons in the gui
        # TODO: add a 'start over'?
        self.proceed_button.connect('clicked', self._on_register_button_clicked)
        self.back_button.connect('clicked', self._on_back_button_clicked)

        # initial-setup will likely
        self.register_widget.connect('finished', self._on_finished)
        self.register_widget.connect('register-finished', self._on_register_finished)
        self.register_widget.connect('register-error', self._on_register_error)
        self.register_widget.connect('register-message', self._on_register_message)

        # update the 'next/register button on page change'
        self.register_widget.connect('notify::register-button-label',
                                       self._on_register_button_label_change)

        self.register_widget.connect('notify::screen-ready',
                                     self._on_register_screen_ready_change)

        self.register_box.show_all()
        self.register_widget.initialize()
        self.back_button.set_sensitive(False)

    @property
    def ready(self):
        """A boolean property indicating the spoke is ready to be visited.
        This could depend on other modules or waiting for internal
        state to be setup."""

        return True

    @property
    def completed(self):
        """A boolean property indicating if all the mandatory actions are completed."""
        # TODO: tie into register_widget.info.register-state

        return self._done

    @property
    def mandatory(self):
        """A boolean property indicating if the module has to be completed before initial-setup is done."""

        return False

    @property
    def status(self):
        """A string property indicating a user facing summary of the spokes status.
        This is displayed under the spokes name on it's hub."""

        # The status property is only used read/only, so no setter required.
        return self._status

    def refresh(self):
        """Update gui widgets to reflect state of self.data.

        This is called whenever a user returns to a Spoke to update the
        info displayed, since the data could have been changed or updated
        by another spoke or by actions that completed in the mean time.

        Here it is used to populate RHSMSpokes registerGui.RegisterInfo self.info,
        since changes there are applied to RegisterWidget self.register_widget
        by RegisterWidget itself.

        The RHSM 'ks' spoke can read values from the kickstart files read by
        initial-setup, and stored in self._addon_data. So this method will
        seed RHSMSpokes gui with any values set there.
        """

        if self._addon_data.serverurl:
            (hostname, port, prefix) = utils.parse_server_info(self._addon_data.serverurl)
            self.info.set_property('hostname', hostname)
            self.info.set_property('port', port)
            self.info.set_property('prefix', prefix)

        if self._addon_data.username:
            self.info.set_property('username',
                                   self._addon_data.username)

        if self._addon_data.password:
            self.info.set_property('password',
                                   self._addon_data.password)

        if self._addon_data.org:
            self.info.set_property('owner_key',
                                   self._addon_data.org)

        if self._addon_data.activationkeys:
            self.info.set_property('activation_keys',
                                   self._addon_data.activationkeys)

        # TODO: support a ordered list of sla preferences?
        if self._addon_data.servicelevel:
            # NOTE: using the first sla in servicelevel only currently
            self.info.set_property('preferred_sla',
                                   self._addon_data.servicelevel[0])

        if self._addon_data.force:
            self.info.set_property('force', True)

        self.register_widget.populate_screens()

    # take info from the gui widgets and set into the self.data
    def apply(self):
        """Take info from the gui widgets and set into the self.data.addons AddonData.

        self.data.addons will be used to persist the values into a
        initial-setup-ks.cfg file when initial-setup completes."""

        # TODO: implement
        pass

    def execute(self):
        """When the spoke is left, this can run anything that needs to happen.

        Wait for any async processing to complete."""
        self.register_widget.async_backend.block_until_complete()

    def _on_register_status_change(self, obj, params):
        status = obj.get_property('register-status')
        self._status = status
        hubQ.send_message(self.__class__.__name__, self._status)

    def _on_back_button_clicked(self, button):
        """Handler for self.back_buttons 'clicked' signal.

        Clear out any user set values and return to the start screen."""
        self.clear_info()
        self.register_widget.emit('back')
        self.back_button.set_sensitive(not self.register_widget.applied_screen_history.is_empty())

        # TODO: clear out settings and restart?
        # TODO: attempt to undo the REST api calls we've made?
        #self.register_widget.set_initial_screen()
        #self.register_widget.clear_screens()

    def _on_register_button_clicked(self, button):
        """Handler for self.proceed_buttons 'clicked' signal.

        The proceed and reset buttons in the RHSM spokes window
        are used to drive the registergui.RegisterWidget by
        emitting a 'proceed' signal to RegisterWidget when the
        'proceed' button in the spoke window is clicked."""
        self.clear_info()

        self.register_widget.emit('proceed')

    def _on_finished(self, obj):
        """Handler for RegisterWidget's 'finished' signal."""
        self._done = True
        really_hide(self.button_box)

    # If we completed registration, that's close enough to consider
    # completed.
    def _on_register_finished(self, obj):
        """Handler for RegisterWidget's 'register-finished' signal.

        Indicates the system successfully registered.
        Note: It does mean the system has finished attaching
        subscriptions, or that RegisterWidget is finished.

        It only indicates the registration portion is finished."""
        self._done = True

    # May merge error and message handling, but error can
    # include tracebacks and alter program flow...
    def _on_register_error(self, widget, msg, exc_info):
        """Handler for RegisterWidget's 'register-error' signal.

        Depending on the data passed to 'register-error' emission, this
        widgets decides how to format the error 'msg'. The 'msg' may
        need to use format_exception to including exception info
        in the msg (ie, the exception msg or status code).

        This uses initial-setups set_error() to display the error
        messages. Currently that is via a Gtk.InfoBar."""

        if exc_info:
            formatted_msg = gui_utils.format_exception(exc_info, msg)
            self.set_error(formatted_msg)
        else:
            log.error(msg)
            self.set_error(msg)

    def _on_register_message(self, widget, msg, msg_type=None):
        """Handler for RegisterWidget's 'register-message' signal.

        If RegisterWidget needs the parent widget to show an info
        or warning message, it emits 'register-message' with the
        msg string and msg_type (a Gtk.MessageType).

        This uses initial-setups set_info() or set_warning() to
        display the message. Currently that is via a Gtk.InfoBar."""

        # default to info.
        msg_type = msg_type or ga_Gtk.MessageType.INFO

        if msg_type == ga_Gtk.MessageType.INFO:
            self.set_info(msg)
        elif msg_type == ga_Gtk.MessageType.WARNING:
            self.set_warning(msg)

    def _on_register_screen_ready_change(self, obj, value):
        ready = self.register_widget.current_screen.get_property('ready')
        self.proceed_button.set_sensitive(ready)
        self.back_button.set_sensitive(ready and not self.register_widget.applied_screen_history.is_empty())

    def _on_register_button_label_change(self, obj, value):
        """Handler for registergui.RegisterWidgets's 'register-button-label' property notifications.

        Used to update the label on the proceed/register/next button in RHSMSpoke
        to reflect RegisterWidget's state. (ie, 'Register', then 'Attach', etc)."""

        register_label = obj.get_property('register-button-label')

        if register_label:
            self.proceed_button.set_label(register_label)
