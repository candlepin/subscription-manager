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

from certlib import EntitlementDirectory, ProductDirectory, ConsumerIdentity, CertLib
from OpenSSL.crypto import load_certificate, FILETYPE_PEM

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

from logutil import getLogger
log = getLogger(__name__)


prefix = os.path.dirname(__file__)
gladexml = os.path.join(prefix, "data/rhsm.glade")
subs_full = os.path.join(prefix, "data/icons/subsmgr-full.png")
subs_empty = os.path.join(prefix, "data/icons/subsmgr-empty.png")


cfg = config.initConfig()
UEP = None


if ConsumerIdentity.exists():
    cert_file = ConsumerIdentity.certpath()
    key_file = ConsumerIdentity.keypath()
    UEP = connection.UEPConnection(host=cfg['hostname'] or "localhost", ssl_port=cfg['port'], handler="/candlepin", cert_file=cert_file, key_file=key_file)

certlib = CertLib()
ENT_CONFIG_DIR="/etc/pki/entitlement/product/"


def get_consumer():
    if not ConsumerIdentity.exists():
        return {}
    consumer = ConsumerIdentity.read()
    consumer_info = {"consumer_name" : consumer.getConsumerName(),
                     "uuid" : consumer.getConsumerId()
                    }
    return consumer_info

consumer = get_consumer()

def fetch_certificates():
    # Force fetch all certs
    try:
        certlib.update()
    except Exception, e:
        log.error("Certificate sync failed")
        log.error(e)
        return False
    return True


class ManageSubscriptionPage:
    """
     Main subscription Manager Window
    """
    def __init__(self):
        self.subsxml = gtk.glade.XML(gladexml, "dialog_updates", domain="subscription-manager")
        self.vbox = \
                        self.subsxml.get_widget("dialog-vbox1")
        self.pname_selected = None
        self.pselect_status = None
        self.psubs_selected = None
        self.populateProductDialog()
        self.setRegistrationStatus()
        self.updateMessage()
        dic = { "on_button_close_clicked" : gtk.main_quit,
                "account_settings_clicked_cb" : self.loadAccountSettings,
                "on_button_add1_clicked" : self.addSubButtonAction,
                "on_button_update1_clicked" : self.updateSubButtonAction,
                "on_button_unsubscribe1_clicked" : self.onUnsubscribeAction,
            }
        self.subsxml.signal_autoconnect(dic)
        self.setButtonState()
        self.mainWin = self.subsxml.get_widget("dialog_updates")
        self.mainWin.connect("delete-event", gtk.main_quit)
        self.mainWin.connect("hide", gtk.main_quit)

        self.mainWin.show_all()

    def loadAccountSettings(self, button):
        print consumer
        if consumer.has_key('uuid'):
            log.info("Machine already registered, loading the re-registration/registration token")
            RegistrationTokenScreen()
        else:
            log.info("loading registration..")
            RegisterScreen() 
        return True

    def refresh(self):
        self.mainWin.destroy()

    def reviewSubscriptionPagePrepare(self):
        entdir = EntitlementDirectory()
        self.vbox.show_all()

    def addSubButtonAction(self, button):
        AddSubscriptionScreen()

    def updateSubButtonAction(self, button):
        if self.pname_selected:
            log.info("Product %s selected for update" % self.pname_selected)
            UpdateSubscriptionScreen(self.pname_selected)

    def setButtonState(self, state=False):
        self.button_update =  self.subsxml.get_widget("button_update1")
        self.button_unsubscribe =  self.subsxml.get_widget("button_unsubscribe1")
        self.button_update.set_sensitive(state)
        self.button_unsubscribe.set_sensitive(state)


    def populateProductDialog(self):
        state_icon_map = {"Expired" : gtk.STOCK_DIALOG_WARNING,
                          "Not Subscribed" : gtk.STOCK_DIALOG_QUESTION,
                          "Subscribed" : gtk.STOCK_APPLY, 
                          "Not Installed" : gtk.STOCK_DIALOG_QUESTION}
        self.tv_products =  self.subsxml.get_widget("treeview_updates")
        self.productList = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                         gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.warn_count = 0
        for product in managerlib.getInstalledProductStatus():
            markup_status = product[1]
            if product[1] in ["Expired", "Not Subscribed", "Not Installed"]:
                self.warn_count += 1
                markup_status = '<span foreground="red"><b>%s</b></span>' % product[1]
            self.status_icon = self.tv_products.render_icon(state_icon_map[product[1]], size=gtk.ICON_SIZE_MENU)
            self.productList.append((self.status_icon, product[0], product[3], markup_status, product[2], product[4]))
        self.tv_products.set_model(self.productList)

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

    def on_selection(self, selection):
        items,iter = selection.get_selected()
        self.pname_selected = items.get_value(iter,1)
        self.psubs_selected = items.get_value(iter,2)
        self.pselect_status = items.get_value(iter,3)
        desc = managerlib.getProductDescription(self.pname_selected)
        pdetails = self.subsxml.get_widget("textview_details")
        pdetails.get_buffer().set_text(desc)
        pdetails.set_cursor_visible(False)
        pdetails.show()
        status = ''.join([x.split('>',1)[-1] for x in self.pselect_status.split('<')])
        if status == "Not Subscribed":
            self.setButtonState(state=False)
        else:
            self.setButtonState(state=True)

    def updateMessage(self):
        self.sumlabel = self.subsxml.get_widget("summaryLabel1")
        self.sm_icon  = self.subsxml.get_widget("sm_icon")
        if self.warn_count > 1:
            self.sumlabel.set_label(
                          constants.WARN_SUBSCRIPTIONS % self.warn_count)
            self.sm_icon.set_from_file(subs_empty)
        elif self.warn_count == 1:
            self.sumlabel.set_label(
                          constants.WARN_ONE_SUBSCRIPTION % self.warn_count)
            self.sm_icon.set_from_file(subs_empty)
        else:
            self.sumlabel.set_label(constants.COMPLIANT_STATUS)
            self.sm_icon.set_from_file(subs_full)

    def setRegistrationStatus(self):
        self.reg_label = self.subsxml.get_widget("reg_status")
        self.reg_button_label = self.subsxml.get_widget("account_settings")
        if ConsumerIdentity.exists():
            self.reg_label.set_label(constants.REG_REMOTE_STATUS % cfg['hostname'])
            self.reg_button_label.set_label(_("Modify Registration"))
        else:
            self.reg_label.set_label(constants.REG_LOCAL_STATUS)
            self.reg_button_label.set_label(_("Register System..."))
        

    def onUnsubscribeAction(self, button):
        global UEP
        if not self.psubs_selected:
            return
        log.info("Product %s selected for unsubscribe" % self.pname_selected)
        dlg = messageWindow.YesNoDialog(constants.CONFIRM_UNSUBSCRIBE % self.pname_selected, self.mainWin)
        if not dlg.getrc():
            return
        print self.psubs_selected
        if not UEP:
            entcerts = EntitlementDirectory().list()
            for cert in entcerts:
                if self.pname_selected == cert.getProduct().getName():
                    cert.delete()
                    log.info("This machine is now unsubscribed from Product %s " % self.pname_selected)
            reload()
            return
        try:
            UEP.unBindBySerialNumber(consumer['uuid'], self.psubs_selected)
            log.info("This machine is now unsubscribed from Product %s " \
                      % self.pname_selected)
        except connection.RestlibException, re:
            log.error(re)
            errorWindow(constants.UNSUBSCRIBE_ERROR)
        except Exception, e:
            # raise warning window
            log.error("Unable to perform unsubscribe due to the following exception \n Error: %s" % e)
            errorWindow(constants.UNSUBSCRIBE_ERROR)
            raise
        # Force fetch all certs
        if not fetch_certificates():
            return
        reload()

class RegisterScreen:
    """
      Registration Widget Screen
    """
    def __init__(self):
        global UEP
        UEP = connection.UEPConnection(cfg['hostname'] or 'localhost', ssl_port=cfg['port'])
        

        self.registerxml = gtk.glade.XML(gladexml, "register_dialog", domain="subscription-manager")
        dic = { "on_close_clicked" : self.cancel,
                "on_register_button_clicked" : self.onRegisterAction, 
            }
        self.registerxml.signal_autoconnect(dic)
        self.registerWin = self.registerxml.get_widget("register_dialog")
        self.registerWin.connect("hide", self.cancel)
        self.registerWin.show_all()

    def cancel(self, button):
        self.registerWin.hide()


    # callback needs the extra arg, so just a wrapper here
    def onRegisterAction(self, button):
        self.register()

    def register(self, testing=None):
        self.uname = self.registerxml.get_widget("account_login")
        self.passwd = self.registerxml.get_widget("account_password")
        self.consumer_name = self.registerxml.get_widget("consumer_name")

        global username, password, consumer, consumername
        username = self.uname.get_text()
        password = self.passwd.get_text()
        consumername = self.consumer_name.get_text()
        if consumername == None:
            consumername = username

        facts = getFacts()
        if not self.validate_account():
            return False

        # for firstboot -t
        if testing:
            return True

        # Unregister consumer if exists
        if ConsumerIdentity.exists():
            try:
                cid = consumer['uuid']
                UEP.unregisterConsumer(cid)
            except Exception, e:
                log.error("Unable to unregister existing user credentials.")
        failed_msg = "Unable to register your system. \n Error: %s"
        try:
            newAccount = UEP.registerConsumer(username, password, name=consumername,
                    facts=facts.get_facts())
            consumer = managerlib.persist_consumer_cert(newAccount)
            # reload cP instance with new ssl certs
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
                    return
            RegistrationTokenScreen()
            self.close_window()
#            reload()
        except connection.RestlibException, e:
            log.error(failed_msg % e.msg)
            errorWindow(constants.REGISTER_ERROR % linkify(e.msg))
            self.close_window()
        except Exception, e:
            log.error(failed_msg % e)
            errorWindow(constants.REGISTER_ERROR % e)
            self.close_window()

    def close_window(self):
        self.registerWin.hide()

    def auto_subscribe(self):
        self.autobind = self.registerxml.get_widget("auto_bind")
        return self.autobind.get_active()

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

    def _reload_cp_with_certs(self):
        cert_file = ConsumerIdentity.certpath()
        key_file = ConsumerIdentity.keypath()
        UEP = connection.UEPConnection(host=cfg['hostname'] or "localhost", ssl_port=cfg['port'], \
                                       handler="/candlepin", cert_file=cert_file, key_file=key_file)


class RegistrationTokenScreen:
    """
     This screen handles reregistration and registration token activation
    """
    def __init__(self):
        self.regtokenxml = gtk.glade.XML(gladexml, "register_token_dialog", domain="subscription-manager")
        dic = { "on_close_clicked" : self.finish, 
                "on_change_account_button" : self.reRegisterAction,
                "on_facts_update_button_clicked" : self.factsUpdateAction,
                "on_submit_button_clicked" : self.submitToken, }
        self.setAccountMsg()
        self.regtokenxml.signal_autoconnect(dic)
        self.regtokenWin = self.regtokenxml.get_widget("register_token_dialog")
        self.regtokenWin.connect("hide", self.finish)
        self.regtokenWin.show_all()

    def finish(self, button=None):
        self.regtokenWin.hide()

    def reRegisterAction(self, button):
        RegisterScreen()
        self.regtokenWin.hide()

    def factsUpdateAction(self, button):
        facts = getFacts()
        try:
            UEP.updateConsumerFacts(consumer['uuid'], facts.get_facts())
        except connection.RestlibException, e:
            log.error("Could not update system facts:  error %s" % ( e))
            errorWindow(linkify(e.msg))
        except Exception, e:
            log.error("Could not update system facts \nError: %s" % (e))
            errorWindow(linkify(e.msg))

    def setAccountMsg(self):
        alabel = self.regtokenxml.get_widget("account_label")
        alabel1 = self.regtokenxml.get_widget("account_label1")
        alabel1.set_label(_("\nThis system is registered with following consumer information"))
        alabel = self.regtokenxml.get_widget("account_label2")
        alabel.set_label(_("<b>    ID:</b>       %s" % consumer["uuid"]))
        alabel = self.regtokenxml.get_widget("account_label3")
        alabel.set_label(_("<b>  Name:</b>     %s" % consumer["consumer_name"]))        

    def submitToken(self, button):
        rlabel = self.regtokenxml.get_widget("regtoken_entry")
        reg_token = rlabel.get_text()
        elabel = self.regtokenxml.get_widget("email_entry")
        email = elabel.get_text()
        if email == "":
            email = None
        try:
            UEP.bindByRegNumber(consumer['uuid'], reg_token, email)
            infoWindow(constants.SUBSCRIBE_REGTOKEN_SUCCESS % reg_token, self.regtokenWin)
        except connection.RestlibException, e:
            log.error("Could not subscribe registration token %s error %s" % (reg_token, e))
            errorWindow(linkify(e.msg))
        except Exception, e:
            log.error("Could not subscribe registration token [%s] \nError: %s" % (reg_token, e))
            errorWindow(constants.SUBSCRIBE_REGTOKEN_ERROR % reg_token)

class AddSubscriptionScreen:
    """
     Add subscriptions Widget screen
    """
    def __init__(self):
        global UEP
        self.selected = {}
        self.addxml = gtk.glade.XML(gladexml, "dialog_add", domain="subscription-manager")
        self.csstatus = self.addxml.get_widget("select_status")
        self.total = 0
        self.consumer = consumer
        available_ent = 0
        if consumer.has_key('uuid'):
            self.availableList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                               gobject.TYPE_STRING, gobject.TYPE_STRING)
            self.matchedList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                               gobject.TYPE_STRING, gobject.TYPE_STRING)
            self.compatList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, \
                                               gobject.TYPE_STRING, gobject.TYPE_STRING)

            try:
                compatible, dlist = managerlib.getCompatibleSubscriptions(UEP, self.consumer['uuid']) 
                self.matched = managerlib.getMatchedSubscriptions(dlist) or []
                matched_pids = []
                for product in self.matched:
                    pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                    self.matchedList.append(None, [False] + pdata)
                    matched_pids.append(product['productId'])
                    available_ent += 1
                self.compat = []
                for prod in compatible:
                    if prod['productId'] not in matched_pids:
                        self.compat.append(prod)
                compatible_pids= []
                for product in self.compat:
                    pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                    self.compatList.append(None, [False] + pdata)
                    compatible_pids.append(product['productId'])
                    available_ent += 1
                all_subs = managerlib.getAllAvailableSubscriptions(UEP, self.consumer['uuid'])
                self.other = []
                for prod in all_subs:
                    if prod['productId'] not in compatible_pids + matched_pids:
                        self.other.append(prod)
                for product in self.other:
                    pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                    self.availableList.append(None, [False] + pdata)
                    available_ent += 1
            
            except:
                log.error("Error populating available subscriptions from the server")
            # machine is talking to candlepin, invoke listing scheme
            self.populateMatchingSubscriptions()
            self.populateCompatibleSubscriptions()
            if cfg['showIncompatiblePools']:
                self.populateOtherSubscriptions()
            else:
                notebook = self.addxml.get_widget("notebook1")
                notebook.remove_page(1)

            dic = { "on_close_clicked" : self.cancel,
                    "on_add_subscribe_button_clicked"   : self.onSubscribeAction,
                }
            self.addxml.signal_autoconnect(dic)
            self.addWin = self.addxml.get_widget("dialog_add")
            self.addWin.connect("hide", self.cancel)
            self.addWin.show_all()
            if not available_ent:
                infoWindow(constants.NO_SUBSCRIPTIONS_WARNING, self.addWin)
                self.addWin.hide()
        else:
            # no CP to talk, use local certs uploads
            ImportCertificate()

    def finish(self):
        self.addWin.hide()
        self.addWin.destroy()
        gtk.main_iteration()

    def cancel(self, button):
        self.addWin.destroy()
        gtk.main_iteration()

    def onImportPrepare(self, button):
        self.addWin.hide()
        ImportCertificate()

    def onSubscribeAction(self, button):
        slabel = self.addxml.get_widget("label_status1")
        #consumer = get_consumer()
        subscribed_count = 0
        #my_model = self.tv_products.get_model()
        #my_model = self.other_tv.get_model()
        my_model = self.match_tv.get_model()
        pwin = progress.Progress()
        pwin.setLabel(_("Performing Subscribe. Please wait."))
        busted_subs = []
        count = 0
        

        for pool, state in self.selected.items():
            print pool, state
            count += 1
            pwin.setProgress(count, len(self.selected.items()))
            # state = (bool, iter)
            if state[0]:
                try:
                    ent_ret = UEP.bindByEntitlementPool(consumer['uuid'], pool)
                    entitled_data = ent_ret[0]['pool']
                    updated_count = str(int(entitled_data['quantity']) - int(entitled_data['consumed']))
                    my_model.set_value(state[-1], 2, updated_count)
                    subscribed_count+=1
                except Exception, e:
                    raise
                    # Subscription failed, continue with rest
                    log.error("Failed to subscribe to product %s Error: %s" % (state[1], e))
                    busted_subs.append(state[1])
                    continue
        if len(busted_subs):
            errorWindow(constants.SUBSCRIBE_ERROR % ', '.join(busted_subs[:]))
        # Force fetch all certs
        if not fetch_certificates():
            return

        pwin.hide()
        self.addWin.hide()
        reload()
            
    def populateMatchingSubscriptions(self):
        """
        populate subscriptions matching currently installed products
        """
        self.match_tv =  self.addxml.get_widget("treeview_available2")
        self.match_tv.set_model(self.matchedList)

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.col_matched_selected, self.matchedList)

        column = gtk.TreeViewColumn(_(''), cell)
        column.add_attribute(cell, "active", 0)
        self.match_tv.append_column(column)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        cell.set_fixed_size(250, -1)
        col.set_resizable(True)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        self.match_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(100)
        self.match_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        self.match_tv.append_column(col)

        self.availableList.set_sort_column_id(1, gtk.SORT_ASCENDING)
    
    def populateCompatibleSubscriptions(self):
        """
        populate subscriptions compatible with your system facts
        """
        self.compatible_tv =  self.addxml.get_widget("treeview_available3")
        self.compatible_tv.set_model(self.compatList)

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.col_compat_selected, self.compatList)

        column = gtk.TreeViewColumn(_(''), cell)
        column.add_attribute(cell, "active", 0)
        self.compatible_tv.append_column(column)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        cell.set_fixed_size(250, -1)
        col.set_resizable(True)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        self.compatible_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(100)
        self.compatible_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        self.compatible_tv.append_column(col)

        self.availableList.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def populateOtherSubscriptions(self):
        """
        populate all available subscriptions
        """
        self.other_tv = self.addxml.get_widget("treeview_available4")
        self.other_tv.set_model(self.availableList)

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.col_other_selected, self.availableList)

        column = gtk.TreeViewColumn(_(''), cell)
        column.add_attribute(cell, "active", 0)
        self.other_tv.append_column(column)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        col.set_resizable(True)
        cell.set_fixed_size(250, -1)
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
        self.other_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        col.set_fixed_width(100)
        self.other_tv.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        self.other_tv.append_column(col)

        self.availableList.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def col_other_selected(self, cell, path, model):
        items, iter = self.other_tv.get_selection().get_selected()
        model[path][0] = not model[path][0]
        self.model = model
        state = model.get_value(iter, 0)
        self.selected[model.get_value(iter, 4)] = (state, model.get_value(iter, 1), iter)
        if state:
            self.total += 1
        else:
            self.total -= 1
        if not self.total:
            self.csstatus.hide()
            return
        self.csstatus.show()
        self.csstatus.set_label(constants.SELECT_STATUS % self.total)

    def col_matched_selected(self, cell, path, model):
        items, iter = self.match_tv.get_selection().get_selected()
        model[path][0] = not model[path][0]
        self.model = model
        state = model.get_value(iter, 0)
        self.selected[model.get_value(iter, 4)] = (state, model.get_value(iter, 1), iter)
        if state:
            self.total += 1
        else:
            self.total -= 1    
        if not self.total:
            self.csstatus.hide()
            return
        self.csstatus.show()
        self.csstatus.set_label(constants.SELECT_STATUS % self.total)

        print self.total
        
    def col_compat_selected(self, cell, path, model):
        items, iter = self.compatible_tv.get_selection().get_selected()
        model[path][0] = not model[path][0]
        self.model = model
        state = model.get_value(iter, 0)
        self.selected[model.get_value(iter, 4)] = (state, model.get_value(iter, 1), iter)
        if state:
            self.total += 1
        else:
            self.total -= 1
        if not self.total:
            self.csstatus.hide()
            return
        self.csstatus.show()
        self.csstatus.set_label(constants.SELECT_STATUS % self.total)
        
    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)


class UpdateSubscriptionScreen:
    def __init__(self, product_selection):
        global UEP
        #self.updatexml = gtk.glade.XML(gladexml, "update_dialog", domain="subscription-manager")
        self.updatexml = gtk.glade.XML(gladexml, "dialog1_updates", domain="subscription-manager")
        self.product_select = product_selection
        #self.selected = {}
        self.setHeadMsg()
        self.updatesList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.available_updates = 0
        try:
            products, dlist = managerlib.getAvailableEntitlements(UEP, consumer['uuid'])
            for product in products:
                if self.product_select in product.values():
                    # Only list selected product's pools
                    pdata = [product['productName'], product['quantity'], product['endDate'], product['id']]
                    self.updatesList.append(None, [False] + pdata)
                    self.available_updates+= 1
        except:
            pass

        if consumer.has_key('uuid'):
            self.populateUpdatesDialog()
            dic = { "on_close_clicked" : self.cancel,
                    #"on_import_cert_button_clicked" : self.onImportPrepare,
                    "on_update_subscribe_button_clicked"   : self.onSubscribeAction,
                }
            self.updatexml.signal_autoconnect(dic)
            #self.updateWin = self.updatexml.get_widget("update_dialog")
            self.updateWin = self.updatexml.get_widget("dialog1_updates")
            self.updateWin.connect("hide", self.cancel)
            self.updateWin.show_all()
            if not self.available_updates:
                infoWindow(constants.NO_UPDATES_WARNING, self.updateWin)
                self.updateWin.hide()
        else:
            ImportCertificate()
            

    def cancel(self, button=None):
        self.updateWin.destroy()
        gtk.main_iteration()

    def onImportPrepare(self, button):
        self.updateWin.hide()
        ImportCertificate()

    def setHeadMsg(self):
        hlabel = self.updatexml.get_widget("update-label2")
        hlabel.set_label(_("<b>Available Subscriptions for %s:</b>") % self.product_select)

    def populateUpdatesDialog(self):
        self.tv_products =  self.updatexml.get_widget("treeview_updates2")
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
        print "Toggle '%s' to: %s" % (model[path][1], model[path][0])
        self.model = model
        self.selected[model.get_value(iter, 4)] = (model.get_value(iter, 0), model.get_value(iter, 1), iter)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)

    def onSubscribeAction(self, button):
        slabel = self.updatexml.get_widget("label_status_update")
        subscribed_count = 0
        my_model = self.tv_products.get_model()
        for pool, state in self.selected.items():
            # state = (bool, iter)
            if state[0]:
                try:
                    ent_ret = UEP.bindByEntitlementPool(consumer['uuid'], pool)
                    entitled_data = ent_ret[0]['pool']
                    updated_count = str(int(entitled_data['quantity']) - int(entitled_data['consumed']))
                    my_model.set_value(state[-1], 2, updated_count)
                    subscribed_count+=1
                except Exception, e:
                    # Subscription failed, continue with rest
                    log.error("Failed to subscribe to product %s Error: %s" % (state[1], e))
                    errorWindow(constants.SUBSCRIBE_ERROR % state[1])
                    continue
        # Force fetch all certs
        if not fetch_certificates():
            return
        if subscribed_count:
            slabel.set_label(constants.SUBSCRIBE_SUCCSSFUL % subscribed_count)
            self.updateWin.hide()
            # refresh main window
            reload()
        else:
            slabel.set_label(constants.ATLEAST_ONE_SELECTION)

class ImportCertificate:
    """
     Import an Entitlement Certificate Widget screen
    """
    def __init__(self):
        #self.importxml = gtk.glade.XML(gladexml, "import_dialog", domain="subscription-manager")
        self.importxml = gtk.glade.XML(gladexml, "dialog1_import", domain="subscription-manager")
        self.add_vbox = \
                        self.importxml.get_widget("import_vbox")

        dic = { "on_close_import" : self.cancel,
                "on_import_cert_button2_clicked" : self.importCertificate,
            }
        self.importxml.signal_autoconnect(dic)
        #self.importWin = self.importxml.get_widget("import_dialog")
        self.importWin = self.importxml.get_widget("dialog1_import")
        self.importWin.connect("hide", self.cancel)
        #self.importWin.set_has_frame(True)
        self.importWin.show_all()

    def cancel(self, button=None):
      self.importWin.hide()
      self.importWin.destroy()
      gtk.main_iteration()

    def importCertificate(self, button):
        fileChooser = self.importxml.get_widget("certificateChooserButton")
        src_cert_file = fileChooser.get_filename()
        if src_cert_file is None:
            errorWindow(_("You must select a certificate."))
            return False

        try:
            data = open(src_cert_file).read()
            x509 = load_certificate(FILETYPE_PEM, data)
        except:
            errorWindow(_("%s is not a valid certificate file. Please upload a valid certificate." % os.path.basename(src_cert_file)))
            return False

        if not os.access(ENT_CONFIG_DIR, os.R_OK):
            os.mkdir(ENT_CONFIG_DIR)

        dest_file_path = os.path.join(ENT_CONFIG_DIR, os.path.basename(src_cert_file))
        #if not os.path.exists(dest_file_path):
        shutil.copy(src_cert_file, dest_file_path)
        print dest_file_path
        self.importWin.hide()
        reload()

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
    gtk.main_quit()
    gui = None
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

    if os.geteuid() != 0 :
        #rootWarning()
        sys.exit(1)
    try:
        gui = ManageSubscriptionPage()
        gtk.main()
    except Exception, e:
        unexpectedError(e.message)

if __name__ == "__main__":
    main()
