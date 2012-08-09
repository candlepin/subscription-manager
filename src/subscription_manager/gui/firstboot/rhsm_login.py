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
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.facts import Facts
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule

from subscription_manager.gui.utils import handle_gui_exception
from subscription_manager.utils import remove_scheme
from subscription_manager.gui.autobind import \
        ServiceLevelNotSupportedException, NoProductsException, \
        AllProductsCoveredException

sys.path.append("/usr/share/rhn")
from up2date_client import config


MANUALLY_SUBSCRIBE_PAGE = 8


class SelectSLAScreen(registergui.SelectSLAScreen):
    """
    override the default SelectSLAScreen to jump to the manual subscribe page.
    """
    def _on_get_service_levels_cb(self, result, error=None):
        if error != None:
            if isinstance(error, ServiceLevelNotSupportedException):
                message = _("Unable to auto-subscribe, server does not support "
                            "service levels. Please run 'Subscription Manager' "
                            "to manually subscribe.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            elif isinstance(error, NoProductsException):
                message = _("No installed products on system. No need to "
                            "update certificates at this time.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            elif isinstance(error, AllProductsCoveredException):
                message = _("All installed products are covered by valid "
                            "entitlements. Please run 'Subscription Manager' "
                            "to subscribe to additional products.")
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
                message = _("Unable to subscribe to any additional products at "
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
                "entitle this system.")
            self._parent.manual_message = message
            self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)


class PerformRegisterScreen(registergui.PerformRegisterScreen):

    def _on_registration_finished_cb(self, new_account, error=None):
        try:
            if error != None:
                raise error

            managerlib.persist_consumer_cert(new_account)
            self._parent.consumer.reload()
            if self._parent.skip_auto_bind:
                message = _("You have opted to skip auto-subscribe.")
                self._parent.manual_message = message
                self._parent.pre_done(MANUALLY_SUBSCRIBE_PAGE)
            else:
                self._parent.pre_done(registergui.SELECT_SLA_PAGE)

        except Exception, e:
            handle_gui_exception(e, registergui.REGISTER_ERROR,
                    self._parent.window)
            self._parent.finish_registration(failed=True)


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

        registergui.RegisterScreen.__init__(self, backend,
                managergui.Consumer(), Facts())

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

        self.manual_message = None

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

        # bad proxy settings can cause socket.error or friends here
        # see bz #810363
        try:
            valid_registration = self.register()
        except socket.error, e:
            handle_gui_exception(e, e, self.registerWin)
            return self._RESULT_FAILURE

        if valid_registration:
            self._cached_credentials = self._get_credentials_hash()
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
        # text and button.
        screen = self._screens[registergui.CHOOSE_SERVER_PAGE]
        screen.proxy_frame.destroy()

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
        registergui.RegisterScreen.finish_registration(self, failed=failed)
        if not failed:
            self._registration_finished = True
            self._skip_remaining_screens(self.interface)
        # if something did fail, we will have shown the user an error message
        # from the superclass _finish_registration. then just leave them on the
        # rhsm_login page so they can try again (or go back and select to skip
        # registration).

    def _skip_remaining_screens(self, interface):
        """
        Find the first non-rhsm module after the rhsm modules, and move to it.

        Assumes that there is only _one_ rhsm screen
        """
        if self._is_compat:
            # el5 is easy, we can just pretend the next button was clicked,
            # and tell our own logic not to run for the button press.
            self._skip_apply_for_page_jump = True
            self.parent.nextClicked()
        else:
            # for newer firstboots, we have to iterate over all firstboot
            # modules, to find our location in the list. then we can just jump
            # to the next one after us.
            i = 0
            while not interface.moduleList[i].__module__.startswith('rhsm_'):
                i += 1

            i += 1
            interface.moveToPage(pageNum=i)

# for el5
childWindow = moduleClass
