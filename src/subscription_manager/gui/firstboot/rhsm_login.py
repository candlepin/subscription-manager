
import gettext
import socket
import sys
import logging

_ = lambda x: gettext.ldgettext("rhsm", x)

import gtk

import rhsm

sys.path.append("/usr/share/rhsm")

# enable logging for firstboot
from subscription_manager import logutil
logutil.init_logger()

log = logging.getLogger("rhsm-app." + __name__)

# neuter linkify in firstboot
from subscription_manager.gui.utils import running_as_firstboot
running_as_firstboot()

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()
from subscription_manager.injection import PLUGIN_MANAGER, IDENTITY, require

from subscription_manager.facts import Facts
from subscription_manager.hwprobe import Hardware
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule
from subscription_manager.gui import managergui
from subscription_manager.gui import registergui
from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.gui.autobind import \
        ServiceLevelNotSupportedException, NoProductsException, \
        AllProductsCoveredException
from subscription_manager import managerlib

from rhsm.connection import RestlibException
from rhsm.utils import remove_scheme

sys.path.append("/usr/share/rhn")
rhn_config = None

try:
    from up2date_client import config as rhn_config
except ImportError:
    log.debug("no rhn-client-tools modules could be imported")

MANUALLY_SUBSCRIBE_PAGE = 11


class SelectSLAScreen(registergui.SelectSLAScreen):
    """
    override the default SelectSLAScreen to jump to the manual subscribe page.
    """
    def _on_get_service_levels_cb(self, result, error=None):
        if error is not None:
            if isinstance(error[1], ServiceLevelNotSupportedException):
                message = _("Unable to auto-attach, server does not support "
                            "service levels. Please run 'Subscription Manager' "
                            "to manually attach a subscription.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            elif isinstance(error[1], NoProductsException):
                message = _("No installed products on system. No need to "
                            "update subscriptions at this time.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            elif isinstance(error[1], AllProductsCoveredException):
                message = _("All installed products are fully subscribed.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            else:
                handle_gui_exception(error, _("Error subscribing"),
                                     self._parent.window)
                self._parent.finish_registration(failed=True)
            return

        (current_sla, unentitled_products, sla_data_map) = result

        self._parent.current_sla = current_sla
        if len(sla_data_map) == 1:
            # If system already had a service level, we can hit this point
            # when we cannot fix any unentitled products:
            if current_sla is not None and \
                    not self._can_add_more_subs(current_sla, sla_data_map):
                message = _("Unable to attach any additional subscriptions at "
                            "current service level: %s") % current_sla
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
                return

            self._dry_run_result = sla_data_map.values()[0]
            self._parent.pre_done(registergui.CONFIRM_SUBS_PAGE)
        elif len(sla_data_map) > 1:
            self._sla_data_map = sla_data_map
            self.set_model(unentitled_products, sla_data_map)
            self._parent.pre_done(registergui.DONT_CHANGE)
        else:
            message = _("No service levels will cover all installed products. "
                "Please run 'Subscription Manager' to manually "
                "attach subscriptions.")
            self._parent.manual_message = message
            self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)


class PerformRegisterScreen(registergui.PerformRegisterScreen):

    def _on_registration_finished_cb(self, new_account, error=None):
        if error is not None:
            handle_gui_exception(error, registergui.REGISTER_ERROR,
                    self._parent.window)
            self._parent.finish_registration(failed=True)
            return

        try:
            managerlib.persist_consumer_cert(new_account)
            self._parent.backend.cs.force_cert_check()  # Ensure there isn't much wait time

            if self._parent.activation_keys:
                self._parent.pre_done(registergui.REFRESH_SUBSCRIPTIONS_PAGE)
            elif self._parent.skip_auto_bind:
                message = _("You have opted to skip auto-attach.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            else:
                self._parent.pre_done(registergui.SELECT_SLA_PAGE)

        # If we get errors related to consumer name on register,
        # go back to the credentials screen where we set the
        # consumer name. See bz#865954
        except RestlibException, e:
            handle_gui_exception(e, registergui.REGISTER_ERROR,
                self._parent.window)
            if e.code == 404 and self._parent.activation_keys:
                self._parent.pre_done(registergui.ACTIVATION_KEY_PAGE)
            if e.code == 400:
                self._parent.pre_done(registergui.CREDENTIALS_PAGE)

        except Exception, e:
            handle_gui_exception(e, registergui.REGISTER_ERROR,
                    self._parent.window)
            self._parent.finish_registration(failed=True)

    def pre(self):
        # TODO: this looks like it needs updating now that we run
        # firstboot without rhn client tools.

        # Because the RHN client tools check if certs exist and bypass our
        # firstboot module if so, we know that if we reach this point and
        # identity certs exist, someone must have hit the back button.
        # TODO: i'd like this call to be inside the async progress stuff,
        # since it does take some time
        identity = require(IDENTITY)
        if identity.is_valid():
            try:
                managerlib.unregister(self._parent.backend.cp_provider.get_consumer_auth_cp(),
                        self._parent.identity.uuid)
            except socket.error, e:
                handle_gui_exception(e, e, self._parent.window)
            self._parent._registration_finished = False

        return registergui.PerformRegisterScreen.pre(self)


class ManuallySubscribeScreen(registergui.Screen):
    widget_names = registergui.Screen.widget_names + ['title']

    def __init__(self, parent, backend):
        super(ManuallySubscribeScreen, self).__init__(
                "manually_subscribe.glade", parent, backend)

        self.button_label = _("Finish")

    def apply(self):
        return registergui.FINISH

    def pre(self):
        if self._parent.manual_message:
            self.title.set_label(self._parent.manual_message)
        # XXX set message here.
        return False


class moduleClass(RhsmFirstbootModule, registergui.RegisterScreen):

    def __init__(self):
        """
        Create a new firstboot Module for the 'register' screen.
        """
        RhsmFirstbootModule.__init__(self,        # Firstboot module title
        # Note: translated title needs to be unique across all
        # firstboot modules, not just the rhsm ones. See bz #828042
                _("Subscription Management Registration"),
                _("Subscription Registration"),
                200.1, 109.10)

        backend = managergui.Backend()
        self.plugin_manager = require(PLUGIN_MANAGER)
        registergui.RegisterScreen.__init__(self, backend, Facts())

        #insert our new screens
        screen = SelectSLAScreen(self, backend)
        screen.index = self._screens[registergui.SELECT_SLA_PAGE].index
        self._screens[registergui.SELECT_SLA_PAGE] = screen
        self.register_notebook.remove_page(screen.index)
        self.register_notebook.insert_page(screen.container,
                                           position=screen.index)

        screen = PerformRegisterScreen(self, backend)
        self._screens[registergui.PERFORM_REGISTER_PAGE] = screen

        screen = ManuallySubscribeScreen(self, backend)
        self._screens.append(screen)
        screen.index = self.register_notebook.append_page(screen.container)

        # Will be False if we are on an older RHEL version where
        # rhn-client-tools already does some things so we don't have to.
        self.standalone = True
        distribution = Hardware().get_distribution()
        log.debug("Distribution: %s" % str(distribution))
        try:
            dist_version = float(distribution[1])
            # We run this for Fedora as well, but all we really care about here
            # is if this is prior to RHEL 7, so this comparison should be safe.
            if dist_version < 7:
                self.standalone = False
        except Exception, e:
            log.error("Unable to parse a distribution version.")
            log.exception(e)
        log.debug("Running standalone firstboot: %s" % self.standalone)

        self.manual_message = None

        self._skip_apply_for_page_jump = False
        self._cached_credentials = None
        self._registration_finished = False

        self.interface = None

        self._apply_result = self._RESULT_FAILURE

    def _set_initial_screen(self):
        """
        Override parent method as in some cases, we use a different
        starting screen.
        """
        if self.standalone:
            self._set_screen(registergui.INFO_PAGE)
        else:
            self._set_screen(registergui.CHOOSE_SERVER_PAGE)

    def _read_rhn_proxy_settings(self):
        if not rhn_config:
            return
        # Read and store rhn-setup's proxy settings, as they have been set
        # on the prior screen (which is owned by rhn-setup)
        up2date_cfg = rhn_config.initUp2dateConfig()
        cfg = rhsm.config.initConfig()

        if up2date_cfg['enableProxy']:
            proxy = up2date_cfg['httpProxy']
            if proxy:
                # Remove any URI scheme provided
                proxy = remove_scheme(proxy)
                try:
                    host, port = proxy.split(':')
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
        else:
            cfg.set('server', 'proxy_hostname', '')
            cfg.set('server', 'proxy_port', '')
            cfg.set('server', 'proxy_user', '')
            cfg.set('server', 'proxy_password', '')

        cfg.save()
        self.backend.cp_provider.set_connection_info()

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """

        # on el5 we can't just move to another page, we have to set the next
        # page then do an apply. since we've already done our work async, skip
        # this time through
        if self._skip_apply_for_page_jump:
            self._skip_apply_for_page_jump = False
            # Reset back to first screen in our module in case the user hits back.
            # The firstboot register screen subclass will handle unregistering
            # if necessary when it runs again.
            self.show()
            return self._RESULT_SUCCESS

        self.interface = interface

        # Note, even if we are standalone firstboot mode (no rhn modules),
        # we may still have RHN installed, and possibly configured.
        self._read_rhn_proxy_settings()

        # bad proxy settings can cause socket.error or friends here
        # see bz #810363
        try:
            valid_registration = self.register()

        except socket.error, e:
            handle_gui_exception(e, e, self.window)
            return self._RESULT_FAILURE

        # run main_iteration till we have no events, like idle
        # loop sources, aka, the thread watchers are finished.
        while gtk.events_pending():
            gtk.main_iteration()

        if valid_registration:
            self._cached_credentials = self._get_credentials_hash()

        # finish_registration/skip_remaining_screens should set
        # __apply_result to RESULT_JUMP
        return self._apply_result

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

    def createScreen(self):
        """
        Create a new instance of gtk.VBox, pulling in child widgets from the
        glade file.
        """
        self.vbox = gtk.VBox(spacing=10)
        self.register_dialog = self.glade.get_widget("dialog-vbox6")
        self.register_dialog.reparent(self.vbox)

        # Get rid of the 'register' and 'cancel' buttons, as we are going to
        # use the 'forward' and 'back' buttons provided by the firsboot module
        # to drive the same functionality
        self._destroy_widget('register_button')
        self._destroy_widget('cancel_button')

        # In firstboot, we leverage the RHN setup proxy settings already
        # presented to the user, so hide the choose server screen's proxy
        # text and button. But, if we are standalone, show our versions.
        if not self.standalone:
            screen = self._screens[registergui.CHOOSE_SERVER_PAGE]
            screen.proxy_frame.destroy()

    def initializeUI(self):
        # Need to make sure that each time the UI is initialized we reset back
        # to the main register screen.
        # NOTE: On EL5 this does not appear to be called when the user
        # presses Back, only when they go through the first time.
        self.show()

    def focus(self):
        """
        Focus the initial UI element on the page, in this case the
        login name field.
        """
        # FIXME:  This is currently broken
        # login_text = self.glade.get_widget("account_login")
        # login_text.grab_focus()

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = self.glade.get_widget(widget_name)
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
        widget = self.glade.get_widget(widget_name)
        return widget.get_text()

    def _set_register_label(self, screen):
        """
        Overridden from registergui to disable changing the firstboot button
        labels.
        """
        pass

    def finish_registration(self, failed=False):
        log.info("Finishing registration, failed=%s" % failed)
        if failed:
            self._set_navigation_sensitive(True)
            self._run_pre(registergui.CREDENTIALS_PAGE)
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

# for el5
childWindow = moduleClass
