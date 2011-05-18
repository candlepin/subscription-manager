#
# GUI Module for standalone subscription-manager cli
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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

import os
import socket
import logging
import locale

import gtk
import gtk.glade

from subscription_manager.gui import messageWindow
from subscription_manager.gui import networkConfig
from subscription_manager import managerlib
from subscription_manager.gui import file_monitor
from subscription_manager.gui import registergui
import rhsm.connection as connection
import rhsm.config as config
from subscription_manager import constants
from subscription_manager.facts import Facts
from subscription_manager.certlib import ProductDirectory, EntitlementDirectory, ConsumerIdentity, \
        CertLib, CertSorter, find_first_invalid_date
from subscription_manager.branding import get_branding

from subscription_manager.gui import activate
from subscription_manager.gui import factsgui
from subscription_manager.gui import widgets
from subscription_manager.gui.installedtab import InstalledProductsTab
from subscription_manager.gui.mysubstab import MySubscriptionsTab
from subscription_manager.gui.allsubs import AllSubscriptionsTab
from subscription_manager.gui.subscription_assistant import \
        SubscriptionAssistant
from subscription_manager.gui.importsub import ImportSubDialog
from subscription_manager.gui.utils import handle_gui_exception, errorWindow, linkify

import gettext
_ = gettext.gettext
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)

prefix = os.path.dirname(__file__)
VALID_IMG = os.path.join(prefix, "data/icons/valid.svg")
INVALID_IMG = os.path.join(prefix, "data/icons/invalid.svg")

#workaround for or_IN issue in python
if (locale.getlocale(locale.LC_TIME)[0] == 'or_IN'):
    locale.setlocale(locale.LC_TIME, 'en_GB')

cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()

cfg = config.initConfig()


class Backend(object):
    """
    Wrapper for sharing UEP connections to Candlepin.

    Reference to a Backend object will be passed around UI components, so
    the UEP connection it contains can be modified/recreated and all
    components will have the updated connection.

    This also serves as a common wrapper for certifcate directories and methods
    to monitor those directories for changes.
    """

    def __init__(self):
        self.create_uep(cert_file=ConsumerIdentity.certpath(),
                        key_file=ConsumerIdentity.keypath())

        # we don't know the user/pass yet, so no point in
        # creating an admin uep till we need it
        self.admin_uep = None

        self.product_dir = ProductDirectory()
        self.entitlement_dir = EntitlementDirectory()
        self.certlib = CertLib(uep=self.uep)

        self.product_monitor = file_monitor.Monitor(self.product_dir.path)
        self.entitlement_monitor = file_monitor.Monitor(
                self.entitlement_dir.path)
        self.identity_monitor = file_monitor.Monitor(ConsumerIdentity.PATH)

    # make a create that does the init
    # and a update() for a name

    def update(self):
        self.create_uep(cert_file=ConsumerIdentity.certpath(),
                        key_file=ConsumerIdentity.keypath())

    def create_uep(self, cert_file=None, key_file=None):
        # Re-initialize our connection:
        self.uep = self._create_uep(cert_file=cert_file,
                                    key_file=key_file)
        # Holds a reference to the old uep:
        self.certlib = CertLib(uep=self.uep)

    def _create_uep(self, username=None, password=None, cert_file=None, key_file=None):
        return connection.UEPConnection(
            host=cfg.get('server', 'hostname'),
            ssl_port=int(cfg.get('server', 'port')),
            handler=cfg.get('server', 'prefix'),
            proxy_hostname=cfg.get('server', 'proxy_hostname'),
            proxy_port=cfg.get('server', 'proxy_port'),
            proxy_user=cfg.get('server', 'proxy_user'),
            proxy_password=cfg.get('server', 'proxy_password'),
            username=username,
            password=password,
            cert_file=cert_file,
            key_file=key_file)

    def is_registered(self):
        if ConsumerIdentity.existsAndValid():
            return True
        return False

    def create_admin_uep(self, username=None, password=None):
        self.admin_uep = self._create_uep(username=username, password=password)

    def monitor_certs(self, callback):
        self.product_monitor.connect('changed', callback)
        self.entitlement_monitor.connect('changed', callback)

    def monitor_identity(self, callback):
        self.identity_monitor.connect('changed', callback)


class Consumer(object):
    """
    Wrapper for sharing consumer identity information throughout GUI
    components.
    """
    def __init__(self):
        self.reload()

    def reload(self):
        """
        Check for consumer certificate on disk and update our info accordingly.
        """
        log.debug("Loading consumer info from identity certificates.")
        if not ConsumerIdentity.existsAndValid():
            self.name = None
            self.uuid = None
        else:
            consumer = ConsumerIdentity.read()
            self.name = consumer.getConsumerName()
            self.uuid = consumer.getConsumerId()


class MainWindow(widgets.GladeWidget):
    """
    The new RHSM main window.
    """
    def __init__(self):
        super(MainWindow, self).__init__('mainwindow.glade',
              ['main_window', 'notebook', 'subscription_status_label',
               'subscription_status_image', 'system_name_label',
               'next_update_label', 'next_update_title', 'register_button',
               'unregister_button', 'update_certificates_button', 'activate_button'])

        self.backend = Backend()
        self.consumer = Consumer()
        self.facts = Facts()

        self.system_facts_dialog = factsgui.SystemFactsDialog(self.backend, self.consumer,
                self.facts)

        self.registration_dialog = registergui.RegisterScreen(self.backend,
                self.consumer, self.facts,
                callbacks=[self.registration_changed])

        self.import_sub_dialog = ImportSubDialog()

        self.subscription_assistant = SubscriptionAssistant(self.backend,
                self.consumer, self.facts)

        self.network_config_dialog = networkConfig.NetworkConfigDialog()
        self.network_config_dialog.xml.get_widget("closeButton").connect("clicked", self._config_changed)

        self.activate_dialog = activate.ActivationDialog(self.backend, self.consumer)

        self.installed_tab = InstalledProductsTab(self.backend, self.consumer,
                self.facts)
        self.my_subs_tab = MySubscriptionsTab(self.backend, self.consumer,
                self.facts)
        self.all_subs_tab = AllSubscriptionsTab(self.backend, self.consumer,
                self.facts)

        for tab in [self.installed_tab, self.my_subs_tab]:
            self.notebook.append_page(tab.get_content(), gtk.Label(tab.get_label()))

        self.glade.signal_autoconnect({
            "on_update_certificates_button_clicked": self._update_certificates_button_clicked,
            "on_register_button_clicked": self._register_button_clicked,
            "on_unregister_button_clicked": self._unregister_button_clicked,
            "on_add_sub_button_clicked": self._add_sub_button_clicked,
            "on_view_facts_button_clicked": self._facts_button_clicked,
            "on_proxy_config_button_clicked":
                self._network_config_button_clicked,
            "on_activate_button_clicked": self._activate_button_clicked,
        })

        # Register callback for when product/entitlement certs are updated
        def on_cert_change(filemonitor):
            self._set_validity_status()

        def on_identity_change(filemonitor):
            self.refresh()

        self.backend.monitor_certs(on_cert_change)
        self.backend.monitor_identity(on_identity_change)

        self.main_window.show_all()
        self.refresh()

        # Check to see if already registered to old RHN/Spacewalk
        # and show dialog if so
        self._check_rhn_classic()

    def registered(self):
        return ConsumerIdentity.existsAndValid()

    def registration_changed(self):
        log.debug("Registration changed, updating main window.")

        self.refresh()

    def refresh(self):
        """ Refresh the UI. """
        self.consumer.reload()
        self._set_validity_status()

        # Show the All Subscriptions tab if registered, hide it otherwise:
        if self.registered() and self.notebook.get_n_pages() == 2:
            self.notebook.append_page(self.all_subs_tab.get_content(),
                    gtk.Label(self.all_subs_tab.get_label()))
        elif not self.registered() and self.notebook.get_n_pages() == 3:
            self.notebook.set_current_page(0)
            self.notebook.remove_page(2)

        self.all_subs_tab.refresh()
        self.installed_tab.refresh()
        self.my_subs_tab.refresh()

        self._show_buttons()
        self._show_activation_buttons()

    def _get_window(self):
        """
        Return the window containing this widget (might be different for
        firstboot).
        """
        return self.main_window

    def _show_buttons(self):
        """
        Renders the Tools buttons dynamically.
        """
        if self.registered():
            self.register_button.hide()
            self.unregister_button.show()
        else:
            self.register_button.show()
            self.unregister_button.hide()

    def _show_activation_buttons(self):
        # Check if consumer can activate a subscription - if an identity cert exists
        can_activate = False

        if self.consumer.uuid:
            try:
                consumer = self.backend.uep.getConsumer(self.consumer.uuid, None, None)
                can_activate = consumer['canActivate']
            except:
                can_activate = False

        if can_activate:
            self.activate_button.show()
        else:
            self.activate_button.hide()

    def _register_button_clicked(self, widget):
        self.registration_dialog.set_parent_window(self._get_window())
        self.registration_dialog.show()

    def _on_unregister_prompt_response(self, dialog, response):
        if not response:
            log.info("unregistrater not confirmed. cancelling")
            return
        log.info("Proceeding with un-registration: %s", self.consumer.uuid)
        try:
            managerlib.unregister(self.backend.uep, self.consumer.uuid, True)
        except Exception, e:
            log.error("Error unregistering system with entitlement platform.")
            handle_gui_exception(e, constants.UNREGISTER_ERROR,
                    logMsg="Consumer may need to be manually cleaned up: %s" %
                    self.consumer.uuid)
        self.consumer.reload()
        # we've unregistered, clear pools from all subscriptionst tab
        # so it's correct if we reshow it
        self.all_subs_tab.clear_pools()
        self.refresh()

    def _unregister_button_clicked(self, widget):
        log.info("Unregister button pressed, asking for confirmation.")
        prompt = messageWindow.YesNoDialog(constants.CONFIRM_UNREGISTER,
                self._get_window())
        prompt.connect('response', self._on_unregister_prompt_response)

    def _network_config_button_clicked(self, widget):
        self.network_config_dialog.set_parent_window(self._get_window())
        self.network_config_dialog.show()

    def _facts_button_clicked(self, widget):
        self.system_facts_dialog.set_parent_window(self._get_window())
        self.system_facts_dialog.show()

    def _add_sub_button_clicked(self, widget):
        self.import_sub_dialog.set_parent_window(self._get_window())
        self.import_sub_dialog.show()

    def _update_certificates_button_clicked(self, widget):
        if self.registered():
            self.subscription_assistant.set_parent_window(self._get_window())
            self.subscription_assistant.show()
        else:
            messageWindow.OkDialog(messageWindow.wrap_text(
                _("You must register before using the subscription assistant.")),
                self._get_window())

    def _activate_button_clicked(self, widget):
        self.activate_dialog.set_parent_window(self._get_window())
        self.activate_dialog.show()

    def _config_changed(self, widget):
        # update the backend's UEP in case we changed proxy
        # config. We specify all these settings since they
        # are new and the default UEP init won't get them
        # (it's default args are set at class init time)
        self.backend.update()

    def _set_validity_status(self):
        """ Updates the entitlement validity status portion of the UI. """
        # Look for products which have invalid entitlements
        sorter = CertSorter(ProductDirectory(), EntitlementDirectory())

        warn_count = len(sorter.expired_entitlement_certs) + \
                len(sorter.unentitled_products)

        if warn_count > 0:
            buf = gtk.gdk.pixbuf_new_from_file_at_size(INVALID_IMG, 32, 32)
            self.subscription_status_image.set_from_pixbuf(buf)
            self.update_certificates_button.show()
            # Change wording slightly for just one product
            if warn_count > 1:
                self.subscription_status_label.set_markup(
                        _("You have <b>%s</b> products with invalid entitlement certificates.")
                        % warn_count)
            else:
                self.subscription_status_label.set_markup(
                        _("You have <b>1</b> product without a valid entitlement certificate."))

        else:
            first_invalid = find_first_invalid_date()
            buf = gtk.gdk.pixbuf_new_from_file_at_size(VALID_IMG, 32, 32)
            self.subscription_status_image.set_from_pixbuf(buf)
            self.subscription_status_label.set_text(
                    _("Product entitlement certificates valid through %s") % \
                        managerlib.formatDate(first_invalid))
            self.update_certificates_button.hide()

    def _check_rhn_classic(self):
        if managerlib.is_registered_with_classic():
            prompt = messageWindow.ContinueDialog(
                    linkify(get_branding().REGISTERED_TO_OTHER_WARNING),
                    self.main_window)
            prompt.connect('response', self._on_rhn_classic_response)

    def _on_rhn_classic_response(self, dialog, response):
        if not response:
            self.main_window.hide()

