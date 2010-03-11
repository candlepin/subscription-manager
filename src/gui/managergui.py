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
sys.path.append('/usr/share/rhsm')

import gtk
import gtk.glade
import gobject
import signal

import messageWindow
import hwprobe
import managerlib
import connection

from certlib import EntitlementDirectory, ProductDirectory, ConsumerIdentity
import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

gladexml = "/usr/share/rhsm/gui/data/standaloneH.glade"
UEP = connection.UEPConnection()
class LoginPage:
    def __init__(self):
        self.loginXml = gtk.glade.XML(gladexml,
                                      "initialLoginWindowVbox", domain="subscription-manager")
        self.loginXml.signal_autoconnect ({ 
              "onLoginUserEntryActivate" : self.loginPageAccountInfoActivate,
              "onLoginPasswordEntryActivate" : self.loginPageAccountInfoActivate,
              })
        instructionsLabel = self.loginXml.get_widget('instructionsLabel')
        self.loginPageHostedLabelText = instructionsLabel.get_label()
        print self.loginPageHostedLabelText
        self.cp = connection.UEPConnection()
        print self.cp

    def loginPagePrepare(self):
        instructionsLabel = self.loginXml.get_widget('instructionsLabel')
        forgotInfoHosted = self.loginXml.get_widget('forgotInfoHosted')
        tipIconHosted = self.loginXml.get_widget('tipIconHosted')
        instructionsLabel.set_label(self.loginPageHostedLabelText)
        forgotInfoHosted.show()
        tipIconHosted.show()

    def loginPageVbox(self):
        return self.loginXml.get_widget("initialLoginWindowVbox")

    def loginPageAccountInfoActivate(self, entry):
        passwordEntry = self.loginXml.get_widget("loginPasswordEntry")
        if entry == passwordEntry or len(passwordEntry.get_text()) > 0:
            if hasattr(self, "onLoginPageNext"):
                self.onLoginPageNext(None, None)
        else:
            passwordEntry.grab_focus()

    def loginPageVerify(self):
        self.loginPw = self.loginXml.get_widget("loginPasswordEntry")
        self.loginUname = self.loginXml.get_widget("loginUserEntry")

        global username, password
        username = self.loginUname.get_text()
        password = self.loginPw.get_text()

        global newAccount
        newAccount = False
        # validate / check user name
        if self.loginUname.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a login."))
            self.loginUname.grab_focus()
            return True

        if self.loginPw.get_text().strip() == "":
            setArrowCursor()
            errorWindow(_("You must enter a password."))
            self.loginPw.grab_focus()
            return True
        
        return False


    def loginPageApply(self):
        status = callAndFilterExceptions(
                self._loginPageApply,
                [],
                _("There was an error while logging in.")
        )
        if status is False:
            return False
        else:
            return True
    
    def _loginPageApply(self):
        try:
            setBusyCursor()
            self.consumer = self.cp.registerConsumer(\
                 self.loginUname.get_text(), self.loginPw.get_text(),
                 self._get_register_info())
            self._write_consumer_cert(self.consumer)
            # Try to Auto Subscribe users
            for product in managerlib.getInstalledProductStatus():
                print "Binding ", product[0]
                try:
                    self.cp.bindByProduct(self.consumer['uuid'], product[0])
                except:
                    pass
        except:
            raise
            setArrowCursor()
            errorWindow(_("There was problem logging in."))
            return True
        
        setArrowCursor()
        return False
    
    def _get_register_info(self):
        stype = {'label':'system'}
        product = {"id":"1","label":"RHEL AP","name":"rhel"}
        facts = hwprobe.Hardware().getAll()
        params = {
                "type":stype,
                "name":'admin',
                "facts":facts,
        }
        return params

    def _write_consumer_cert(self, consumerinfo):
        if not os.path.isdir("/etc/pki/consumer/"):
            os.mkdir("/etc/pki/consumer/")
        #TODO: this will a pki cert in future
        print consumerinfo
        consumerid = ConsumerIdentity(consumerinfo['idCert']['key'], \
                                      consumerinfo['idCert']['pem'])
        consumerid.write()
        f = open("/etc/pki/consumer/cert.uuid", "w")
        f.write(consumerinfo['uuid'])
        f.close()

class ManageSubscriptionPage:
    def __init__(self):
        self.subsxml = gtk.glade.XML(gladexml, "dialog_updates", domain="subscription-manager")
        self.vbox = \
                        self.subsxml.get_widget("dialog-vbox1")
        self.populateProductDialog()
        self.updateMessage()
        #self.reviewSubscriptionPagePrepare()
        dic = { "on_button_close_clicked" : gtk.main_quit,
                "account_settings_clicked_cb" : self.loadAccountSettings,
                "on_button_add1_clicked" : self.addSubButtonAction
            }
        self.subsxml.signal_autoconnect(dic)
        self.mainWin = self.subsxml.get_widget("dialog_updates")
        self.mainWin.connect("delete-event", gtk.main_quit)
        self.mainWin.connect("hide", gtk.main_quit)
        #self.mainWin.connect("on_button_add1_clicked", self.addSubButtonAction)

        self.mainWin.show_all()

    def loadAccountSettings(self, button):
        login_page = LoginPage()
        login_page.loginPagePrepare()
        return True

    def reviewSubscriptionPagePrepare(self):
        entdir = EntitlementDirectory()
        self.vbox.show_all()

    def addSubButtonAction(self, button):
        AddSubscriptionScreen()

    def populateProductDialog(self):
        self.productList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.warn_count = 0
        for product in managerlib.getInstalledProductStatus():
            self.productList.append(product)
            if product[1] in ["Expired", "Not Subscribed"]:
                self.warn_count += 1
        self.tv_products =  self.subsxml.get_widget("treeview_updates")
        self.tv_products.set_model(self.productList)

        self.tv_products.set_rules_hint(True)

        col = gtk.TreeViewColumn(_("Product"), gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Subscription Status"), gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=2)
        col.set_sort_column_id(2)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        self.productList.set_sort_column_id(0, gtk.SORT_ASCENDING)


    def provideCertificatePageApply(self):
        self._provideCertificatePageApply()

    def updateMessage(self):
        self.sumlabel = self.subsxml.get_widget("summaryLabel1")
        if self.warn_count:
            self.sumlabel.set_label(_("<b>%s products or subscriptions need your attention.\n\n</b>Add or Update subscriptions for products you are using.\n" % self.warn_count))
        else:
            self.sumlabel.set_label(_("Add or Update subscriptions for products you are using."))

    def _provideCertificatePageApply(self):
        """Does what the comment for provideCertificatePageApply says, but might 
        raise various exceptions.
        
        """
        try:
            fileChooser = self.subsxml.get_widget("button_import")
            certFile = fileChooser.get_filename()
            if certFile is None:
                pass 
        except:
            raise

    def reviewSubscriptionPageVbox(self):
        return self.vbox


class AddSubscriptionScreen:
    def __init__(self):
        self.addxml = gtk.glade.XML(gladexml, "add_dialog", domain="subscription-manager")
        self.add_vbox = \
                        self.addxml.get_widget("add-dialog-vbox2")
        self.populateAvailableList()

        dic = { "on_close_clicked" : self.cancel,
            }
        self.addxml.signal_autoconnect(dic)
        self.addWin = self.addxml.get_widget("add_dialog")
        #self.addWin.connect("delete-event", self.finish)
        self.addWin.connect("hide", self.cancel)
        #self.mainWin.connect("on_button_add1_clicked", self.addSubButtonAction)

        self.addWin.show_all()

    def finish(self):
        self.addWin.hide()

    def cancel(self, button):
        self.addWin.hide()

    def populateAvailableList(self):
        consumer = managerlib.check_registration()
        self.availableList = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        for product in managerlib.getAvailableEntitlements(UEP, consumer):
            self.availableList.append(product.values())
        self.tv_products =  self.addxml.get_widget("treeview_available")
        self.tv_products.set_model(self.availableList)


        column = gtk.TreeViewColumn(_(''))
        cell = gtk.CellRendererToggle()
        cell.connect('toggled', self.col_selected)
        column.pack_start(cell, True)
        column.set_attributes(cell, active=1)
        column.set_clickable(True)
        #hide toggle for separators
        column.set_cell_data_func(cell, self._cell_data_toggle_func)
        self.tv_products.append_column(column)

        col = gtk.TreeViewColumn(_("Product"), gtk.CellRendererText(), text=0)
        col.set_spacing(4)
        col.set_sort_column_id(1)
        col.set_clickable(True)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Available Slots"), gtk.CellRendererText(), text=2)
        col.set_spacing(4)
        col.set_sort_column_id(3)
        col.set_clickable(True)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)

        col = gtk.TreeViewColumn(_("Expires"), gtk.CellRendererText(), text=1)
        col.set_spacing(4)
        col.set_sort_column_id(2)
        col.set_clickable(True)
        col.set_sort_order(gtk.SORT_ASCENDING)
        self.tv_products.append_column(col)
        
        sel = self.tv_products.get_selection()
        sel.set_mode(gtk.SELECTION_SINGLE)
        self.availableList.set_sort_column_id(0, gtk.SORT_ASCENDING) 

    def col_selected(self, cell, path):
        pass

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter):
        renderer.set_property('visible', True)


class UpdateSubscriptionScreen:
    def __init__(self):
        pass

class RemoveSubscriptionScreen:
    def __init__(self):
        pass

class UploadCertificate:
    def __init__(self):
        pass


def unexpectedError(message, exc_info=None):
    #logFile = '/var/log/up2date'
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
