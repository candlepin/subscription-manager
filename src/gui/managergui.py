#!/usr/bin/python
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
import sys
import shutil
sys.path.append('/usr/share/rhsm')

import gtk
import gtk.glade
import gobject
import signal

import messageWindow
import hwprobe
import managerlib
import connection
import config

from certlib import EntitlementDirectory, ProductDirectory, ConsumerIdentity, CertLib
import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

gladexml = "/usr/share/rhsm/gui/data/standaloneH.glade"

cfg = config.initConfig()

UEP = connection.UEPConnection(cfg['hostname'] or 'localhost')
certlib = CertLib()
ENT_CONFIG_DIR="/etc/pki/entitlement/product/"


def get_consumer():
    if not ConsumerIdentity.exists():
        return {}
    consumer = ConsumerIdentity.read()
    consumer_info = {"consumer_name" : consumer.getConsumerName(),
                     "uuid" : consumer.getConsumerId(),
                     "user_account"  : consumer.getUser()
                    }
    return consumer_info

consumer = get_consumer()

class ManageSubscriptionPage:
    """
     Main subscription Manager Window
    """
    def __init__(self):
        self.subsxml = gtk.glade.XML(gladexml, "dialog_updates", domain="subscription-manager")
        self.vbox = \
                        self.subsxml.get_widget("dialog-vbox1")
        self.pname_selected = None
        self.populateProductDialog()
        self.updateMessage()
        dic = { "on_button_close_clicked" : gtk.main_quit,
                "account_settings_clicked_cb" : self.loadAccountSettings,
                "on_button_add1_clicked" : self.addSubButtonAction,
                "on_button_update1_clicked" : self.updateSubButtonAction,
                "on_button_unsubscribe1_clicked" : self.onUnsubscribeAction,
            }
        self.subsxml.signal_autoconnect(dic)
        self.mainWin = self.subsxml.get_widget("dialog_updates")
        self.mainWin.connect("delete-event", gtk.main_quit)
        self.mainWin.connect("hide", gtk.main_quit)

        self.mainWin.show_all()

    def loadAccountSettings(self, button):
        print consumer
        if consumer.has_key('uuid'):
            RegistrationTokenScreen()
        else:
            RegisterScreen() 
        return True

    def reviewSubscriptionPagePrepare(self):
        entdir = EntitlementDirectory()
        self.vbox.show_all()

    def addSubButtonAction(self, button):
        AddSubscriptionScreen()

    def updateSubButtonAction(self, button):
        if self.pname_selected:
            UpdateSubscriptionScreen(self.pname_selected)

    def populateProductDialog(self):
        state_icon_map = {"Expired" : gtk.STOCK_DIALOG_WARNING,
                          "Not Subscribed" : gtk.STOCK_DIALOG_QUESTION,
                          "Subscribed" : gtk.STOCK_APPLY, }
        self.tv_products =  self.subsxml.get_widget("treeview_updates")
        self.productList = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.warn_count = 0
        for product in managerlib.getInstalledProductStatus():
            markup_status = product[1]
            if product[1] in ["Expired", "Not Subscribed"]:
                self.warn_count += 1
                markup_status = '<span foreground="red"><b>%s</b></span>' % product[1]
            self.status_icon = self.tv_products.render_icon(state_icon_map[product[1]], size=gtk.ICON_SIZE_MENU)
            self.productList.append((self.status_icon, product[0], markup_status, product[2]))
        self.tv_products.set_model(self.productList)

        #self.tv_products.set_rules_hint(True)

        col = gtk.TreeViewColumn('')
        col.set_spacing(6)
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        cell.set_fixed_size(-1, 35)
        col.set_attributes(cell, pixbuf=0)
        self.tv_products.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Product"), cell, text=1)
        col.set_sort_column_id(1)
        col.set_spacing(6)
        cell.set_fixed_size(-1, 35)
        self.tv_products.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Subscription Status"), cell, markup=2)
        col.set_sort_column_id(2)
        col.set_spacing(6)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=3)
        col.set_sort_column_id(3)
        col.set_spacing(6)
        self.tv_products.append_column(col)

        #self.productList.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.selection = self.tv_products.get_selection()
        self.selection.connect('changed', self.on_selection)

    def on_selection(self, selection):
        items,iter = selection.get_selected()
        self.pname_selected = items.get_value(iter,1)
        desc = managerlib.getProductDescription(self.pname_selected)
        pdetails = self.subsxml.get_widget("textview_details")
        pdetails.get_buffer().set_text(desc)
        pdetails.set_cursor_visible(False)
        pdetails.show()

    def updateMessage(self):
        self.sumlabel = self.subsxml.get_widget("summaryLabel1")
        if self.warn_count:
            self.sumlabel.set_label(_("<b>\n %s products or subscriptions need your attention.\n\n</b>Add or Update subscriptions for products you are using.\n" % self.warn_count))
        else:
            self.sumlabel.set_label(_("Add or Update subscriptions for products you are using."))

    def onUnsubscribeAction(self, button):
        print self.pname_selected
        try:
            ent_list = UEP.getEntitlementList(consumer['uuid'])
            entId = None
            for ent in ent_list:
                print ent['entitlement']['pool']['productId']
                if self.pname_selected == ent['entitlement']['pool']['productId']:
                    entId = ent['entitlement']['id']
            if entId:
                print UEP.unBindByEntitlementId(consumer['uuid'], entId)
                # Force fetch all certs
                certlib.update()
        except:
            # be gentle for now
            raise #pass

class RegisterScreen:
    """
      Registration Widget Screen
    """
    def __init__(self):
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

    def onRegisterAction(self, button):
        self.uname = self.registerxml.get_widget("account_login")
        self.passwd = self.registerxml.get_widget("account_password")

        global username, password, consumer
        username = self.uname.get_text()
        password = self.passwd.get_text()

        # validate / check user name
        if self.uname.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a login."))
            self.uname.grab_focus()

        if self.passwd.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a password."))
            self.passwd.grab_focus()
        newAccount = UEP.registerConsumer(username, password, self._get_register_info())
        consumer = managerlib.persist_consumer_cert(newAccount)
        self.registerWin.hide()

    def _get_register_info(self):
        stype = {'label':'system'}
        product = {"id":"1","label":"RHEL AP","name":"rhel"}
        facts = hwprobe.Hardware().getAll()
        entrys = []
        for fact_key in facts.keys():
            entry_facts = {}
            entry_facts['key'] = fact_key
            entry_facts['value'] = facts[fact_key]
            entrys.append(entry_facts)

        params = { "consumer" : {
                "type":stype,
                "name":'admin',
                "facts":{'metadata': 
                             {"entry":entrys}
                        }
                 }
              }
        return params

class RegistrationTokenScreen:
    """
     This screen handles reregistration and registration token activation
    """
    def __init__(self):
        self.regtokenxml = gtk.glade.XML(gladexml, "register_token_dialog", domain="subscription-manager")
        dic = { "on_close_clicked" : self.finish, 
                "on_change_account_button" : self.reRegisterAction,
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

    def setAccountMsg(self):
        euser = "admin" #TODO:get this from identity cert
        alabel = self.regtokenxml.get_widget("account_label")
        alabel.set_label(_("This system is registered with the account <b>%s</b>" % euser))

    def submitToken(self, button):
        rlabel = self.regtokenxml.get_widget("regtoken_entry")
        reg_token = rlabel.get_text()
        #consumer = get_consumer()
        UEP.bindByRegNumber(consumer['uuid'], reg_token)

class AddSubscriptionScreen:
    """
     Add subscriptions Widget screen
    """
    def __init__(self):
        self.selected = {}
        #self.addxml = gtk.glade.XML(gladexml, "add_dialog", domain="subscription-manager")
        self.addxml = gtk.glade.XML(gladexml, "dialog1_add", domain="subscription-manager")
        self.add_vbox = \
                        self.addxml.get_widget("add-dialog-vbox1")
        self.consumer = consumer #get_consumer()
        available_ent = 0
        self.availableList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        try:
            for product in managerlib.getAvailableEntitlements(UEP, self.consumer['uuid']):
                self.availableList.append(None, [False] + product.values())
                available_ent += 1
        except:
            pass
        if available_ent and consumer['uuid']:
            self.populateAvailableList()

            dic = { "on_close_clicked" : self.cancel,
                    "on_import_cert_button_clicked"   : self.onImportPrepare,
                    "on_add_subscribe_button_clicked"   : self.onSubscribeAction,
                }
            self.addxml.signal_autoconnect(dic)
            #self.addWin = self.addxml.get_widget("add_dialog")
            self.addWin = self.addxml.get_widget("dialog1_add")
            self.addWin.connect("hide", self.cancel)
            #self.addWin.set_decorated(0) 
            self.addWin.show_all()
        else:
            ImportCertificate()

    def finish(self):
        self.addWin.hide()

    def cancel(self, button):
        self.addWin.hide()

    def onImportPrepare(self, button):
        self.addWin.hide()
        ImportCertificate()

    def onSubscribeAction(self, button):
        slabel = self.addxml.get_widget("label_status")
        #consumer = get_consumer()
        subscribed_count = 0
        my_model = self.tv_products.get_model()
        for product, state in self.selected.items():
            # state = (bool, iter)
            if state[0]:
                try:
                    entitled_data = UEP.bindByProduct(consumer['uuid'], product)['entitlement']['pool']
                    updated_count = str(int(entitled_data['quantity']) - int(entitled_data['consumed']))
                    my_model.set_value(state[-1], 3, updated_count)
                    subscribed_count+=1
                except:
                    # Subscription failed, continue with rest
                    continue
        # Force fetch all certs
        certlib.update()
        if len(self.selected.items()):
            slabel.set_label(_("<i><b>Successfully consumed %s subscription(s)</b></i>" % subscribed_count))
        else:
            slabel.set_label(_("<i><b>Please select atleast one subscription to apply</b></i>"))

    def populateAvailableList(self):
        #self.tv_products =  self.addxml.get_widget("treeview_available")
        self.tv_products =  self.addxml.get_widget("treeview_available1")
        self.tv_products.set_model(self.availableList)

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.col_selected, self.availableList)

        column = gtk.TreeViewColumn(_('Select'), cell)
        column.add_attribute(cell, "active", 0)
        self.tv_products.append_column(column)

        col = gtk.TreeViewColumn(_("Product"), gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=3)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=2)
        col.set_sort_column_id(3)
        self.tv_products.append_column(col)

        self.availableList.set_sort_column_id(1, gtk.SORT_ASCENDING) 

    def col_selected(self, cell, path, model):
        items, iter = self.tv_products.get_selection().get_selected()
        model[path][0] = not model[path][0]
        print "Toggle '%s' to: %s" % (model[path][1], model[path][0])
        self.model = model
        self.selected[model.get_value(iter, 1)] = (model.get_value(iter, 0), iter)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)


class UpdateSubscriptionScreen:
    def __init__(self, product_selection):
        #self.updatexml = gtk.glade.XML(gladexml, "update_dialog", domain="subscription-manager")
        self.updatexml = gtk.glade.XML(gladexml, "dialog1_updates", domain="subscription-manager")
        self.product_select = product_selection
        self.selected = {}
        self.setHeadMsg()
        self.updatesList = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.available_updates = 0
        try:
            for product in managerlib.getAvailableEntitlements(UEP, consumer['uuid']):
                if self.product_select in product.values():
                    # Only list selected product's pools
                    self.updatesList.append(None, [False] + product.values())
                    self.available_updates+= 1
        except:
            pass

        if self.available_updates and consumer['uuid']:
            self.populateUpdatesDialog()
            dic = { "on_close_clicked" : self.cancel,
                    "on_import_cert_button_clicked" : self.onImportPrepare,
                    "on_update_subscribe_button_clicked"   : self.onSubscribeAction,
                }
            self.updatexml.signal_autoconnect(dic)
            #self.updateWin = self.updatexml.get_widget("update_dialog")
            self.updateWin = self.updatexml.get_widget("dialog1_updates")
            self.updateWin.connect("hide", self.cancel)
            self.updateWin.show_all()
        else:
            ImportCertificate()
            

    def cancel(self, button=None):
        self.updateWin.hide()

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
        cell.set_property('activatable', True)
        cell.connect('toggled', self.col_update_selected, self.updatesList)

        column = gtk.TreeViewColumn(_('Select'), cell)
        column.add_attribute(cell, "active", 0)
        self.tv_products.append_column(column)

        col = gtk.TreeViewColumn(_("Product"), gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=3)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=2)
        col.set_sort_column_id(3)
        self.tv_products.append_column(col)

        self.updatesList.set_sort_column_id(1, gtk.SORT_ASCENDING)

    def col_update_selected(self, cell, path, model):
        items, iter = self.tv_products.get_selection().get_selected()
        model[path][0] = not model[path][0]
        print "Toggle '%s' to: %s" % (model[path][1], model[path][0])
        self.model = model
        self.selected[model.get_value(iter, 1)] = (model.get_value(iter, 0), iter)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)

    def onSubscribeAction(self, button):
        slabel = self.updatexml.get_widget("label_status_update")
        subscribed_count = 0
        my_model = self.tv_products.get_model()
        for product, state in self.selected.items():
            # state = (bool, iter)
            if state[0]:
                try:
                    entitled_data = UEP.bindByProduct(consumer['uuid'], product)['entitlement']['pool']
                    updated_count = str(int(entitled_data['quantity']) - int(entitled_data['consumed']))
                    my_model.set_value(state[-1], 3, updated_count)
                    subscribed_count+=1
                except:
                    # Subscription failed, continue with rest
                    continue
        # Force fetch all certs
        certlib.update()
        if len(self.selected.items()):
            slabel.set_label(_("<i><b>Successfully consumed %s subscription(s)</b></i>" % subscribed_count))
        else:
            slabel.set_label(_("<i><b>Please select atleast one subscription to apply</b></i>"))

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

    def importCertificate(self, button):
        fileChooser = self.importxml.get_widget("certificateChooserButton")
        src_cert_file = fileChooser.get_filename()
        if src_cert_file is None:
            errorWindow(_("You must select a certificate."))
            return False

        if not os.access(ENT_CONFIG_DIR, os.R_OK):
            os.mkdir(ENT_CONFIG_DIR)

        dest_file_path = os.path.join(ENT_CONFIG_DIR, os.path.basename(src_cert_file))
        if not os.path.exists(dest_file_path):
            shutil.copy(src_cert_file, dest_file_path)
        print dest_file_path
        self.importWin.hide()

def unexpectedError(message, exc_info=None):
    message = message + "\n" + (_("This error shouldn't have happened. If you'd "
                                 "like to help us improve this program, please "
                                 "file a bug at bugzilla.redhat.com. Including "
                                 "the relevant parts of would be very "
                                 "helpful. Thanks!") )
    errorWindow(message)
    if exc_info:
        (etype, value, stack_trace) = exc_info

def callAndFilterExceptions(function, allowedExceptions, 
        disallowedExceptionMessage, errorHandler=unexpectedError):
    assert callable(function)
    allowedExceptions.append(SystemExit)
    try:
        return function()
    except:
        (exceptionType, exception, stackTrace) = sys.exc_info()
        if exceptionType in allowedExceptions:
            raise
        else:
            errorHandler(disallowedExceptionMessage, 
                    (exceptionType, exception, stackTrace))

def errorWindow(message):
    messageWindow.ErrorDialog(messageWindow.wrap_text(message))

def setArrowCursor():
    """Dummy function that will be overidden by rhn_register's standalone gui
    and firstboot in different ways.
    
    """
    pass

def setBusyCursor():
    """Dummy function that will be overidden by rhn_register's standalone gui
    and firstboot in different ways.
    
    """
    pass


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if os.geteuid() != 0 :
        #rootWarning()
        sys.exit(1)

    gui = ManageSubscriptionPage()
    gtk.main()


if __name__ == "__main__":
    main()
