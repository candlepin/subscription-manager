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
        CertLib, CertSorter

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

from logutil import getLogger
log = getLogger(__name__)

prefix = os.path.dirname(__file__)
COMPLIANT_IMG = os.path.join(prefix, "data/icons/compliant.svg")
NON_COMPLIANT_IMG = os.path.join(prefix, "data/icons/non-compliant.svg")
UPDATE_FILE = '/var/run/rhsm/update'

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

    def __init__(self, uep):
        self.uep = uep

        self.product_dir = ProductDirectory()
        self.entitlement_dir = EntitlementDirectory()
        self.certlib = CertLib(uep=self.uep)

        self.product_monitor = self._monitor(self.product_dir)
        self.entitlement_monitor = self._monitor(self.entitlement_dir)
        self.identity_monitor = gio.File(ConsumerIdentity.PATH).monitor()

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
              ['main_window', 'notebook', 'compliance_count_label',
               'compliance_status_label', 'compliance_status_image',
               'button_bar', 'system_name_label', 'next_update_label',
               'next_update_title'])

        self.backend = Backend(connection.UEPConnection(
            cert_file=ConsumerIdentity.certpath(),
            key_file=ConsumerIdentity.keypath()))
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
        })

        # Register callback for when product/entitlement certs are updated
        def on_cert_change(filemonitor, first_file, other_file, event_type):
            self._set_compliance_status()

        def on_identity_change(filemonitor, first_file, other_file, event_type):
            self.refresh()

        def on_cert_update(filemonitor, first_file, other_file, event_type):
            self._set_next_update()

        self.backend.monitor_certs(on_cert_change)
        self.backend.monitor_identity(on_identity_change)

        # For updating the 'Next Update' time
        gio.File(UPDATE_FILE).monitor().connect('changed', on_cert_update)

        self.refresh()

        self.main_window.show_all()

    def registered(self):
        return ConsumerIdentity.existsAndValid()

    def registration_changed(self):
        log.debug("Registration changed, updating main window.")

        self.refresh()

    def refresh(self):
        """ Refresh the UI. """
        self._set_compliance_status()
        self._set_system_name()
        self._set_next_update()

        # Show the All Subscriptions tab if registered, hide it otherwise:
        if self.registered() and self.notebook.get_n_pages() == 2:
            self.notebook.append_page(self.all_subs_tab.get_content(),
                    gtk.Label(self.all_subs_tab.get_label()))
        elif not self.registered() and self.notebook.get_n_pages() == 3:
            self.notebook.set_current_page(0)
            self.notebook.remove_page(2)

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
        log.debug("Showing buttons.")
        # Clear all existing buttons:
        self.button_bar.foreach(lambda widget: self.button_bar.remove(widget))

        registered = self.registered()
        if not registered:
            self._show_register_button()
        else:
            self._show_unregister_button()

        self._show_add_sub_button()


        self._show_facts_button()

        self._show_network_config_button()

        self.button_bar.show_all()

    def _show_register_button(self):
        """
        Adds the register button to the button bar.
        """
        button = gtk.Button(label=_("Register System"))
        button.connect("clicked", self._register_button_clicked)
        self.button_bar.add(button)

    def _show_unregister_button(self):
        """
        Adds the unregister button to the button bar.
        """
        button = gtk.Button(label=_("Unregister System"))
        button.connect("clicked", self._unregister_button_clicked)
        self.button_bar.add(button)

    def _show_network_config_button(self):
        """
        Adds the network config button to the button bar.
        """
        button = gtk.Button(label=_("Proxy Configuration"))
        button.connect("clicked", self._network_config_button_clicked)
        self.button_bar.add(button)

    def _show_facts_button(self):
        """
        Adds the show facts button to the button bar.
        """
        button = gtk.Button(label=_("View My System Facts"))
        button.connect("clicked", self._facts_button_clicked)
        self.button_bar.add(button)

    def _show_add_sub_button(self):
        """
        Adds the dialog for manually importing a subscription.
        """
        log.debug("Add subscription button pressed.")
        button = gtk.Button(label=_("Add Subscription"))
        button.connect("clicked", self._add_sub_button_clicked)
        self.button_bar.add(button)

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

    def _config_changed(self, widget):
        # update the backend's UEP in case we changed proxy
        # config. We specify all these settings since they
        # are new and the default UEP init won't get them
        # (it's default args are set at class init time)
        self.backend.uep = connection.UEPConnection(
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



    def _set_compliance_status(self):
        """ Updates the compliance status portion of the UI. """
        # Look for products which are out of compliance:
        sorter = CertSorter(ProductDirectory(), EntitlementDirectory())

        warn_count = len(sorter.expired_entitlement_certs) + \
                len(sorter.unentitled_products)

        if warn_count > 0:
            self.compliance_status_image.set_from_file(NON_COMPLIANT_IMG)
            self.compliance_count_label.set_markup(
                    '<span size="large"><b>%s</b></span>' % str(warn_count))
            # Change wording slightly if just one product out of compliance:
            if warn_count > 1:
                self.compliance_status_label.set_text(
                        _("You have %s products which are out of compliance.")
                        % warn_count)
            else:
                self.compliance_status_label.set_text(
                        _("You have 1 product which is out of compliance.") )

        else:
            self.compliance_status_image.set_from_file(COMPLIANT_IMG)
            self.compliance_count_label.set_text("")
            self.compliance_status_label.set_text(
                    _("Your system is compliant.") )

    def _set_system_name(self):
        self.consumer.reload()

        # TODO:  Need to escape markup here
        name = self.consumer.name or _('Not registered')
        self.system_name_label.set_markup('<b>%s</b>' % name)

    def _set_next_update(self):
        try:
            next_update = long(file(UPDATE_FILE).read())
        except:
            next_update = None

        if next_update:
            # TODO:  show/hide was not working here - this is a little hacky...
            self.next_update_title.set_text(_('Next Update:'))

            update_time = datetime.fromtimestamp(next_update)
            self.next_update_label.set_text(update_time.ctime())
        else:
            self.next_update_title.set_text('')
            self.next_update_label.set_text('')


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
            admin_cp = connection.UEPConnection(username=username,
                    password=password)
            newAccount = admin_cp.registerConsumer(name=consumername,
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

