from __future__ import print_function, division, absolute_import

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

import locale
import logging
import webbrowser
import os
import threading
import time
import socket

import rhsm.config as config

from six.moves import urllib

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.ga import GLib as ga_GLib

from subscription_manager.branding import get_branding
from subscription_manager.entcertlib import EntCertActionInvoker
from subscription_manager.repolib import YumPluginManager
from rhsmlib.facts.hwprobe import ClassicCheck
from rhsmlib.services import unregister
from subscription_manager.utils import get_client_versions, get_server_versions, parse_baseurl_info, restart_virt_who, print_error

from rhsm import utils as rhsm_utils

from subscription_manager.gui import factsgui
from subscription_manager.gui import messageWindow
from subscription_manager.gui import networkConfig
from subscription_manager.gui import redeem
from subscription_manager.gui import registergui
from subscription_manager.gui import utils
from subscription_manager.gui import widgets

from subscription_manager.gui.about import AboutDialog
from subscription_manager.gui.allsubs import AllSubscriptionsTab
from subscription_manager.gui.importsub import ImportSubDialog
from subscription_manager.gui.installedtab import InstalledProductsTab
from subscription_manager.gui.mysubstab import MySubscriptionsTab
from subscription_manager.gui.preferences import PreferencesDialog
from subscription_manager.gui.utils import handle_gui_exception, linkify
from subscription_manager.gui.reposgui import RepositoriesDialog
from subscription_manager.gui.networkConfig import reset_resolver
from subscription_manager.overrides import Overrides
from subscription_manager.cli import system_exit

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

cfg = config.initConfig()

ONLINE_DOC_URL_TEMPLATE = "https://access.redhat.com/documentation/%s/red_hat_subscription_management/"
ONLINE_DOC_FALLBACK_URL = "https://access.redhat.com/documentation/en-us/red_hat_subscription_management/"

# every GUI browser from https://docs.python.org/2/library/webbrowser.html with updates within last 2 years of writing
PREFERRED_BROWSERS = [
    "mozilla",
    "firefox",
    "epiphany",
    "konqueror",
    "opera",
    "google-chrome",
    "chrome",
    "chromium",
    "chromium-browser",
]

# inform user of the URL in case our detection is outdated
NO_BROWSER_MESSAGE = _("Browser not detected. Documentation URL is %s.")


class Backend(object):
    """
    Wrapper for sharing UEP connections to Candlepin.

    Reference to a Backend object will be passed around UI components, so
    the UEP connection it contains can be modified/recreated and all
    components will have the updated connection.

    This also serves as a common wrapper for certificate directories and methods
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

    # cause cert_sorter to cert_check to cause file_monitor.Monitor to look for
    # for new certs, add this as a main loop timer callback to do that on timer.
    def on_cert_check_timer(self):
        self.cs.force_cert_check()


class MainWindow(widgets.SubmanBaseWidget):
    """
    The new RHSM main window.
    """
    widget_names = ['main_window', 'notebook', 'system_name_label',
                    'register_menu_item', 'unregister_menu_item',
                    'redeem_menu_item', 'settings_menu_item', 'repos_menu_item',
                    'import_cert_menu_item']
    gui_file = "mainwindow"

    def log_server_version(self, uep):
        server_versions = get_server_versions(uep)
        log.debug("Server Versions: %s" % server_versions)
        # Remove this from the GTK main loop
        return False

    def _on_proxy_error_dialog_response(self, window, response):
        if response:
            self.network_config_dialog.show()
        else:
            system_exit(os.EX_UNAVAILABLE)

    def _exit(self, *args):
        system_exit(0)

    def __init__(self, backend=None,
                 ent_dir=None, prod_dir=None,
                 auto_launch_registration=False):
        super(MainWindow, self).__init__()

        rhsm_cfg = config.initConfig()
        proxy_server = rhsm_cfg.get("server", "proxy_hostname")
        proxy_port = int(rhsm_cfg.get("server", "proxy_port") or config.DEFAULT_PROXY_PORT)

        def show_proxy_error_dialog(proxy_auth_required=False):
            """
            When proxy server is set in configuration and it is not
            possible to connect to proxy server, then open dialog
            for setting proxy server.
            """
            if proxy_auth_required:
                proxy_user = rhsm_cfg.get("server", "proxy_user")
                proxy_password = rhsm_cfg.get("server", "proxy_password")
                if proxy_user or proxy_password:
                    err_msg = _("Wrong proxy username or password, please check your settings.")
                else:
                    err_msg = _("Proxy authentication required, please check your settings.")
            else:
                err_msg = _("Proxy connection failed, please check your settings.")
            print_error(err_msg)
            error_dialog = messageWindow.ContinueDialog(err_msg, self._get_window())
            error_dialog.connect("response", self._on_proxy_error_dialog_response)
            self.network_config_dialog = networkConfig.NetworkConfigDialog()
            # Sub-man gui will be terminated after saving settings and it is
            # necessary to start it once again.
            self.network_config_dialog.saveButton.connect("clicked", self._exit)
            self.network_config_dialog.cancelButton.connect("clicked", self._exit)

        self.backend = backend or Backend()
        cp = self.backend.cp_provider.get_consumer_auth_cp()

        # allow specifying no_proxy via api or config
        no_proxy = rhsm_cfg.get('server', 'no_proxy')
        if no_proxy:
            os.environ['no_proxy'] = no_proxy

        rhsm_utils.fix_no_proxy()
        log.debug('Environment variable NO_PROXY=%s will be used' % no_proxy)

        # Don't check the proxy server if the hostname we aim to connect to is covered by no_proxy
        if proxy_server and not urllib.request.proxy_bypass(rhsm_cfg.get('server', 'hostname')):
            if not utils.test_proxy_reachability(proxy_server, proxy_port):
                show_proxy_error_dialog()
                return

            try:
                # Try to send to the simplest Rest API call to Candlepin server.
                # This result will be used for getting version of Candlepin server.
                # See self.log_server_version.
                cp.supports_resource("status")
            except socket.error as err:
                # See https://tools.ietf.org/html/rfc7235#section-4.3
                if "407 Proxy Authentication Required" in err.message:
                    show_proxy_error_dialog(proxy_auth_required=True)
                    return

        self.identity = require(IDENTITY)
        log.debug("Client Versions: %s " % get_client_versions())
        ga_GLib.idle_add(self.log_server_version, cp)

        settings = self.main_window.get_settings()

        # prevent gtk from trying to save a list of recently used files, which
        # as root, causes gtk warning:
        #  "Attempting to set the permissions of `/root/.local/share/recently-used.xbel'
        # The __name__ use is just for the 'origin' value gtk uses to store
        # where a Gtk.Settings value was set.
        settings.set_long_property('gtk-recent-files-max-age', 0,
                                   "%s:%s" % (__name__, type(self).__name__))

        ga_Gtk.Window.set_default_icon_name("subscription-manager")

        self.product_dir = prod_dir or self.backend.product_dir
        self.entitlement_dir = ent_dir or self.backend.entitlement_dir

        self.system_facts_dialog = factsgui.SystemFactsDialog(update_callback=self._handle_facts_updated)

        self.preferences_dialog = PreferencesDialog(self.backend,
                                                    self._get_window())

        self.repos_dialog = RepositoriesDialog(self.backend, self._get_window())

        self.import_sub_dialog = ImportSubDialog()

        self.network_config_dialog = networkConfig.NetworkConfigDialog()
        self.network_config_dialog.saveButton.connect("clicked", self._config_changed)

        self.redeem_dialog = redeem.RedeemDialog(self.backend)

        self.installed_tab_icon = ga_Gtk.Image()
        self.installed_tab_icon.set_from_stock(ga_Gtk.STOCK_YES,
                ga_Gtk.IconSize.MENU)

        self.installed_tab = InstalledProductsTab(self.backend,
                                                  self.installed_tab_icon,
                                                  self,
                                                  ent_dir=self.entitlement_dir,
                                                  prod_dir=self.product_dir)

        self.my_subs_tab = MySubscriptionsTab(self.backend,
                                              self.main_window,
                                              ent_dir=self.entitlement_dir,
                                              prod_dir=self.product_dir)

        self.all_subs_tab = AllSubscriptionsTab(self.backend,
                                                self.main_window)

        hbox = ga_Gtk.HBox(spacing=6)
        hbox.pack_start(self.installed_tab_icon, False, False, 0)
        hbox.pack_start(ga_Gtk.Label(self.installed_tab.get_label()), False, False, 0)
        self.notebook.append_page(self.installed_tab.get_content(), hbox)
        hbox.show_all()

        self.notebook.append_page(self.my_subs_tab.get_content(),
                                  ga_Gtk.Label(self.my_subs_tab.get_label()))

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
            "on_quit_menu_item_activate": ga_Gtk.main_quit,
        })

        # various state tracking for async operations
        self._show_overrides = False
        self._can_redeem = False

        self.backend.cs.add_callback(self.on_cert_sorter_cert_change)

        self.main_window.show_all()

        # Check to see if already registered to old RHN/Spacewalk
        # and show dialog if so
        self._check_rhn_classic()

        # Update everything with compliance data
        self.backend.cs.notify()

        # managergui needs cert_sort.cert_monitor.run_check() to run
        # on a timer to detect cert changes from outside the gui
        # (via rhsmdd for example, or manually provisioned).
        cert_monitor_thread = threading.Thread(target=self._cert_check_timer, name="CertMonitorThread")
        cert_monitor_thread.daemon = True
        cert_monitor_thread.start()

        if auto_launch_registration and not self.registered():
            self._register_item_clicked(None)

        enabled_yum_plugins = YumPluginManager.enable_pkg_plugins()
        if len(enabled_yum_plugins) > 0:
            messageWindow.InfoDialog(
                YumPluginManager.warning_message(enabled_yum_plugins),
                self._get_window(),
                _("Warning - subscription-manager plugins were automatically enabled")
            )

    def registered(self):
        return self.identity.is_valid()

    def _cert_check_timer(self):
        while True:
            self.backend.on_cert_check_timer()
            time.sleep(2.0)

    def _cert_change_update(self):
        # Update installed products
        self.installed_tab.refresh()
        # Update attached subs
        self.my_subs_tab.refresh()
        # Update main window
        self.refresh()
        # Reset repos dialog, see bz 1132919
        self.repos_dialog = RepositoriesDialog(self.backend, self._get_window())

    # When something causes cert_sorter to update it's state, refresh the gui
    # The cert directories being updated will cause this (either noticed
    # from a timer, or via cert_sort.force_cert_check).
    def on_cert_sorter_cert_change(self):
        # gather data used in GUI refresh
        self._show_overrides = self._should_show_overrides()
        self._can_redeem = self._should_show_redeem()
        self.installed_tab.update()
        self.my_subs_tab.update_subscriptions(update_gui=False)  # don't update GUI since we're in a different thread

        # queue up in the main thread since the cert check may be done by another thread.
        ga_GLib.idle_add(self._cert_change_update)

    def _on_sla_back_button_press(self):
        self._perform_unregister()
        self._register_item_clicked(None)

    def _on_sla_cancel_button_press(self):
        self._perform_unregister()

    def on_registration_changed(self):
        # Show the All Subscriptions tab if registered, hide it otherwise:
        if self.registered() and self.notebook.get_n_pages() == 2:
            self.notebook.append_page(self.all_subs_tab.get_content(),
                    ga_Gtk.Label(self.all_subs_tab.get_label()))
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
            #self.register_menu_item.hide()
            self.register_menu_item.set_sensitive(False)
            self.unregister_menu_item.set_sensitive(True)
            self.settings_menu_item.set_sensitive(True)  # preferences
            self.import_cert_menu_item.set_sensitive(False)
        else:
            self.register_menu_item.set_sensitive(True)
            self.unregister_menu_item.set_sensitive(False)
            self.settings_menu_item.set_sensitive(False)
            self.import_cert_menu_item.set_sensitive(True)
        if self._show_overrides:
            self.repos_menu_item.set_sensitive(True)
        else:
            self.repos_menu_item.set_sensitive(False)

    def _should_show_overrides(self):
        is_registered = self.registered()

        show_overrides = False
        try:
            cp = self.backend.cp_provider.get_consumer_auth_cp()
            # This can throw an exception if we cannot connect to the server, bz 1058374
            show_overrides = is_registered and cp.supports_resource('content_overrides')
        except Exception as e:
            log.debug("Failed to check if the server supports resource content_overrides")
            log.debug(e)

        return show_overrides

    def _show_redemption_buttons(self):
        if self._can_redeem:
            self.redeem_menu_item.set_sensitive(True)
        else:
            self.redeem_menu_item.set_sensitive(False)

    def _should_show_redeem(self):
        # Check if consumer can redeem a subscription - if an identity cert exists
        can_redeem = False

        if self.identity.uuid:
            try:
                consumer = self.backend.cp_provider.get_consumer_auth_cp().getConsumer(self.identity.uuid, None, None)
                can_redeem = consumer['canActivate']
            except Exception:
                can_redeem = False

        return can_redeem

    def _register_item_clicked(self, widget):
        registration_dialog = registergui.RegisterDialog(self.backend)
        registration_dialog.register_dialog.connect('destroy',
                                                    self._on_dialog_destroy,
                                                    widget)
        registration_dialog.window.set_transient_for(self._get_window())

        if registration_dialog and widget:
            widget.set_sensitive(False)

        registration_dialog.initialize()
        registration_dialog.show()

    def _on_dialog_destroy(self, obj, widget):
        # bz#1382897 make sure register menu item is left in appropriate state
        if (widget is not self.register_menu_item or not self.registered()) and widget:
            widget.set_sensitive(True)
        return False

    def _preferences_item_clicked(self, widget):
        try:
            self.preferences_dialog.show()
        except Exception as e:
            handle_gui_exception(e, _("Error in preferences dialog."
                                      "Please see /var/log/rhsm/rhsm.log for more information."),
                                 self._get_window())

    def _repos_item_clicked(self, widget):
        try:
            self.repos_dialog.show()
        except Exception as e:
            handle_gui_exception(e, _("Error in repos dialog. "
                                      "Please see /var/log/rhsm/rhsm.log for more information."),
                                 self._get_window())

    def _on_unregister_prompt_response(self, dialog, response):
        if not response:
            log.debug("unregister prompt not confirmed. cancelling")
            return
        log.debug("Proceeding with un-registration: %s", self.identity.uuid)
        self._perform_unregister()

    def _perform_unregister(self):
        try:
            reset_resolver()
            unregister.UnregisterService(self.backend.cp_provider.get_consumer_auth_cp()).unregister()
        except Exception as e:
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
        log.debug("Unregister button pressed, asking for confirmation.")
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
        autobind_wizard = registergui.AutobindWizardDialog(self.backend)
        autobind_wizard.register_dialog.connect('destroy',
                                                self._on_dialog_destroy,
                                                widget)
        autobind_wizard.window.set_transient_for(self._get_window())

        if autobind_wizard and widget:
            widget.set_sensitive(False)

        autobind_wizard.initialize()
        autobind_wizard.show()

    def _redeem_item_clicked(self, widget):
        self.redeem_dialog.set_parent_window(self._get_window())
        self.redeem_dialog.show()

    def _getting_started_item_clicked(self, widget):
        try:
            # try to open documentation in yelp
            ga_Gtk.show_uri(None, 'ghelp:subscription-manager', time.time())
        except Exception as e:
            # if we can't open it, it's probably because the user didn't
            # install the docs, or yelp. no need to bother them.
            log.warn("Unable to open help documentation: %s", e)

    def _about_item_clicked(self, widget):
        about = AboutDialog(self._get_window(), self.backend)
        about.show()

    def _online_docs_item_clicked(self, widget):
        browser = None
        for possible_browser in PREFERRED_BROWSERS:
            try:
                browser = webbrowser.get(possible_browser)
                break
            except webbrowser.Error:
                pass
        if browser is None:
            utils.show_error_window(NO_BROWSER_MESSAGE % (self._get_online_doc_url()))
        else:
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
        if lang is not None:
            url = ONLINE_DOC_URL_TEMPLATE % (lang.replace("_", "-").lower())
        else:
            url = ONLINE_DOC_FALLBACK_URL
        try:
            urllib.request.urlopen(url)
        except urllib.error.URLError:
            # Use the default if there is no translation.
            url = ONLINE_DOC_FALLBACK_URL
        return url

    def _handle_facts_updated(self):
        # see bz 1323271 - update compliance on update of facts
        self.backend.cs.load()
        self.backend.cs.notify()
