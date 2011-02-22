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

import gio
import gtk
import gtk.glade

import messageWindow
import networkConfig
import managerlib
import rhsm.connection as connection
import rhsm.config as config
import constants
from facts import Facts
from certlib import ProductDirectory, EntitlementDirectory, ConsumerIdentity, \
        CertLib, CertSorter, find_first_noncompliant_date

import activate
import factsgui
import widgets
from installedtab import InstalledProductsTab
from mysubstab import MySubscriptionsTab
from allsubs import AllSubscriptionsTab
from compliance import ComplianceAssistant
from importsub import ImportSubDialog
from utils import handle_gui_exception, errorWindow, linkify
from datetime import datetime

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

log = logging.getLogger('rhsm-app.' + __name__)

prefix = os.path.dirname(__file__)
COMPLIANT_IMG = os.path.join(prefix, "data/icons/compliant.svg")
NON_COMPLIANT_IMG = os.path.join(prefix, "data/icons/non-compliant.svg")

cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()

cfg = config.initConfig()

class GladeWrapper(gtk.glade.XML):
    def __init__(self, filename):
        gtk.glade.XML.__init__(self, filename)

    def get_widget(self, widget_name):
        widget = gtk.glade.XML.get_widget(self, widget_name)
        if widget is None:
            print "ERROR: widget %s was not found" % widget_name
            raise Exception ("Widget %s not found" % widget_name)
        return widget

rhsm_xml = GladeWrapper(os.path.join(prefix, "data/rhsm.glade"))
registration_xml = GladeWrapper(os.path.join(prefix,
    "data/registration.glade"))

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

        self.product_monitor = self._monitor(self.product_dir)
        self.entitlement_monitor = self._monitor(self.entitlement_dir)
        self.identity_monitor = gio.File(ConsumerIdentity.PATH).monitor()

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



    def create_admin_uep(self, username=None, password=None):
        self.admin_uep = self._create_uep(username=username, password=password)

    def _monitor(self, directory):
        return gio.File(directory.path).monitor()

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


def fetch_certificates(backend):
    def errToMsg(err):
        return ' '.join(str(err).split('-')[1:]).strip()
    # Force fetch all certs
    try:
        result = backend.certlib.update()
        if result[1]:
            msg = 'Entitlement Certificate(s) update failed due to the following reasons:\n' + \
            '\n'.join(map(errToMsg , result[1]))
            errorWindow(msg)
    except socket.error, e:
        log.error("Socket error: %s %s" %  (e, e.strerror))
        handle_gui_exception(e, e.strerror)
        return False
    except Exception, e:
        log.error("Certificate sync failed")
        log.exception(e)
        return False
    return True


class MainWindow(widgets.GladeWidget):
    """
    The new RHSM main window.
    """
    def __init__(self):
        super(MainWindow, self).__init__('mainwindow.glade',
              ['main_window', 'notebook', 'compliance_status_label',
               'compliance_status_image', 'system_name_label',
               'next_update_label', 'next_update_title', 'register_button',
               'unregister_button', 'compliant_button', 'activate_button'])

        self.backend = Backend()
        self.consumer = Consumer()
        self.facts = Facts()

        self.system_facts_dialog = factsgui.SystemFactsDialog(self.backend, self.consumer,
                self.facts)

        self.registration_dialog = RegisterScreen(self.backend, self.consumer,
                self.facts, callbacks=[self.registration_changed])

        self.import_sub_dialog = ImportSubDialog()

        self.compliance_assistant = ComplianceAssistant(self.backend,
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
            "on_compliant_button_clicked": self._compliant_button_clicked,
            "on_register_button_clicked": self._register_button_clicked,
            "on_unregister_button_clicked": self._unregister_button_clicked,
            "on_add_sub_button_clicked": self._add_sub_button_clicked,
            "on_view_facts_button_clicked": self._facts_button_clicked,
            "on_proxy_config_button_clicked":
                self._network_config_button_clicked,
            "on_activate_button_clicked": self._activate_button_clicked,
        })

        # Register callback for when product/entitlement certs are updated
        def on_cert_change(filemonitor, first_file, other_file, event_type):
            self._set_compliance_status()

        def on_identity_change(filemonitor, first_file, other_file, event_type):
            self.refresh()

        self.backend.monitor_certs(on_cert_change)
        self.backend.monitor_identity(on_identity_change)

        self.main_window.show_all()
        self.refresh()

        # Check to see if already registered to old RHN - and show dialog
        self._check_rhn_classic()

    def registered(self):
        return ConsumerIdentity.existsAndValid()

    def registration_changed(self):
        log.debug("Registration changed, updating main window.")

        self.refresh()

    def refresh(self):
        """ Refresh the UI. """
        self.consumer.reload()
        self._set_compliance_status()

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

    def _compliant_button_clicked(self, widget):
        if self.registered():
            self.compliance_assistant.set_parent_window(self._get_window())
            self.compliance_assistant.show()
        else:
            messageWindow.OkDialog(messageWindow.wrap_text(
                _("You must register before using the compliance assistant.")),
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


    def _set_compliance_status(self):
        """ Updates the compliance status portion of the UI. """
        # Look for products which are out of compliance:
        sorter = CertSorter(ProductDirectory(), EntitlementDirectory())

        warn_count = len(sorter.expired_entitlement_certs) + \
                len(sorter.unentitled_products)

        if warn_count > 0:
            buf = gtk.gdk.pixbuf_new_from_file_at_size(NON_COMPLIANT_IMG, 32,
                    32)
            self.compliance_status_image.set_from_pixbuf(buf)
            self.compliant_button.show()
            # Change wording slightly if just one product out of compliance:
            if warn_count > 1:
                self.compliance_status_label.set_markup(
                        _("You have <b>%s</b> products out of compliance.")
                        % warn_count)
            else:
                self.compliance_status_label.set_markup(
                        _("You have <b>1</b> product out of compliance.") )

        else:
            first_noncompliant = find_first_noncompliant_date()
            buf = gtk.gdk.pixbuf_new_from_file_at_size(COMPLIANT_IMG, 32, 32)
            self.compliance_status_image.set_from_pixbuf(buf)
            self.compliance_status_label.set_text(
                    _("All products are in compliance until %s") % \
                            first_noncompliant.strftime("%x") )
            self.compliant_button.hide()

    def _check_rhn_classic(self):
        if managerlib.is_registered_with_classic():
            prompt = messageWindow.ContinueDialog(
                    linkify(constants.RHN_CLASSIC_WARNING),
                    self._get_window())
            prompt.connect('response', self._on_rhn_classic_response)

    def _on_rhn_classic_response(self, dialog, response):
        if not response:
            self.main_window.hide()

class RegisterScreen:
    """
      Registration Widget Screen
    """

    def __init__(self, backend, consumer, facts=None, callbacks=None):
        """
        Callbacks will be executed when registration status changes.
        """
        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.callbacks = callbacks

        dic = {"on_register_cancel_button_clicked": self.cancel,
               "on_register_button_clicked": self.onRegisterAction,
            }

        registration_xml.signal_autoconnect(dic)
        self.registerWin = registration_xml.get_widget("register_dialog")
        self.registerWin.connect("hide", self.cancel)
        self.registerWin.connect("delete_event", self.delete_event)
        self.initializeConsumerName()

        self.uname = registration_xml.get_widget("account_login")
        self.passwd = registration_xml.get_widget("account_password")
        self.consumer_name = registration_xml.get_widget("consumer_name")

    def show(self):
        self.registerWin.present()

    def delete_event(self, event, data=None):
        return self.close_window()

    def cancel(self, button):
        self.close_window()

    def initializeConsumerName(self):
        consumername = registration_xml.get_widget("consumer_name")
        if not consumername.get_text():
            consumername.set_text(socket.gethostname())

    # callback needs the extra arg, so just a wrapper here
    def onRegisterAction(self, button):
        self.register()

    def register(self, testing=None):
        username = self.uname.get_text()
        password = self.passwd.get_text()
        consumername = self.consumer_name.get_text()

        if not self.validate_consumername(consumername):
            return False

        if not self.validate_account():
            return False

        # for firstboot -t
        if testing:
            return True

        try:
            self.backend.create_admin_uep(username=username,
                                          password=password)
            newAccount = self.backend.admin_uep.registerConsumer(name=consumername,
                    facts=self.facts.get_facts())
            managerlib.persist_consumer_cert(newAccount)
            self.consumer.reload()
            # reload CP instance with new ssl certs
            if self.auto_subscribe():
                # try to auomatically bind products
                products = managerlib.getInstalledProductHashMap()
                try:
                    self.backend.uep.bindByProduct(self.consumer.uuid,
                            products.values())
                    log.info("Automatically subscribed to products: %s " \
                            % ", ".join(products.keys()))
                except Exception, e:
                    log.exception(e)
                    log.warning("Warning: Unable to auto subscribe to %s" \
                            % ", ".join(products.keys()))
                # force update of certs
                if not fetch_certificates(self.backend):
                    return False

            self.close_window()

            self.emit_consumer_signal()

        except Exception, e:
           return handle_gui_exception(e, constants.REGISTER_ERROR)
        return True

    def emit_consumer_signal(self):
        for method in self.callbacks:
            method()

    def close_window(self):
        self.registerWin.hide()
        return True

    def auto_subscribe(self):
        self.autobind = registration_xml.get_widget("auto_bind")
        return self.autobind.get_active()

    def validate_consumername(self, consumername):
        if not consumername:
            setArrowCursor()
            errorWindow(_("You must enter a system name."))
            self.consumer_name.grab_focus()
            return False
        return True

    def validate_account(self):
        # validate / check user name
        if self.uname.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a login."))
            self.uname.grab_focus()
            return False

        if self.passwd.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a password."))
            self.passwd.grab_focus()
            return False
        return True

    def set_parent_window(self, window):
        self.registerWin.set_transient_for(window)


def setArrowCursor():
    pass


def setBusyCursor():
    pass

