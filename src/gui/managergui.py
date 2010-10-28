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
import re
import sys
import shutil
import socket

import gtk
import gtk.glade
import gobject
import signal
import pango

import messageWindow
import progress
import managerlib
import connection
import config
import constants
from facts import getFacts
from certlib import EntitlementDirectory, ConsumerIdentity, CertLib
from OpenSSL.crypto import load_certificate, FILETYPE_PEM
from socket import error as socket_error
from M2Crypto import SSL
import xml.sax.saxutils

import factsgui

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

from logutil import getLogger
log = getLogger(__name__)

prefix = os.path.dirname(__file__)
subs_full = os.path.join(prefix, "data/icons/subsmgr-full.png")
subs_empty = os.path.join(prefix, "data/icons/subsmgr-empty.png")

cfg = config.initConfig()
cert_file = ConsumerIdentity.certpath()
key_file = ConsumerIdentity.keypath()
UEP = connection.UEPConnection(cert_file=cert_file, key_file=key_file)

CONSUMER_SIGNAL = "on_consumer_changed"

# Register new signal emitted by various dialogs when entitlement data changes
gobject.signal_new(CONSUMER_SIGNAL, gtk.Dialog, gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())
gobject.signal_new(CONSUMER_SIGNAL, gtk.Window, gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())

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
regtoken_xml = GladeWrapper(os.path.join(prefix,
    "data/regtoken.glade"))

certlib = CertLib()
ENT_CONFIG_DIR = os.path.join(cfg.get('rhsm', 'entitlementCertDir'), 'product')


def get_consumer():
    if not ConsumerIdentity.existsAndValid():
        return {}
    consumer = ConsumerIdentity.read()
    consumer_info = {"consumer_name": consumer.getConsumerName(),
                     "uuid": consumer.getConsumerId()}
    return consumer_info

consumer = get_consumer()


def fetch_certificates():
    def errToMsg(err):
        return ' '.join(str(err).split('-')[1:]).strip()
    # Force fetch all certs
    try:
        result = certlib.update()
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

register_screen = None
regtoken_screen = None


def show_register_screen():
    global register_screen

    if register_screen:
        register_screen.show()
    else:
        register_screen = RegisterScreen()


def show_regtoken_screen():
    global regtoken_screen

    if regtoken_screen:
        regtoken_screen.show()
    else:
        regtoken_screen = RegistrationTokenScreen()


def handle_gui_exception(e, callback, logMsg = None, showMsg = True):
    if logMsg:
        log.error(logMsg)
    log.exception(e)

    if showMsg:
        if isinstance(e, socket_error):
            errorWindow(_('network error, unable to connect to server'))
        elif isinstance(e, SSL.SSLError):
            errorWindow(_('Unable to verify server\'s identity: %s' % str(e)))
        elif isinstance(e, connection.RestlibException):
            errorWindow(callback % linkify(e.msg))
        else:
            if hasattr(callback, '__call__'):
                errorWindow(_(callback(e)))
            else:
                errorWindow(_(callback)) #just a string
    return False


class ManageSubscriptionPage:
    """ Main Subscription Manager window. """

    def __init__(self):
        self.pname_selected = None
        self.pselect_status = None
        self.psubs_selected = None

        self.state_icon_map = {"Expired": gtk.STOCK_DIALOG_WARNING,
                               "Not Subscribed": gtk.STOCK_DIALOG_QUESTION,
                               "Subscribed": gtk.STOCK_APPLY,
                               "Not Installed": gtk.STOCK_DIALOG_QUESTION}
        self.create_gui()

    def create_gui(self):
        global UEP

        self.add_subscription_screen = None
        self.import_certificate_screen = None
        self.populateProductDialog()
        self.setRegistrationStatus()
        self.updateMessage()

        self.system_facts_dialog = factsgui.SystemFactsDialog()

        dic = {
               "on_add_button_clicked": self.addSubButtonAction,
               "on_update_button_clicked": self.updateSubButtonAction,
               "on_unsubscribe_button_clicked": self.onUnsubscribeAction,
            }
        rhsm_xml.signal_autoconnect(dic)
        self.setButtonState()
        self.mainWin = rhsm_xml.get_widget("manage_subscriptions_dialog")
        self.mainWin.connect("delete-event", gtk.main_quit)
        self.mainWin.connect("hide", gtk.main_quit)

        self.button_bar = rhsm_xml.get_widget("action_area")
        self.show_buttons()

        # TODO: Do we really need to redraw the whole GUI for this?
        # Register custom signal for consumer changes
        registration_window = registration_xml.get_widget('register_dialog')
        registration_window.connect(CONSUMER_SIGNAL, self.reload_gui)
        self.mainWin.connect(CONSUMER_SIGNAL, self.reload_gui)
        self.show()

    def reload_gui(self, widget=None):
        log.debug("reload_gui")
        self.setRegistrationStatus()
        self.updateProductDialog()
        self.show_buttons()

    def show_buttons(self):
        """
        Display the button bar. Called both when the screen is created, and
        upon subsequent refreshes.

        Subclasses (i.e. firstboot) may override this method to hide
        certain buttons.
        """
        log.debug("Showing buttons.")
        self.button_bar.foreach(lambda widget: self.button_bar.remove(widget))
        exists = ConsumerIdentity.existsAndValid()
        self._show_facts_button()
        if exists:
            self._show_regtoken_button()
            self._show_unregister_button()
        else:
            self._show_register_button()
        self._show_close_button()

        self.button_bar.show_all()

    def _show_regtoken_button(self):
        """
        Adds the activate subscription button to the button bar.
        """
        button = gtk.Button(label=_("Activate a Subscription"))
        button.connect("clicked", self.show_regtoken_dialog)
        self.button_bar.add(button)

    def _show_facts_button(self):
        """
        Adds the show facts button to the button bar.
        """
        button = gtk.Button(label=_("View System Facts"))
        button.connect("clicked", self.show_facts_dialog)
        self.button_bar.add(button)

    def _show_register_button(self):
        """
        Adds the register button to the button bar.
        """
        button = gtk.Button(label=_("Register System"))
        button.connect("clicked", self.show_register_dialog)
        self.button_bar.add(button)

    def _show_unregister_button(self):
        """
        Adds the unregister button to the button bar.
        """
        button = gtk.Button(label=_("Unregister System"))
        button.connect("clicked", self.show_unregister_dialog)
        self.button_bar.add(button)

    def _show_close_button(self):
        """
        Adds the close button to the button bar.
        """
        button = gtk.Button(label=_("Close"))
        button.connect("clicked", gtk.main_quit)
        self.button_bar.add(button)

    def show(self):
        self.mainWin.show()

    def show_facts_dialog(self, button):
        self.system_facts_dialog.show()

    def show_regtoken_dialog(self, button):
        show_regtoken_screen()

    def show_register_dialog(self, button):
        show_register_screen()

    def refresh(self):
        self.mainWin.destroy()

    def show_add_subscription_screen(self):
        if not self.add_subscription_screen:
            self.add_subscription_screen = AddSubscriptionScreen()
            self.add_subscription_screen.addWin.connect('hide', self.reload_gui)

        self.add_subscription_screen.show()

    def show_import_certificate_screen(self):
        if not self.import_certificate_screen:
            self.import_certificate_screen = ImportCertificate()
            self.import_certificate_screen.importWin.connect('hide',
                    self.reload_gui)

        self.import_certificate_screen.show()

    def addSubButtonAction(self, button):
        if consumer.has_key('uuid'):
            self.show_add_subscription_screen()
        else:
            self.show_import_certificate_screen()

    def updateSubButtonAction(self, button):
        if self.pname_selected:
            log.info("Product %s selected for update" % self.pname_selected)
            if consumer.has_key('uuid'):
                UpdateSubscriptionScreen(self.pname_selected, self.mainWin)
            else:
                self.show_import_certificate_screen()

    def setButtonState(self, state=False):
        self.button_update = rhsm_xml.get_widget("update_button")
        self.button_unsubscribe = rhsm_xml.get_widget("unsubscribe_button")
        self.button_update.set_sensitive(state)
        self.button_unsubscribe.set_sensitive(state)

    def updateProductDialog(self):
        self.warn_count = 0
        self.productList.clear()
        for product in managerlib.getInstalledProductStatus():
            log.info("Product %s", product)
            markup_status = product[1]
            if product[1] in ["Expired", "Not Subscribed", "Not Installed"]:
                self.warn_count += 1
                markup_status = '<span foreground="red"><b>%s</b></span>' % \
                        xml.sax.saxutils.escape(product[1])
            self.status_icon = self.tv_products.render_icon(
                    self.state_icon_map[product[1]], size=gtk.ICON_SIZE_MENU)
            self.productList.append((self.status_icon, product[0], product[3], 
                markup_status, product[2], product[4]))
        self.tv_products.set_model(self.productList)
        self.updateMessage()


    def populateProductDialog(self):
        self.tv_products = rhsm_xml.get_widget("treeview_updates")
        self.productList = gtk.ListStore(gtk.gdk.Pixbuf, 
                gobject.TYPE_STRING, gobject.TYPE_STRING,
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)

        self.updateProductDialog()

        #self.tv_products.set_rules_hint(True)

        col = gtk.TreeViewColumn('')
        col.set_spacing(15)
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        cell.set_fixed_size(-1, 35)
        col.set_attributes(cell, pixbuf=0)
        self.tv_products.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_spacing(6)
        col.set_sort_column_id(1)
        col.set_resizable(True)
        cell.set_fixed_size(250, -1)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Contract"), gtk.CellRendererText(), text=5)
        col.set_sort_column_id(2)
        col.set_spacing(6)
        self.tv_products.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Status"), cell, markup=3)
        col.set_sort_column_id(3)
        col.set_spacing(6)
        self.tv_products.append_column(col)

        cell = gtk.CellRendererText()
        cell.set_fixed_size(250, -1)
        col = gtk.TreeViewColumn(_("Expires"), cell, text=4)
        col.set_sort_column_id(4)
        col.set_resizable(True)
        col.set_spacing(6)
        self.tv_products.append_column(col)

        #self.productList.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.selection = self.tv_products.get_selection()
        self.selection.connect('changed', self.on_selection)

        self.setRegistrationStatus()

    def on_selection(self, selection):
        def set_text(text):
            pdetails = rhsm_xml.get_widget("textview_details")
            pdetails.get_buffer().set_text(text)
            pdetails.set_cursor_visible(False)
            pdetails.show()
            
        items, iter = selection.get_selected()
        if iter is None:
            set_text('')
            self.setButtonState(False)
            return

        self.pname_selected = items.get_value(iter, 1)
        self.psubs_selected = items.get_value(iter, 2)
        self.pselect_status = items.get_value(iter, 3)
        desc = managerlib.getProductDescription(self.pname_selected)
        set_text(desc)
        status = ''.join([x.split('>', 1)[-1] for x in self.pselect_status.split('<')])
        self.setButtonState(status != "Not Subscribed")

    def updateMessage(self):
        def set_label_and_icon(msg, icon = subs_empty):
            self.sumlabel = rhsm_xml.get_widget("summary_label")
            self.sm_icon = rhsm_xml.get_widget("sm_icon")
            self.sumlabel.set_label(msg)
            self.sm_icon.set_from_file(icon)

        if self.warn_count > 1:
            set_label_and_icon(constants.WARN_SUBSCRIPTIONS % self.warn_count)
        elif self.warn_count == 1:
            set_label_and_icon(constants.WARN_ONE_SUBSCRIPTION % self.warn_count)
        else:
            set_label_and_icon(constants.COMPLIANT_STATUS, subs_full)

    def setRegistrationStatus(self):
        """
        Updates the main window to reflect current registration status.
        """
        exists = ConsumerIdentity.existsAndValid()
        log.debug("updating registration status.. consumer exists?: %s", exists)

        reg_as_label = rhsm_xml.get_widget('registered_as_label')
        if exists:
            reg_as_label.set_label(_("This system is registered as: <b>%s</b>" %
                ConsumerIdentity.read().getConsumerId()))
        else:
            reg_as_label.set_label(_("This system is not registered."))


    def onUnsubscribeAction(self, button):
        global UEP
        if not self.psubs_selected:
            return
        log.info("Product %s selected for unsubscribe" % self.pname_selected)
        dlg = messageWindow.YesNoDialog(constants.CONFIRM_UNSUBSCRIBE % 
                xml.sax.saxutils.escape(self.pname_selected), self.mainWin)
        if not dlg.getrc():
            return

        # only unbind if we are registered to a server
        if ConsumerIdentity.exists():
            try:
                UEP.unbindBySerial(consumer['uuid'], self.psubs_selected)
                log.info("This machine is now unsubscribed from Product %s " \
                          % self.pname_selected)
                if self.add_subscription_screen:
                    self.add_subscription_screen.subs_changed = True

            except Exception, e:
                handle_gui_exception(re, constants.UNSUBSCRIBE_ERROR)
                raise
        # not registered, locally managed
        else:
            entcerts = EntitlementDirectory().list()
            for cert in entcerts:
                if self.pname_selected == cert.getProduct().getName():
                    cert.delete()
                    log.info("This machine is now unsubscribed from Product %s " % self.pname_selected)
             #FIXME:
            self.reload_gui()
            return
        # Force fetch all certs
        if not fetch_certificates():
            return
        self.reload_gui()

    def show_unregister_dialog(self, button):
        global UEP, consumer
        log.info("Unregister called in gui. Asking for confirmation")
        prompt = messageWindow.YesNoDialog(constants.CONFIRM_UNREGISTER)
        if not prompt.getrc():
            log.info("unregistrater not confirmed. cancelling")
            return
        log.info("Proceeding with un-registration: %s", consumer['uuid'])
        try:
            managerlib.unregister(UEP, consumer['uuid'], False)
            # TODO: probably not a great idea to use a global variable here.
            # Reset the global consumer variable.
            consumer = get_consumer()
            self.mainWin.emit(CONSUMER_SIGNAL)
        except Exception, e:
            log.error("Error unregistering system with entitlement platform.")
            handle_gui_exception(e, constants.UNREGISTER_ERROR,
                                 "Consumer may need to be manually cleaned up: %s" % consumer)



class RegisterScreen:
    """
      Registration Widget Screen
    """

    def __init__(self):
        dic = {"on_register_cancel_button_clicked": self.cancel,
               "on_register_button_clicked": self.onRegisterAction,
            }
        registration_xml.signal_autoconnect(dic)
        self.registerWin = registration_xml.get_widget("register_dialog")
        self.registerWin.connect("hide", self.cancel)
        self.registerWin.connect("delete_event", self.delete_event)
        self.initializeConsumerName()

        self.registerWin.run()

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
        self.uname = registration_xml.get_widget("account_login")
        self.passwd = registration_xml.get_widget("account_password")
        self.consumer_name = registration_xml.get_widget("consumer_name")

        global username, password, consumer, consumername, UEP
        username = self.uname.get_text()
        password = self.passwd.get_text()
        consumername = self.consumer_name.get_text()

        if not self.validate_consumername(consumername):
            return False

        facts = getFacts()
        if not self.validate_account():
            return False

        # for firstboot -t
        if testing:
            return True

        # TODO: Can't really hit this block anymore.
        # Unregister consumer if exists
        if ConsumerIdentity.exists():
            try:
                cid = consumer['uuid']
                UEP.unregisterConsumer(cid)
            except Exception, e:
                handle_gui_exception(e, None, "Unable to unregister existing user credentials.", False)

        failed_msg = _("Unable to register your system. \n Error: %s")
        try:
            admin_cp = connection.UEPConnection(username=username,
                    password=password)
            newAccount = admin_cp.registerConsumer(name=consumername,
                    facts=facts.get_facts())
            consumer = managerlib.persist_consumer_cert(newAccount)
            # reload CP instance with new ssl certs
            self._reload_cp_with_certs()
            if self.auto_subscribe():
                # try to auomatically bind products
                for pname, phash in managerlib.getInstalledProductHashMap().items():
                    try:
                        UEP.bindByProduct(consumer['uuid'], phash)
                        log.info("Automatically subscribe the machine to product %s " % pname)
                    except:
                        log.warning("Warning: Unable to auto subscribe the machine to %s" % pname)
                if not fetch_certificates():
                    return False

            self.close_window()

            self.emit_consumer_signal()

        except Exception, e:
           return handle_gui_exception(e, constants.REGISTER_ERROR)
        return True

    def emit_consumer_signal(self):
        self.registerWin.emit(CONSUMER_SIGNAL)

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

    # TODO: I don't think this is necessary
    def _reload_cp_with_certs(self):
        global UEP
        cert_file = ConsumerIdentity.certpath()
        key_file = ConsumerIdentity.keypath()
        UEP = connection.UEPConnection(cert_file=cert_file, key_file=key_file)


class RegistrationTokenScreen:
    """
     This screen handles reregistration and registration token activation
    """

    def __init__(self):
        dic = {
                "on_register_token_close_clicked" : self.finish,
                "on_change_account_button" : self.reRegisterAction,
                "on_facts_update_button_clicked" : self.factsUpdateAction,
                "on_submit_button_clicked" : self.submitToken,
                }
        self.setAccountMsg()
        regtoken_xml.signal_autoconnect(dic)
        self.regtokenWin = regtoken_xml.get_widget("register_token_dialog")
        self.regtokenWin.connect("hide", self.finish)
        self.regtokenWin.connect("delete_event", self.delete_event)

        self.regtokenWin.run()

    def show(self):
        self.regtokenWin.present()

    def delete_event(self, event, data=None):
        return self.finish()

    def finish(self, button=None):
        self.regtokenWin.hide()
        return True

    def reRegisterAction(self, button):
        show_register_screen()
        self.regtokenWin.hide()

    def factsUpdateAction(self, button):
        facts = getFacts()
        try:
            UEP.updateConsumerFacts(consumer['uuid'], facts.get_facts())
        except Exception, e:
            handle_gui_exception(e, "Could not update facts.\nError: %s" % e)

    def setAccountMsg(self):
        alabel1 = regtoken_xml.get_widget("account_label1")
        alabel1.set_label(_("\nThis system is registered with following consumer information"))
        alabel = regtoken_xml.get_widget("account_label2")
        alabel.set_label(_("<b>    ID:</b>       %s" % consumer["uuid"]))
        alabel = regtoken_xml.get_widget("account_label3")
        alabel.set_label(_("<b>  Name:</b>     %s" % consumer["consumer_name"]))

    def submitToken(self, button):
        rlabel = regtoken_xml.get_widget("regtoken_entry")
        reg_token = rlabel.get_text()
        elabel = regtoken_xml.get_widget("email_entry")
        email = elabel.get_text()
        if email == "":
            email = None
        try:
            UEP.bindByRegNumber(consumer['uuid'], reg_token, email)
            infoWindow(constants.SUBSCRIBE_REGTOKEN_SUCCESS % reg_token, self.regtokenWin)
        except Exception, e:
            handle_gui_exception(e, constants.SUBSCRIBE_REGTOKEN_ERROR % reg_token,
                                 "Could not subscribe registration token %s.\nError: %s" % (reg_token, e))


def show_busted_subs(busted_subs):
    if len(busted_subs):
        products = [x[0] for x in busted_subs]
        reasons = [linkify(x[1].msg) for x in busted_subs \
                if isinstance(x[1], connection.RestlibException)]
        msg = constants.SUBSCRIBE_ERROR % ', '.join(products)
        msg += "\n\n"
        msg += "\n".join(reasons)
        errorWindow(msg)


class AddSubscriptionScreen:
    """
     Add subscriptions Widget screen
    """

    def __init__(self):
        global UEP
        self.selected = {}
        self.csstatus = rhsm_xml.get_widget("select_status")
        self.total = 0
        self.consumer = consumer
        self.available_ent = 0
        self.subs_changed = False
        self.availableList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                           gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.matchedList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                           gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.compatList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                           gobject.TYPE_STRING, gobject.TYPE_STRING)

        self.populateSubscriptionLists()
        # machine is talking to candlepin, invoke listing scheme
        self.createMatchingSubscriptionsTreeview()
        self.createCompatibleSubscriptionsTreeview()
        if (cfg.get('rhsm', 'showIncompatiblePools') == '1'):
            self.createOtherSubscriptionsTreeview()
        else:
            notebook = rhsm_xml.get_widget("add_subscription_notebook")
            notebook.remove_page(1)

        dic = {"on_add_subscribe_close_clicked": self.cancel,
               "on_add_subscribe_button_clicked": self.onSubscribeAction,
            }
        rhsm_xml.signal_autoconnect(dic)
        self.addWin = rhsm_xml.get_widget("add_subscription_dialog")
        self.addWin.connect("delete_event", self.delete_event)
        #self.addWin.connect("hide", self.cancel)
        if not self.available_ent:
            infoWindow(constants.NO_SUBSCRIPTIONS_WARNING, self.addWin)
            self.addWin.hide()

    def populateSubscriptionLists(self):


        self.compat = []
        self.matched = []
        self.other = []
        try:
            compatible = managerlib.getAvailableEntitlements(UEP,
                    self.consumer['uuid'])
            self.matched = managerlib.getMatchedSubscriptions(compatible)
            matched_pids = []
            for product in self.matched:
                pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                self.matchedList.append(None, [False] + pdata)
                matched_pids.append(product['productId'])
                self.available_ent += 1

            for prod in compatible:
                if prod['productId'] not in matched_pids:
                    self.compat.append(prod)

            compatible_pids = []
            for product in self.compat:
                pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                self.compatList.append(None, [False] + pdata)
                compatible_pids.append(product['productId'])
                self.available_ent += 1

            all_subs = managerlib.getAvailableEntitlements(UEP, self.consumer['uuid'], all=True)
            self.other = []
            for prod in all_subs:
                if prod['productId'] not in compatible_pids + matched_pids:
                    self.other.append(prod)

            for product in self.other:
                pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                self.availableList.append(None, [False] + pdata)
                self.available_ent += 1
        except socket.error, e:
            handle_gui_exception(e, e.strerror)
        except Exception, e:
            log.error("Error populating available subscriptions from the server")
            log.error("Exception: %s" % e)

        # bz 646451: grey out apply button if there is nothing to subscribe to
        apply_button = rhsm_xml.get_widget("add_subscribe_apply_button")
        apply_button.set_sensitive(False)
        if self.compat or self.matched or self.other:
            apply_button.set_sensitive(True)

    # hook to forward
    def finish(self):
        self.addWin.hide()
        #self.addWin.destroy()
        gtk.main_iteration()
        return True

    # back?
    def cancel(self, button):
        self.addWin.hide()

    def delete_event(self, event, data=None):
        return self.finish()

    def show(self):
        global consumer
        if consumer['uuid'] != self.consumer['uuid']:
            log.info('consumer has changed \nfrom: %s \nto: %s',
                     self.consumer, consumer)
            self.consumer = consumer
            self.subs_changed = True

        if self.subs_changed:
            for item in [self.compatList, self.availableList, self.matchedList]:
                item.clear()
            self.populateSubscriptionLists()
            self.subs_changed = False
        self.addWin.present()

    def onSubscribeAction(self, button):
        slabel = rhsm_xml.get_widget("available_subscriptions_label")
        #consumer = get_consumer()
        subscribed_count = 0
        pwin = progress.Progress()
        pwin.setLabel(_("Performing Subscribe. Please wait."))
        busted_subs = []
        count = 0

        pwin.setProgress(count, len(self.selected.items()))

        for pool, state in self.selected.items():
            # state = (bool, iter)
            if state[0]:
                try:
                    ent_ret = UEP.bindByEntitlementPool(consumer['uuid'], pool)

                    my_model = state[3]

                    # unselect the row
                    my_model.set_value(state[2], 0, False)
                    self.selected[pool] = (False, state[1], state[2])

                    subscribed_count += 1
                except Exception, e:
                    # Subscription failed, continue with rest
                    log.error("Failed to subscribe to product %s Error: %s" % (state[1], e))
                    log.exception(e)
                    busted_subs.append((state[1], e))
                    continue
            count += 1
            pwin.setProgress(count, len(self.selected.items()))

        show_busted_subs(busted_subs)

        # Signal to refresh the Add Subscriptions page on next show:
        self.subs_changed = True

        # Force fetch all certs
        if not fetch_certificates():
            pwin.hide()
            return

        pwin.hide()
        self.addWin.hide()

    def createSubscriptionsTreeview(self, treeview, subscriptions, toggle_callback):
        """
        populate subscriptions compatible with your system facts
        """
        treeview.set_model(subscriptions)

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', toggle_callback, subscriptions)

        column = gtk.TreeViewColumn(_(''), cell)
        column.add_attribute(cell, "active", 0)
        treeview.append_column(column)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        cell.set_fixed_size(250, -1)
        col.set_resizable(True)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        treeview.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(100)
        treeview.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        treeview.append_column(col)
        
        subscriptions.set_sort_column_id(1, gtk.SORT_ASCENDING)
        
        
    def createMatchingSubscriptionsTreeview(self):
        self.match_tv = rhsm_xml.get_widget("treeview_matching")
        self.createSubscriptionsTreeview(self.match_tv,
                                           self.matchedList,
                                           self.col_matched_selected)


    def createCompatibleSubscriptionsTreeview(self):
        self.compatible_tv = rhsm_xml.get_widget("treeview_compatible")
        self.createSubscriptionsTreeview(self.compatible_tv,
                                           self.compatList, 
                                           self.col_compat_selected)

  
    def createOtherSubscriptionsTreeview(self):
        self.other_tv = rhsm_xml.get_widget("treeview_not_compatible")
        self.createSubscriptionsTreeview(self.other_tv,
                                           self.availableList,
                                           self.col_other_selected)


    def _update_tree_model(self, model, path, iter):
        model[path][0] = not model[path][0]
        self.model = model
        state = model.get_value(iter, 0)
        self.selected[model.get_value(iter, 4)] = (state, model.get_value(iter, 1), iter, model)
        if state:
            self.total += 1
        else:
            self.total -= 1
        if not self.total:
            self.csstatus.hide()
            return
        self.csstatus.show()
        self.csstatus.set_label(constants.SELECT_STATUS % self.total)

    def col_other_selected(self, cell, path, model):
        items, iter = self.other_tv.get_selection().get_selected()
        self._update_tree_model(model, path, iter)

    def col_matched_selected(self, cell, path, model):
        items, iter = self.match_tv.get_selection().get_selected()
        self._update_tree_model(model, path, iter)

    def col_compat_selected(self, cell, path, model):
        items, iter = self.compatible_tv.get_selection().get_selected()
        self._update_tree_model(model, path, iter)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)


class UpdateSubscriptionScreen:

    def __init__(self, product_selection, parentWindow):
        global UEP

        self.product_select = product_selection
        self.setHeadMsg()
        self.updatesList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.available_updates = 0
        try:
            products = managerlib.getAvailableEntitlements(UEP, consumer['uuid'])
            for product in products:
                if self.product_select in product.values():
                    # Only list selected product's pools
                    pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                    self.updatesList.append(None, [False] + pdata)
                    self.available_updates += 1
        except:
            pass

        #if no updates are available, just return. no point in creating update window.
        if not self.available_updates:
            infoWindow(constants.NO_UPDATES_WARNING, parentWindow)
            return

        self.populateUpdatesDialog()
        dic = {"on_update_subscriptions_close_clicked": self.cancel,
               "on_update_subscriptions_button_clicked": self.onSubscribeAction,
            }
        rhsm_xml.signal_autoconnect(dic)
        self.updateWin = rhsm_xml.get_widget("update_subscriptions_dialog")
        self.updateWin.connect("hide", self.cancel)
        self.updateWin.connect("delete_event", self.delete_event)
        self.updateWin.show_all()

    def cancel(self, button=None):
        self.updateWin.destroy()
        gtk.main_iteration()
        return True

    def delete_event(self, event, data=None):
        return self.cancel()

    def setHeadMsg(self):
        hlabel = rhsm_xml.get_widget("available_subscriptions_label")
        hlabel.set_label(_("<b>Available Subscriptions for %s:</b>") % self.product_select)

    def populateUpdatesDialog(self):
        self.tv_products = rhsm_xml.get_widget("subscriptions_update_treeview")
        self.tv_products.set_model(self.updatesList)

        cell = gtk.CellRendererToggle()
        cell.connect('toggled', self.col_update_selected, self.updatesList)

        column = gtk.TreeViewColumn(_(' '), cell)
        column.add_attribute(cell, "active", 0)
        self.tv_products.append_column(column)

        col = gtk.TreeViewColumn(_("Product"), gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        self.tv_products.append_column(col)

        self.updatesList.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def col_update_selected(self, cell, path, model):
        self.selected = {}
        items, iter = self.tv_products.get_selection().get_selected()
        #for col in range(model.get_n_columns()+1):
        for col in range(self.available_updates):
            if str(path) == str(col):
                model[path][0] = not model[path][0]
            else:
                model[col][0] = False
        self.model = model
        self.selected[model.get_value(iter, 4)] = (model.get_value(iter, 0), model.get_value(iter, 1), iter)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)

    def onSubscribeAction(self, button):
        subscribed_count = 0
        my_model = self.tv_products.get_model()
        busted_subs = []
        for pool, state in self.selected.items():
            # state = (bool, iter)
            if state[0]:
                try:
                    ent_ret = UEP.bindByEntitlementPool(consumer['uuid'], pool)
                    entitled_data = ent_ret[0]['pool']
                    updated_count = str(int(entitled_data['quantity']) - int(entitled_data['consumed']))
                    my_model.set_value(state[-1], 2, updated_count)
                    subscribed_count += 1
                except Exception, e:
                    # Subscription failed, continue with rest
                    log.error("Failed to subscribe to product %s Error: %s" % (state[1], e))
                    busted_subs.append((state[1], e))
                    continue

        show_busted_subs(busted_subs)

        # Force fetch all certs
        if not fetch_certificates():
            return
        if subscribed_count:
            slabel.set_label(constants.SUBSCRIBE_SUCCSSFUL % subscribed_count)
            self.updateWin.hide()
            # refresh main window
        else:
            slabel.set_label(constants.ATLEAST_ONE_SELECTION)
        self.reload_gui()

class ImportCertificate:

    """
     Import an Entitlement Certificate Widget screen
    """

    def __init__(self):
        self.add_vbox = rhsm_xml.get_widget("import_vbox")

        dic = {"on_import_cancel_button_clicked": self.cancel,
               "on_certificate_import_button_clicked": self.importCertificate,
            }
        rhsm_xml.signal_autoconnect(dic)
        self.importWin = rhsm_xml.get_widget("entitlement_import_dialog")
        self.importWin.connect("hide", self.cancel)
        self.importWin.connect("delete_event", self.delete_event)
        self.importWin.show_all()

    def cancel(self, button=None):
        self.importWin.hide()
#        self.importWin.destroy()
        gtk.main_iteration()
        return True

    def show(self):
        self.importWin.present()

    def delete_event(self, event, data=None):
        return self.cancel()

    def importCertificate(self, button):
        fileChooser = rhsm_xml.get_widget("certificate_chooser_button")
        src_cert_file = fileChooser.get_filename()
        if src_cert_file is None:
            errorWindow(_("You must select a certificate."))
            return False

        try:
            data = open(src_cert_file).read()
            x509 = load_certificate(FILETYPE_PEM, data)
        except:
            errorWindow(_("%s is not a valid certificate file. Please upload a valid certificate." %
                          os.path.basename(src_cert_file)))
            return False

        if not os.access(ENT_CONFIG_DIR, os.R_OK):
            os.mkdir(ENT_CONFIG_DIR)

        dest_file_path = os.path.join(ENT_CONFIG_DIR, os.path.basename(src_cert_file))
        #if not os.path.exists(dest_file_path):
        shutil.copy(src_cert_file, dest_file_path)
 #       print dest_file_path
        self.importWin.hide()
#        reload()


def unexpectedError(message, exc_info=None):
    message = message + "\n" + constants.UNEXPECTED_ERROR
    errorWindow(message)
    if exc_info:
        (etype, value, stack_trace) = exc_info


def errorWindow(message):
    messageWindow.ErrorDialog(messageWindow.wrap_text(message))


def infoWindow(message, parent):
    messageWindow.infoDialog(messageWindow.wrap_text(message), parent)


def setArrowCursor():
    pass


def setBusyCursor():
    pass


def reload():
    global gui
    gui.refresh()
#    gtk.main_quit()
#    gui = None
    main()


def linkify(msg):
    """
    Parse a string for any urls and wrap them in a hrefs, for use in a
    gtklabel.
    """
    # lazy regex; should be good enough.
    url_regex = re.compile("https?://\S*")

    def add_markup(mo):
        url = mo.group(0)
        return '<a href="%s">%s</a>' % (url, url)

    return url_regex.sub(add_markup, msg)


def main():
    global gui
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if os.geteuid() != 0:
        #rootWarning()
        sys.exit(1)

    managerlib.check_identity_cert_perms()

    try:
        gui = ManageSubscriptionPage()
        gtk.main()
    except Exception, e:
        raise
        unexpectedError(e.message)


if __name__ == "__main__":
    main()
