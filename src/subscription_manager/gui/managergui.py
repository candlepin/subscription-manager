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

from subscription_manager.injection import require, IDENTITY, CERT_SORTER, CP_PROVIDER
import subscription_manager.injection as inj

import gettext
import locale
import logging
import subprocess
import urllib2
import webbrowser

import gtk

import rhsm.config as config

from subscription_manager.branding import get_branding
from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.facts import Facts
from subscription_manager.hwprobe import ClassicCheck
from subscription_manager import managerlib
from subscription_manager.utils import get_client_versions, get_server_versions, parse_baseurl_info, restart_virt_who

from subscription_manager.gui import factsgui
from subscription_manager.gui import messageWindow
from subscription_manager.gui import networkConfig
from subscription_manager.gui import redeem
from subscription_manager.gui import registergui
from subscription_manager.gui import widgets

from subscription_manager.gui.about import AboutDialog
from subscription_manager.gui.allsubs import AllSubscriptionsTab
from subscription_manager.gui.importsub import ImportSubDialog
from subscription_manager.gui.installedtab import InstalledProductsTab
from subscription_manager.gui.mysubstab import MySubscriptionsTab
from subscription_manager.gui.preferences import PreferencesDialog
from subscription_manager.gui.utils import handle_gui_exception, linkify
from subscription_manager.gui.reposgui import RepositoriesDialog
from subscription_manager.overrides import Overrides


_ = gettext.gettext

gettext.textdomain("rhsm")

gtk.window_set_default_icon_name("subscription-manager")

log = logging.getLogger('rhsm-app.' + __name__)

cfg = config.initConfig()

ONLINE_DOC_URL_TEMPLATE = "https://access.redhat.com/knowledge/docs/Red_Hat_Subscription_Management/?locale=%s"
ONLINE_DOC_FALLBACK_URL = "https://access.redhat.com/knowledge/docs/Red_Hat_Subscription_Management/"


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
        self.identity = require(IDENTITY)
        self.cp_provider = require(CP_PROVIDER)

        self.update()

        self.product_dir = inj.require(inj.PROD_DIR)
        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.certlib = EntCertActionInvoker()
        self.overrides = Overrides()

        self.cs = require(CERT_SORTER)

    # make a create that does the init
    # and a update() for a name
    def update(self):
        self.create_uep()
        self.create_content_connection()

    def create_uep(self):
        # Re-initialize our connection:
        self.cp_provider.set_connection_info()

        # These objects hold a reference to the old uep and must be updated:
        # FIXME: We should find a way to update the connection so that the
        #        conncection objects are refreshed rather than recreated.

        self.certlib = EntCertActionInvoker()
        self.overrides = Overrides()

    def create_content_connection(self):
        (cdn_hostname, cdn_port, cdn_prefix) = parse_baseurl_info(cfg.get('rhsm', 'baseurl'))

        self.cp_provider.set_content_connection_info(cdn_hostname=cdn_hostname,
                                                     cdn_port=cdn_port)
        # ContentConnection now handles reading the proxy information
        return self.cp_provider.get_content_connection()


class MainWindow(widgets.SubmanBaseWidget):
    """
    The new RHSM main window.
    """
    widget_names = ['main_window', 'notebook', 'system_name_label',
                    'register_menu_item', 'unregister_menu_item',
                    'redeem_menu_item', 'settings_menu_item', 'repos_menu_item']
    gui_file = "mainwindow.glade"

    def __init__(self, backend=None, facts=None,
                 ent_dir=None, prod_dir=None,
                 auto_launch_registration=False):
        super(MainWindow, self).__init__()

        self.backend = backend or Backend()
        self.identity = require(IDENTITY)

        self.facts = facts or Facts(self.backend.entitlement_dir,
                self.backend.product_dir)
        # We need to make sure facts are loaded immediately, some GUI operations
        # are done in separate threads, and if facts try to load in another
        # thread the virt guest detection code breaks due to hwprobe's use of
        # signals.
        self.facts.get_facts()

        log.debug("Client Versions: %s " % get_client_versions())
        log.debug("Server Versions: %s " % get_server_versions(self.backend.cp_provider.get_consumer_auth_cp()))

        settings = self.main_window.get_settings()
        # prevent gtk from trying to save a list of recently used files, which
        # as root, causes gtk warning:
        #  "Attempting to set the permissions of `/root/.local/share/recently-used.xbel'
        # The __name__ use is just for the 'origin' value gtk uses to store
        # where a Gtk.Settings value was set.
        settings.set_long_property('gtk-recent-files-max-age', 0,
                                   "%s:%s" % (__name__, type(self).__name__))

        self.product_dir = prod_dir or self.backend.product_dir
        self.entitlement_dir = ent_dir or self.backend.entitlement_dir

        self.system_facts_dialog = factsgui.SystemFactsDialog(self.facts)

        self.registration_dialog = registergui.RegisterScreen(self.backend, self.facts,
                                                              self._get_window())

        self.preferences_dialog = PreferencesDialog(self.backend,
                                                    self._get_window())

        self.repos_dialog = RepositoriesDialog(self.backend, self._get_window())

        self.import_sub_dialog = ImportSubDialog()

        self.network_config_dialog = networkConfig.NetworkConfigDialog()
        self.network_config_dialog.saveButton.connect("clicked", self._config_changed)

        self.redeem_dialog = redeem.RedeemDialog(self.backend)

        self.installed_tab_icon = gtk.Image()
        self.installed_tab_icon.set_from_stock(gtk.STOCK_YES,
                gtk.ICON_SIZE_MENU)

        self.installed_tab = InstalledProductsTab(self.backend,
                                                  self.facts,
                                                  self.installed_tab_icon,
                                                  self,
                                                  ent_dir=self.entitlement_dir,
                                                  prod_dir=self.product_dir)
        self.my_subs_tab = MySubscriptionsTab(self.backend,
                                              self.main_window,
                                              ent_dir=self.entitlement_dir,
                                              prod_dir=self.product_dir)

        self.all_subs_tab = AllSubscriptionsTab(self.backend,
                                                self.facts,
                                                self.main_window)

        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(self.installed_tab_icon, False, False)
        hbox.pack_start(gtk.Label(self.installed_tab.get_label()), False, False)
        self.notebook.append_page(self.installed_tab.get_content(), hbox)
        hbox.show_all()

        self.notebook.append_page(self.my_subs_tab.get_content(),
                gtk.Label(self.my_subs_tab.get_label()))

        self.connect_signals({
            "on_register_menu_item_activate": self._register_item_clicked,
            "on_unregister_menu_item_activate": self._unregister_item_clicked,
            "on_import_cert_menu_item_activate": self._import_cert_item_clicked,
            "on_view_facts_menu_item_activate": self._facts_item_clicked,
            "on_proxy_config_menu_item_activate": self._proxy_config_item_clicked,
            "on_redeem_menu_item_activate": self._redeem_item_clicked,
            "on_preferences_menu_item_activate": self._preferences_item_clicked,
            "on_repos_menu_item_activate": self._repos_item_clicked,
            "on_about_menu_item_activate": self._about_item_clicked,
            "on_getting_started_menu_item_activate": self._getting_started_item_clicked,
            "on_online_docs_menu_item_activate": self._online_docs_item_clicked,
            "on_quit_menu_item_activate": gtk.main_quit,
        })

        def on_cert_change():
            # Update installed products
            self.installed_tab.update_products()
            self.installed_tab._set_validity_status()
            # Update attached subs
            self.my_subs_tab.update_subscriptions()
            # Update main window
            self.refresh()
            # Reset repos dialog, see bz 1132919
            self.repos_dialog = RepositoriesDialog(self.backend, self._get_window())

        self.backend.cs.add_callback(on_cert_change)

        self.main_window.show_all()

        # Check to see if already registered to old RHN/Spacewalk
        # and show dialog if so
        self._check_rhn_classic()

        # Update everything with compliance data
        self.backend.cs.notify()

        if auto_launch_registration and not self.registered():
            self._register_item_clicked(None)

    def registered(self):
        return self.identity.is_valid()

    def _on_sla_back_button_press(self):
        self._perform_unregister()
        self._register_item_clicked(None)

    def _on_sla_cancel_button_press(self):
        self._perform_unregister()

    def on_registration_changed(self):
        # Show the All Subscriptions tab if registered, hide it otherwise:
        if self.registered() and self.notebook.get_n_pages() == 2:
            self.notebook.append_page(self.all_subs_tab.get_content(),
                    gtk.Label(self.all_subs_tab.get_label()))
        elif not self.registered() and self.notebook.get_n_pages() == 3:
            self.notebook.set_current_page(0)
            self.notebook.remove_page(2)

        # we've unregistered, clear pools from all subscriptions tab
        # so it's correct if we reshow it
        self.all_subs_tab.sub_details.clear()
        self.all_subs_tab.clear_pools()

        self.installed_tab.set_registered(self.registered())

        self._show_buttons()
        self._show_redemption_buttons()

    def refresh(self):
        """ Refresh the UI. """
        # Always run on startup, when there is no last_uuid
        if not hasattr(self, 'last_uuid') or self.identity.uuid != self.last_uuid:
            self.last_uuid = self.identity.uuid
            self.on_registration_changed()

        self.all_subs_tab.refresh()
        self.installed_tab.refresh()
        self.my_subs_tab.refresh()

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
        is_registered = self.registered()
        if is_registered:
            self.register_menu_item.hide()
            self.unregister_menu_item.show()
            self.settings_menu_item.show()  # preferences
        else:
            self.register_menu_item.show()
            self.unregister_menu_item.hide()
            self.settings_menu_item.hide()

        show_overrides = False
        try:
            cp = self.backend.cp_provider.get_consumer_auth_cp()
            # This can throw an exception if we cannot connect to the server, bz 1058374
            show_overrides = is_registered and cp.supports_resource('content_overrides')
        except Exception, e:
            log.debug("Failed to check if the server supports resource content_overrides")
            log.debug(e)

        if show_overrides:
            self.repos_menu_item.show()
        else:
            self.repos_menu_item.hide()

    def _show_redemption_buttons(self):
        # Check if consumer can redeem a subscription - if an identity cert exists
        can_redeem = False

        if self.identity.uuid:
            try:
                consumer = self.backend.cp_provider.get_consumer_auth_cp().getConsumer(self.identity.uuid, None, None)
                can_redeem = consumer['canActivate']
            except Exception:
                can_redeem = False

        if can_redeem:
            self.redeem_menu_item.show()
        else:
            self.redeem_menu_item.hide()

    def _register_item_clicked(self, widget):
        self.registration_dialog.show()

    def _preferences_item_clicked(self, widget):
        try:
            self.preferences_dialog.show()
        except Exception, e:
            handle_gui_exception(e, _("Error in preferences dialog."
                                      "Please see /var/log/rhsm/rhsm.log for more information."),
                                 self._get_window())

    def _repos_item_clicked(self, widget):
        try:
            self.repos_dialog.show()
        except Exception, e:
            handle_gui_exception(e, _("Error in repos dialog. "
                                      "Please see /var/log/rhsm/rhsm.log for more information."),
                                 self._get_window())

    def _on_unregister_prompt_response(self, dialog, response):
        if not response:
            log.debug("unregister prompt not confirmed. cancelling")
            return
        log.info("Proceeding with un-registration: %s", self.identity.uuid)
        self._perform_unregister()

    def _perform_unregister(self):
        try:
            managerlib.unregister(self.backend.cp_provider.get_consumer_auth_cp(), self.identity.uuid)
        except Exception, e:
            log.error("Error unregistering system with entitlement platform.")
            handle_gui_exception(e, _("<b>Errors were encountered during unregister.</b>") +
                                      "\n%s\n" +
                                      _("Please see /var/log/rhsm/rhsm.log for more information."),
                                self.main_window,
                                log_msg="Consumer may need to be manually cleaned up: %s" %
                                self.identity.uuid)
        # managerlib.unregister removes product and entitlement directories
        self.backend.product_dir.__init__()
        self.backend.entitlement_dir.__init__()

        # We have new credentials, restart virt-who
        restart_virt_who()

        self.backend.cs.force_cert_check()

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
                                                     self.facts,
                                                     self._get_window())
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
        if ClassicCheck().is_registered_with_classic():
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
            url = ONLINE_DOC_FALLBACK_URL
        return url
