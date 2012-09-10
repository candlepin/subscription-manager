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

import locale
import logging
import subprocess
import urlparse

import gtk
import gtk.glade

from subscription_manager.gui import messageWindow
from subscription_manager.gui import networkConfig
from subscription_manager import managerlib
from subscription_manager.gui import file_monitor
from subscription_manager.gui import registergui
import rhsm.connection as connection
import rhsm.config as config
from subscription_manager import classic_check
from subscription_manager.facts import Facts
from subscription_manager.certdirectory import ProductDirectory, EntitlementDirectory
from subscription_manager.certlib import ConsumerIdentity, CertLib
from subscription_manager.branding import get_branding
from subscription_manager.utils import get_client_versions, get_server_versions, \
restart_virt_who

from subscription_manager.gui import redeem
from subscription_manager.gui import factsgui
from subscription_manager.gui import widgets
from subscription_manager.gui.installedtab import InstalledProductsTab
from subscription_manager.gui.mysubstab import MySubscriptionsTab
from subscription_manager.gui.allsubs import AllSubscriptionsTab
from subscription_manager.gui.importsub import ImportSubDialog
from subscription_manager.gui.utils import handle_gui_exception, linkify
from subscription_manager.gui.preferences import PreferencesDialog
from subscription_manager.gui.about import AboutDialog

import webbrowser
import urllib2

import gettext
_ = gettext.gettext
gettext.textdomain("rhsm")
gtk.glade.bindtextdomain("rhsm")

log = logging.getLogger('rhsm-app.' + __name__)


cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()

cfg = config.initConfig()

ONLINE_DOC_URL_TEMPLATE = "http://docs.redhat.com/docs/%s/Red_Hat_Enterprise_Linux/"


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

        self.create_content_connection()
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

        # connect handlers to refresh the cached data when we notice a change.
        # do this before any other handlers might connect
        self.product_monitor.connect("changed",
                lambda monitor: self.product_dir.refresh())
        self.entitlement_monitor.connect("changed",
                lambda monitor: self.entitlement_dir.refresh())

    # make a create that does the init
    # and a update() for a name

    def update(self):
        self.create_uep(cert_file=ConsumerIdentity.certpath(),
                        key_file=ConsumerIdentity.keypath())
        self.content_connection = self._create_content_connection()

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

    def create_content_connection(self):
        self.content_connection = self._create_content_connection()

    def _create_content_connection(self):
        return connection.ContentConnection(host=urlparse.urlparse(cfg.get('rhsm', 'baseurl'))[1],
                                            ssl_port=443,
                                            proxy_hostname=cfg.get('server', 'proxy_hostname'),
                                            proxy_port=cfg.get('server', 'proxy_port'),
                                            proxy_user=cfg.get('server', 'proxy_user'),
                                            proxy_password=cfg.get('server', 'proxy_password'))

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
        try:
            consumer = ConsumerIdentity.read()
            self.name = consumer.getConsumerName()
            self.uuid = consumer.getConsumerId()
        # XXX shouldn't catch the global exception here, but that's what
        # existsAndValid did, so this is better.
        except Exception:
            self.name = None
            self.uuid = None

    def is_valid(self):
        return self.uuid is not None

    def getConsumerName(self):
        return self.name

    def getConsumerId(self):
        return self.uuid


class MainWindow(widgets.GladeWidget):
    """
    The new RHSM main window.
    """
    widget_names = ['main_window', 'notebook', 'system_name_label',
                    'next_update_label', 'register_menu_item',
                    'unregister_menu_item', 'redeem_menu_item']

    def __init__(self, backend=None, consumer=None,
                 facts=None, ent_dir=None, prod_dir=None,
                 auto_launch_registration=False):
        super(MainWindow, self).__init__('mainwindow.glade')

        self.backend = backend or Backend()
        self.consumer = consumer or Consumer()
        self.facts = facts or Facts(self.backend.entitlement_dir,
                self.backend.product_dir)

        log.debug("Client Versions: %s " % get_client_versions())
        log.debug("Server Versions: %s " % get_server_versions(self.backend.uep))

        self.product_dir = prod_dir or self.backend.product_dir
        self.entitlement_dir = ent_dir or self.backend.entitlement_dir

        self.system_facts_dialog = factsgui.SystemFactsDialog(self.backend, self.consumer,
                self.facts)

        self.registration_dialog = registergui.RegisterScreen(self.backend,
                self.consumer, self.facts,
                callbacks=[self.registration_changed])

        self.preferences_dialog = PreferencesDialog(self.backend, self.consumer,
                                                    self._get_window())

        self.import_sub_dialog = ImportSubDialog()

        self.network_config_dialog = networkConfig.NetworkConfigDialog()
        self.network_config_dialog.xml.get_widget("closeButton").connect("clicked", self._config_changed)

        self.redeem_dialog = redeem.RedeemDialog(self.backend, self.consumer)

        self.installed_tab_icon = gtk.Image()
        self.installed_tab_icon.set_from_stock(gtk.STOCK_YES,
                gtk.ICON_SIZE_MENU)

        self.installed_tab = InstalledProductsTab(self.backend, self.consumer,
                                                  self.facts,
                                                  self.installed_tab_icon,
                                                  self,
                                                  ent_dir=self.entitlement_dir,
                                                  prod_dir=self.product_dir)
        self.my_subs_tab = MySubscriptionsTab(self.backend, self.consumer,
                                              self.facts, self.main_window,
                                              ent_dir=self.entitlement_dir,
                                              prod_dir=self.product_dir)

        self.all_subs_tab = AllSubscriptionsTab(self.backend, self.consumer,
                self.facts, self.main_window)

        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(self.installed_tab_icon, False, False)
        hbox.pack_start(gtk.Label(self.installed_tab.get_label()), False, False)
        self.notebook.append_page(self.installed_tab.get_content(), hbox)
        hbox.show_all()

        self.notebook.append_page(self.my_subs_tab.get_content(),
                gtk.Label(self.my_subs_tab.get_label()))

        self.glade.signal_autoconnect({
            "on_register_menu_item_activate": self._register_item_clicked,
            "on_unregister_menu_item_activate": self._unregister_item_clicked,
            "on_import_cert_menu_item_activate": self._import_cert_item_clicked,
            "on_view_facts_menu_item_activate": self._facts_item_clicked,
            "on_proxy_config_menu_item_activate": self._proxy_config_item_clicked,
            "on_redeem_menu_item_activate": self._redeem_item_clicked,
            "on_preferences_menu_item_activate": self._preferences_item_clicked,
            "on_about_menu_item_activate": self._about_item_clicked,
            "on_getting_started_menu_item_activate": self._getting_started_item_clicked,
            "on_online_docs_menu_item_activate": self._online_docs_item_clicked,
            "on_quit_menu_item_activate": gtk.main_quit,
        })

        def on_identity_change(filemonitor):
            self.consumer.reload()
            self.refresh()

        self.backend.monitor_identity(on_identity_change)

        self.main_window.show_all()
        self.refresh()

        # Check to see if already registered to old RHN/Spacewalk
        # and show dialog if so
        self._check_rhn_classic()

        if auto_launch_registration and not self.registered():
            self._register_item_clicked(None)

    def registered(self):
        return self.consumer.is_valid()

    def _on_sla_back_button_press(self):
        self._perform_unregister()
        self._register_item_clicked(None)

    def _on_sla_cancel_button_press(self):
        self._perform_unregister()

    def registration_changed(self):
        log.debug("Registration changed, updating main window.")
        self.consumer.reload()
        self.refresh()

    def refresh(self):
        """ Refresh the UI. """
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

        self.installed_tab.set_registered(self.registered())

        self._show_buttons()
        self._show_redemption_buttons()

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
            self.register_menu_item.hide()
            self.unregister_menu_item.show()
        else:
            self.register_menu_item.show()
            self.unregister_menu_item.hide()

    def _show_redemption_buttons(self):
        # Check if consumer can redeem a subscription - if an identity cert exists
        can_redeem = False

        if self.consumer.uuid:
            try:
                consumer = self.backend.uep.getConsumer(self.consumer.uuid, None, None)
                can_redeem = consumer['canActivate']
            except:
                can_redeem = False

        if can_redeem:
            self.redeem_menu_item.show()
        else:
            self.redeem_menu_item.hide()

    def _register_item_clicked(self, widget):
        self.registration_dialog.set_parent_window(self._get_window())
        self.registration_dialog.show()

    def _preferences_item_clicked(self, widget):
        try:
            self.preferences_dialog.show()
        except Exception, e:
            handle_gui_exception(e, _("Error in preferences dialog. Please see /var/log/rhsm/rhsm.log for more information."), self._get_window())

    def _on_unregister_prompt_response(self, dialog, response):
        if not response:
            log.info("unregistrater not confirmed. cancelling")
            return
        log.info("Proceeding with un-registration: %s", self.consumer.uuid)
        self._perform_unregister()

    def _perform_unregister(self):
        try:
            managerlib.unregister(self.backend.uep, self.consumer.uuid)
        except Exception, e:
            log.error("Error unregistering system with entitlement platform.")
            handle_gui_exception(e,
                    _("<b>Errors were encountered during unregister.</b>") + \
                    "\n%s\n" + \
                    _("Please see /var/log/rhsm/rhsm.log for more information."),
                    self.main_window,
                    logMsg="Consumer may need to be manually cleaned up: %s" %
                    self.consumer.uuid)
        self.consumer.reload()

        # We have new credentials, restart virt-who
        restart_virt_who()

        # we've unregistered, clear pools from all subscriptions tab
        # so it's correct if we reshow it
        self.all_subs_tab.clear_pools()
        self.refresh()

    def _unregister_item_clicked(self, widget):
        log.info("Unregister button pressed, asking for confirmation.")
        prompt = messageWindow.YesNoDialog(
                _("<b>Are you sure you want to unregister?</b>"),
                self._get_window())
        prompt.connect('response', self._on_unregister_prompt_response)

    def _proxy_config_item_clicked(self, widget):
        self.network_config_dialog.set_parent_window(self._get_window())
        self.network_config_dialog.show()

    def _facts_item_clicked(self, widget):
        self.system_facts_dialog.set_parent_window(self._get_window())
        self.system_facts_dialog.show()

    def _import_cert_item_clicked(self, widget):
        self.import_sub_dialog.set_parent_window(self._get_window())
        self.import_sub_dialog.show()

    def _update_certificates_button_clicked(self, widget):
        autobind_wizard = registergui.AutobindWizard(self.backend,
                                                     self.consumer, self.facts)
        autobind_wizard.set_parent_window(self._get_window())
        autobind_wizard.show()

    def _redeem_item_clicked(self, widget):
        self.redeem_dialog.set_parent_window(self._get_window())
        self.redeem_dialog.show()

    def _getting_started_item_clicked(self, widget):
        try:
            # unfortunately, gtk.show_uri does not work in RHEL 5
            subprocess.call(["gnome-open", "ghelp:subscription-manager"])
        except Exception, e:
            # if we can't open it, it's probably because the user didn't
            # install the docs, or yelp. no need to bother them.
            log.warn("Unable to open help documentation: %s", e)

    def _about_item_clicked(self, widget):
        about = AboutDialog(self._get_window(), self.backend)
        about.show()

    def _online_docs_item_clicked(self, widget):
        webbrowser.open_new(self._get_online_doc_url())

    def _quit_item_clicked(self):
        self.hide()

    def _config_changed(self, widget):
        # update the backend's UEP in case we changed proxy
        # config. We specify all these settings since they
        # are new and the default UEP init won't get them
        # (it's default args are set at class init time)
        self.backend.update()

    def _check_rhn_classic(self):
        if classic_check.ClassicCheck().is_registered_with_classic():
            prompt = messageWindow.ContinueDialog(
                    linkify(get_branding().REGISTERED_TO_OTHER_WARNING),
                    self.main_window, _("System Already Registered"))
            prompt.connect('response', self._on_rhn_classic_response)

    def _on_rhn_classic_response(self, dialog, response):
        if not response:
            self.main_window.hide()

    def _get_online_doc_url(self):
        lang, encoding = locale.getdefaultlocale()
        url = ONLINE_DOC_URL_TEMPLATE % (lang.replace("_", "-"))
        try:
            urllib2.urlopen(url)
        except urllib2.URLError:
            # Use the default if there is no translation.
            url = ONLINE_DOC_URL_TEMPLATE % ("en-US")
        return url
