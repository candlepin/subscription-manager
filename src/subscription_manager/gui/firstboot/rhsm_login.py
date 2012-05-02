import sys
import gtk
import socket

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

import rhsm

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import managergui
from subscription_manager import managerlib
from subscription_manager.gui import registergui
from subscription_manager.gui import autobind
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.facts import Facts
from subscription_manager.gui.manually_subscribe import get_screen
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule

from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.utils import remove_scheme

sys.path.append("/usr/share/rhn")
from up2date_client import config


class moduleClass(RhsmFirstbootModule, registergui.RegisterScreen):

    def __init__(self):
        """
        Create a new firstboot Module for the 'register' screen.
        """
        RhsmFirstbootModule.__init__(self,
                _("Entitlement Platform Registration"),
                _("Entitlement Registration"),
                200.1, 109.10)

        self.pages = {
                "rhsm_manually_subscribe": _("Manual Configuraton Required"),
                "rhsm_select_sla": _("Service Level"),
                "rhsm_confirm_subs": _("Confirm Subscriptions"),
                }

        backend = managergui.Backend()

        registergui.RegisterScreen.__init__(self, backend,
                managergui.Consumer(), Facts())

        self._skip_apply_for_page_jump = False
        self._cached_credentials = None
        self._registration_finished = False

    def _read_rhn_proxy_settings(self):
        # Read and store rhn-setup's proxy settings, as they have been set
        # on the prior screen (which is owned by rhn-setup)
        up2date_cfg = config.initUp2dateConfig()
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
        self.backend.uep = rhsm.connection.UEPConnection(
            host=cfg.get('server', 'hostname'),
            ssl_port=int(cfg.get('server', 'port')),
            handler=cfg.get('server', 'prefix'),
            proxy_hostname=cfg.get('server', 'proxy_hostname'),
            proxy_port=cfg.get('server', 'proxy_port'),
            proxy_user=cfg.get('server', 'proxy_user'),
            proxy_password=cfg.get('server', 'proxy_password'),
            username=None, password=None,
            cert_file=ConsumerIdentity.certpath(),
            key_file=ConsumerIdentity.keypath())

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
            return self._RESULT_SUCCESS

        self.interface = interface

        self._read_rhn_proxy_settings()

        credentials = self._get_credentials_hash()

        # bad proxy settings can cause socket.error or friends here
        # see bz #810363
        try:
            valid_registration = self.register(testing=testing)
        except socket.error, e:
            handle_gui_exception(e, e, self.registerWin)
            return self._RESULT_FAILURE

        if valid_registration:
            self._cached_credentials = credentials
        return self._RESULT_FAILURE

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

    def registrationTokenScreen(self):
        """
        Overridden from RegisterScreen - ignore any requests to show the
        registration screen on this particular page.
        """
        pass

    def createScreen(self):
        """
        Create a new instance of gtk.VBox, pulling in child widgets from the
        glade file.
        """
        self.vbox = gtk.VBox(spacing=10)
        self.register_dialog = registergui.registration_xml.get_widget("dialog-vbox6")
        self.register_dialog.reparent(self.vbox)

        # Get rid of the 'register' and 'cancel' buttons, as we are going to
        # use the 'forward' and 'back' buttons provided by the firsboot module
        # to drive the same functionality
        self._destroy_widget('register_button')
        self._destroy_widget('cancel_button')

    def initializeUI(self):
        # Need to make sure that each time the UI is initialized we reset back
        # to the main register screen.

        # if they've already registered during firstboot and have clicked
        # back to register again, we must first unregister.
        # XXX i'd like this call to be inside the async progress stuff,
        # since it does take some time
        if self._registration_finished and ConsumerIdentity.exists():
            try:
                managerlib.unregister(self.backend.uep, self.consumer.uuid)
            except socket.error, e:
                handle_gui_exception(e, e, self.registerWin)
            self.consumer.reload()
            self._registration_finished = False

        self._show_credentials_page()
        self._clear_registration_widgets()
        self.initializeConsumerName()

    def focus(self):
        """
        Focus the initial UI element on the page, in this case the
        login name field.
        """
        # FIXME:  This is currently broken
        login_text = registergui.registration_xml.get_widget("account_login")
        login_text.grab_focus()

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = registergui.registration_xml.get_widget(widget_name)
        widget.destroy()

    def _get_credentials_hash(self):
        """
        Return an internal hash representation of the text input
        widgets.  This is used to compare if we have changed anything
        when moving back and forth across modules.
        """
        credentials = [self._get_text(name) for name in \
                           ('account_login', 'account_password',
                               'consumer_name')]
        return hash(tuple(credentials))

    def _get_text(self, widget_name):
        """
        Return the text value of an input widget referenced
        by name.
        """
        widget = registergui.registration_xml.get_widget(widget_name)
        return widget.get_text()

    def _finish_registration(self, failed=False):
        registergui.RegisterScreen._finish_registration(self, failed=failed)
        if not failed:
            self._registration_finished = True

            self._init_sla()
        # if something did fail, we will have shown the user an error message
        # from the superclass _finish_registration. then just leave them on the
        # rhsm_login page so they can try again (or go back and select to skip
        # registration).

    def _move_to_manual_install(self, title):
        # TODO Change the message on the screen.
        get_screen().set_title(title)
        self.moveToPage("rhsm_manually_subscribe")

    def _init_sla(self):
        if self.skip_auto_subscribe():
            return self._move_to_manual_install(_("You have opted to skip auto-subscribe."))

        # sla autosubscribe time. load up the possible slas, to decide if
        # we need to display the selection screen, or go to the confirm
        # screen.
        # XXX this should really be done async.

        controller = autobind.init_controller(self.backend, self.consumer,
                Facts())

        # XXX see autobind.AutobindWizard load() and _show_initial_screen
        # for matching error handling.
        try:
            controller.load()
        except autobind.ServiceLevelNotSupportedException:
            message = _("Unable to auto-subscribe, server does not support service levels. Please run 'Subscription Manager' to manually subscribe.")
            return self._move_to_manual_install(message)

        except autobind.NoProductsException:
            message = _("No installed products on system. No need to update certificates at this time.")
            return self._move_to_manual_install(message)

        except autobind.AllProductsCoveredException:
            message = _("All installed products are covered by valid entitlements. Please run 'Subscription Manager' to subscribe to additional products.")
            return self._move_to_manual_install(message)

        except socket.error, e:
            handle_gui_exception(e, None, self.registerWin)
            return

        if len(controller.suitable_slas) > 1:
            self.moveToPage("rhsm_select_sla")
        elif len(controller.suitable_slas) == 1:
            if controller.current_sla and \
                    not controller.can_add_more_subs():
                message = _("Unable to subscribe to any additional products at current service level: %s") % controller.current_sla
                return self._move_to_manual_install(message)

            self.moveToPage("rhsm_confirm_subs")
        else:
            message = _("No service levels will cover all installed products. " + \
                "Please run 'Subscription Manager' to manually " + \
                "entitle this system.")
            return self._move_to_manual_install(message)

    def moveToPage(self, page):
        """
        el5 compat method for jumping pages
        """
        if self._is_compat:
            # we must be on el5.
            self._skip_apply_for_page_jump = True
            self.parent.setPage(page)
            self.parent.nextClicked()
        else:
            self.interface.moveToPage(moduleTitle=self.pages[page])

# for el5
childWindow = moduleClass
