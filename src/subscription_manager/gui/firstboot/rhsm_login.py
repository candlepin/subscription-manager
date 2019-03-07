from __future__ import print_function, division, absolute_import

import sys
import logging
import dbus.mainloop.glib

from subscription_manager import ga_loader
ga_loader.init_ga()

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.ga import gtk_compat, GLib

gtk_compat.threads_init()

import rhsm

# enable logging for firstboot
from subscription_manager import logutil
logutil.init_logger()

log = logging.getLogger(__name__)

# neuter linkify in firstboot
from subscription_manager.gui.utils import running_as_firstboot
running_as_firstboot()

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()

from subscription_manager import injection as inj

from rhsmlib.facts.hwprobe import HardwareCollector
from subscription_manager.gui import managergui
from subscription_manager.gui import registergui
from subscription_manager.gui.utils import format_exception

from firstboot import module
from firstboot import constants

from subscription_manager.i18n import configure_i18n, ugettext as _
configure_i18n()

from rhsm.utils import remove_scheme

sys.path.append("/usr/share/rhn")
rhn_config = None

try:
    from up2date_client import config as rhn_config
except ImportError:
    log.debug("no rhn-client-tools modules could be imported")


class moduleClass(module.Module, object):

    def __init__(self):
        """
        Create a new firstboot Module for the 'register' screen.
        """
        super(moduleClass, self).__init__()

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        GLib.threads_init()
        dbus.mainloop.glib.threads_init()

        self.mode = constants.MODE_REGULAR
        self.title = _("Subscription Management Registration")
        self.sidebarTitle = _("Subscription Registration")
        self.priority = 200.1

        # NOTE: all of this is copied form former firstboot_base module
        # and may no longer be needed
        # set this so subclasses can override behaviour if needed
        self._is_compat = False

        reg_info = registergui.RegisterInfo()
        self.backend = managergui.Backend()
        self.plugin_manager = inj.require(inj.PLUGIN_MANAGER)
        self.register_widget = registergui.FirstbootWidget(self.backend, reg_info)
        self.register_widget.connect("notify::screen-ready", self._on_screen_ready_change)

        # Will be False if we are on an older RHEL version where
        # rhn-client-tools already does some things so we don't have to.
        self.standalone = True
        distribution = HardwareCollector().get_distribution()
        log.debug("Distribution: %s" % str(distribution))

        try:
            dist_version = float(distribution[1])
            # We run this for Fedora as well, but all we really care about here
            # is if this is prior to RHEL 7, so this comparison should be safe.
            if dist_version < 7:
                self.standalone = False
        except Exception as e:
            log.error("Unable to parse a distribution version.")
            log.exception(e)
        log.debug("Running standalone firstboot: %s" % self.standalone)

        self.manual_message = None

        self._skip_apply_for_page_jump = False
        self._cached_credentials = None
        self._registration_finished = False

        self.interface = None
        self.finished = False

        self.proxies_were_enabled_from_gui = None
        self._apply_result = constants.RESULT_FAILURE

        self.page_status = constants.RESULT_FAILURE

    def _on_screen_ready_change(self, obj, param):
        ready = self.register_widget.current_screen.get_property('ready')
        self._set_navigation_sensitive(ready)

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """
        self.interface = interface

        self.register_widget.emit('proceed')

        # This is always "fail" until we get to the done screen
        return self.page_status

    def createScreen(self):
        """
        Create a new instance of gtk.VBox, pulling in child widgets from the
        glade file.
        """
        self.vbox = ga_Gtk.VBox()
        # self.vbox.pack_start(self.get_widget("register_widget"), False, False, 0)
        self.vbox.pack_start(self.register_widget.register_widget, False, False, 0)

        self.register_widget.connect('finished', self.on_finished)
        self.register_widget.connect('register-error', self.on_register_error)
        self.register_widget.connect('register-message', self.on_register_message)

        # In firstboot, we leverage the RHN setup proxy settings already
        # presented to the user, so hide the choose server screen's proxy
        # text and button. But, if we are standalone, show our versions.
        if not self.standalone:
            screen = self.register_widget._screens[registergui.CHOOSE_SERVER_PAGE]
            screen.proxy_frame.destroy()

    def focus(self):
        """
        Focus the initial UI element on the page, in this case the
        login name field.
        """
        # FIXME:  This is currently broken
        # login_text = self.glade.get_widget("account_login")
        # login_text.grab_focus()

    def initializeUI(self):
        log.debug("initializeUi %s", self)
        # Need to make sure that each time the UI is initialized we reset back
        # to the main register screen.

        if self.finished:
            self.register_widget.done()
            return

        # Note, even if we are standalone firstboot mode (no rhn modules),
        # we may still have RHN installed, and possibly configured.
        self._read_rhn_proxy_settings()

        self.register_widget.initialize()
        # Make sure to show the unregister screen
        self.register_widget.info.set_property('enable-unregister', True)

    def needsNetwork(self):
        """
        This lets firstboot know that networking is required, in order to
        talk to hosted UEP.
        """
        return True

    def needsReboot(self):
        return False

    # TODO: verify this doesnt break anything
    def not_renderModule(self, interface):
        #ParentClass.renderModule(self, interface)

        # firstboot module class docs state to not override renderModule,
        # so this is breaking the law.
        #
        # This is to set line wrapping on the title label to resize
        # correctly with our long titles and their even longer translations
        super(moduleClass, self).renderModule(interface)

        # FIXME: likely all of this should be behind a try/except, since it's
        #        likely to break, and it is just to fix cosmetic issues.
        # Walk down widget tree to find the title label
        label_container = self.vbox.get_children()[0]
        title_label = label_container.get_children()[0]

        # Set the title to wrap and connect to size-allocate to
        # properly resize the label so that it takes up the most
        # space it can.
        title_label.set_line_wrap(True)
        title_label.connect('size-allocate',
                             lambda label, size: label.set_size_request(size.width - 1, -1))

    def shouldAppear(self):
        """
        Indicates to firstboot whether to show this screen.  In this case
        we want to skip over this screen if there is already an identity
        certificate on the machine (most likely laid down in a kickstart).
        """
        identity = inj.require(inj.IDENTITY)
        return not identity.is_valid()

    def on_register_message(self, obj, msg, message_type=None):
        message_type = message_type or ga_Gtk.MessageType.ERROR
        self.error_dialog(msg, message_type=message_type)

    def on_register_error(self, obj, msg, exc_list):
        self.page_status = constants.RESULT_FAILURE

        # TODO: we can add the register state, error type (error or exc)
        if exc_list:
            self.handle_register_exception(obj, msg, exc_list)
        else:
            self.handle_register_error(obj, msg)
            return True

    def on_finished(self, obj):
        self.finished = True
        self.page_status = constants.RESULT_SUCCESS
        return False

    def handle_register_error(self, obj, msg):
        self.error_dialog(msg)

    def handle_register_exception(self, obj, msg, exc_info):
        # We are checking to see if exc_info seems to have come from
        # a call to sys.exc_info()
        # (likely somewhere in registergui.AsyncBackend)
        # See bz 1395662 for more info
        if isinstance(exc_info, tuple) and \
           isinstance(exc_info[1], registergui.RemoteUnregisterException):
            # Don't show a message box when we cannot unregister from the server
            # Instead log the exception
            log.exception(exc_info[1])
            return
        message = format_exception(exc_info, msg)
        self.error_dialog(message)

    def error_dialog(self, text, message_type=None):
        message_type = message_type or ga_Gtk.MessageType.ERROR
        dlg = ga_Gtk.MessageDialog(None, 0, message_type,
                                   ga_Gtk.ButtonsType.OK, text)
        dlg.set_markup(text)
        dlg.set_skip_taskbar_hint(True)
        dlg.set_skip_pager_hint(True)
        dlg.set_position(ga_Gtk.WindowPosition.CENTER)

        def response_handler(obj, response_id):
            obj.destroy()

        dlg.connect('response', response_handler)
        dlg.set_modal(True)
        dlg.show()

    def _get_initial_screen(self):
        """
        Override parent method as in some cases, we use a different
        starting screen.
        """
        if self.standalone:
            return registergui.INFO_PAGE
        else:
            return registergui.CHOOSE_SERVER_PAGE

    @property
    def error_screen(self):
        return self._get_initial_screen()

    def _read_rhn_proxy_settings(self):
        if not rhn_config:
            return

        # Read and store rhn-setup's proxy settings, as they have been set
        # on the prior screen (which is owned by rhn-setup)
        up2date_cfg = rhn_config.initUp2dateConfig()
        cfg = rhsm.config.initConfig()

        # Track if we have changed this in the gui proxy dialog, if
        # we have changed it to disabled, then we apply "null", otherwise
        # if the version off the fs was disabled, we ignore the up2date proxy settings.
        #
        # Don't do anything if proxies aren't enabled in rhn config.
        if not up2date_cfg['enableProxy']:
            if self.proxies_were_enabled_from_gui:
                cfg.set('server', 'proxy_hostname', '')
                cfg.set('server', 'proxy_port', '')
                self.backend.cp_provider.set_connection_info()

            return

        # If we get here, we think we are enabling or updating proxy info
        # based on changes from the gui proxy settings dialog, so take that
        # to mean that enabledProxy=0 means to unset proxy info, not just to
        # not override it.
        self.proxies_were_enabled_from_gui = up2date_cfg['enableProxy']

        proxy = up2date_cfg['httpProxy']
        if proxy:
            # Remove any URI scheme provided
            proxy = remove_scheme(proxy)
            try:
                host, port = proxy.split(':')
                # the rhn proxy value is unicode, assume we can
                # cast to ascii ints
                port = str(int(port))
                cfg.set('server', 'proxy_hostname', host)
                cfg.set('server', 'proxy_port', port)
            except ValueError:
                cfg.set('server', 'proxy_hostname', proxy)
                cfg.set('server', 'proxy_port',
                        rhsm.config.DEFAULT_PROXY_PORT)

        if up2date_cfg['enableProxyAuth']:
            cfg.set('server', 'proxy_user', up2date_cfg['proxyUser'])
            cfg.set('server', 'proxy_password',
                    up2date_cfg['proxyPassword'])

        self.backend.cp_provider.set_connection_info()

    def close_window(self):
        """
        Overridden from RegisterScreen - we want to bypass the default behavior
        of hiding the GTK window.
        """
        pass

    def emit_consumer_signal(self):
        """
        Overriden from RegisterScreen - we don't care about consumer update
        signals.
        """
        pass

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = self.get_object(widget_name)
        widget.destroy()

    def _set_navigation_sensitive(self, sensitive):
        # we are setting the firstboot next/back buttons
        # insensitive here, instead of the register/cancel
        # buttons this calls if shown in standalone gui.
        # But, to get to those, we need a reference to the
        # firstboot interface instance.
        # In rhel6.4, we don't get a handle on interface, until we
        # module.apply(). We call _set_navigation_sensitive from
        # module.show() (to set these back if they have changed in
        # the standalone gui flow), which is before apply(). So
        # do nothing here if we haven't set a ref to self.interface
        # yet. See bz#863572
        # EL5:
        if self._is_compat:
            self.compat_parent.backButton.set_sensitive(sensitive)
            self.compat_parent.nextButton.set_sensitive(sensitive)
        # EL6:
        else:
            if self.interface is not None:
                self.interface.backButton.set_sensitive(sensitive)
                self.interface.nextButton.set_sensitive(sensitive)

    def _get_credentials_hash(self):
        """
        Return an internal hash representation of the text input
        widgets.  This is used to compare if we have changed anything
        when moving back and forth across modules.
        """
        return {"username": self.username,
                "password": self.password,
                "consumername": self.consumername,
        }

    def _get_text(self, widget_name):
        """
        Return the text value of an input widget referenced
        by name.
        """
        widget = self.get_object(widget_name)
        return widget.get_text()

    def _set_register_label(self, screen):
        """
        Overridden from registergui to disable changing the firstboot button
        labels.
        """
        pass

    def finish_registration(self, failed=False):
        log.debug("Finishing registration, failed=%s" % failed)
        if failed:
            self._set_navigation_sensitive(True)
            self._set_initial_screen()
        else:
            self._registration_finished = True
            self._skip_remaining_screens(self.interface)
            registergui.RegisterScreen.finish_registration(self, failed=failed)

    def _skip_remaining_screens(self, interface):
        """
        Find the first non-rhsm module after the rhsm modules, and move to it.

        Assumes that there is only _one_ rhsm screen
        """
        if self._is_compat:
            # el5 is easy, we can just pretend the next button was clicked,
            # and tell our own logic not to run for the button press.
            self._skip_apply_for_page_jump = True
            self.compat_parent.nextClicked()
        else:
            self._apply_result = self._RESULT_SUCCESS
            return
