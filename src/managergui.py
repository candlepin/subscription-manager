import gtk
import gtk.glade
import signal
import os
import sys
import messageWindow
import hwprobe
import managerlib

import connection
from certlib import EntitlementDirectory, ProductDirectory
import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

gladegui = "../data/subsgui.glade"
gladexml = "../data/subsMgr.glade"
UEP = None
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
            print self.consumer
            self._write_consumer_cert(self.consumer['uuid'])
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
        # consumerid = ConsumerIdentity(consumerinfo['key'], \
        #                               consumerinfo['cert'])
        # consumerid.write()
        f = open("/etc/pki/consumer/cert.pem", "w")
        f.write(consumerinfo)
        f.close()

class ReviewSubscriptionPage:
    def __init__(self):
        self.reviewSubscriptionXml = gtk.glade.XML(gladexml, "dialog_updates", domain="subscription-manager")
        self.vbox = \
                        self.reviewSubscriptionXml.get_widget("dialog-vbox1")
        #self.gtkVBox1 = \
        #                self.reviewSubscriptionXml.get_widget("vbox1")
        #self.gtkHBox = \
        #                self.reviewSubscriptionXml.get_widget("hbox_header")
        #self.gtkVBox2 = \
        #                self.reviewSubscriptionXml.get_widget("vbox2")

    def reviewSubscriptionPagePrepare(self):
        entdir = EntitlementDirectory()
        self.vbox.show()
        vpaned_upd =  self.reviewSubscriptionXml.get_widget("vpaned_updates")
        print vpaned_upd.set_data
        vpaned_upd.set_data('a',1)
        #self.gtkHBox.show()
        #self.gtkVBox2.show()

    def reviewSubscriptionPageVbox(self):
        return self.vbox


class FinishPage:
    """The finish screen. This can show two different versions: successful and
    unsuccessful.
    """
    def __init__(self):
        self.failedFinishXml = gtk.glade.XML(gladexml,
                                                "failedFinishWindowVbox",
                                                domain="subscription-manager")
        self.successfulFinishXml = gtk.glade.XML(gladexml,
                                                "successfulFinishWindowVbox",
                                                domain="subscription-manager")
        self.finishContainerVbox = gtk.VBox()
        self.failedFinishVbox = \
                self.failedFinishXml.get_widget("failedFinishWindowVbox")
        self.successfulFinishVbox = \
                self.successfulFinishXml.get_widget("successfulFinishWindowVbox")
        self.finishContainerVbox.pack_start(self.failedFinishVbox)

    def finishPageVbox(self):
        return self.finishContainerVbox

    def finishPagePrepare(self):
        #containerChildren = self.finishContainerVbox.get_children()
        #assert len(containerChildren) == 1
        self.finishContainerVbox.remove(containerChildren[0])
        self.finishContainerVbox.pack_start(self.successfulFinishVbox)
        sys.exit(0)

class ConfirmQuitDialog:
    def __init__(self):
        self.xml = gtk.glade.XML(gladexml, "confirmQuitDialog", 
                                 domain="subscription-manager")
        self.dialog = self.xml.get_widget("confirmQuitDialog")
        
        self.rc = self.dialog.run()
        if self.rc == gtk.RESPONSE_NONE:
            self.rc = 0
        #if self.rc == 1:
        #    try:
        #        rhnreg.createSystemRegisterRemindFile()
        #    except (OSError, IOError), error:
        #        log.log_me("Reminder file couldn't be written. Details: %s" %
        #                   error)
        self.dialog.destroy()

class Gui(LoginPage, ReviewSubscriptionPage, FinishPage):
    def __init__(self):
        self.xml = gtk.glade.XML(gladegui, "mainWin", domain="subscription-manager") 
        self.xml.signal_autoconnect (
            {"onDruidCancel" : self.onDruidCancel,
              "onLoginPagePrepare" : self.onLoginPagePrepare,
              "onLoginPageNext" : self.onLoginPageNext,
              "onReviewSubscriptionPagePrepare" : self.onReviewSubscriptionPagePrepare,
              "onReviewSubscriptionPageNext" : self.onReviewSubscriptionPageNext,
              "onFinishPagePrepare" : self.onFinishPagePrepare,
              "onFinishPageFinish" : self.onFinishPageFinish,
        })

        LoginPage.__init__(self)
        ReviewSubscriptionPage.__init__(self)
        FinishPage.__init__(self)

        contents = self.loginPageVbox()
        container = self.xml.get_widget("loginPageVbox")
        container.pack_start(contents, True)

        contents = self.reviewSubscriptionPageVbox()
        container = self.xml.get_widget("reviewSubscriptionPageVbox")
        container.pack_start(contents) #, True)

        contents = self.finishPageVbox()
        container = self.xml.get_widget("finishPageVbox")
        container.pack_start(contents, True)

        self.druid = self.xml.get_widget("druid")
        self.mainWin = self.xml.get_widget("mainWin")
        self.mainWin.connect("delete-event", gtk.main_quit)
        self.mainWin.connect("hide", gtk.main_quit)

        self.loginPage = self.xml.get_widget("loginPage")
        self.reviewSubscriptionPage = self.xml.get_widget("dialog_updates")
        #self.finishPage = self.xml.get_widget("finishPage")

        def mySetBusyCursor():
            cursor = gtk.gdk.Cursor(gtk.gdk.WATCH)
            self.mainWin.window.set_cursor(cursor)
            while gtk.events_pending():
                gtk.main_iteration(False)
        def mySetArrowCursor():
            cursor = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
            self.mainWin.window.set_cursor(cursor)
            while gtk.events_pending():
                gtk.main_iteration(False)
        self.setBusyCursor = mySetBusyCursor
        self.setArrowCursor = mySetArrowCursor

        self.mainWin.show_all()

    def onDruidCancel(self, dummy):
        dialog = ConfirmQuitDialog()
        if dialog.rc == 1:
            self.druid.set_page(self.finishPage)
        else:
            return True

    def onLoginPagePrepare(self, page, dummy):
        self.loginPage.emit_stop_by_name("prepare")
        self.loginXml.get_widget("loginUserEntry").grab_focus()
        self.loginPagePrepare()

    def onLoginPageNext(self, page, dummy):
        """This must manually switch pages because another function calls it to
        advance the druid. It returns True to inform the druid of this.
        """
        ret = self.loginPageVerify()
        if ret:
            return ret

        ret = self.loginPageApply()
        if ret:
            return ret

        self.goToPageAfterLogin()
        return True

    def goToPageAfterLogin(self):
        self.druid.set_page(self.reviewSubscriptionPage)
        return True

    def onReviewSubscriptionPagePrepare(self, page, dummy):
        self.reviewSubscriptionPagePrepare()
        #self.druid.set_buttons_sensitive(False, True, False, False)
        #self.reviewSubscriptionPage.emit_stop_by_name("prepare")

    def onReviewSubscriptionPageNext(self, page, dummy):
        print "NNNNNNNNNNNNN"
        self.druid.set_page(self.finishPage)
        return True

    def onFinishPagePrepare(self, page=None, dummy=None):
        self.druid.set_buttons_sensitive(False, False, False, False)
        self.druid.set_show_finish(True)
        self.finishPage.emit_stop_by_name("prepare")
        self.druid.finish.set_label(_("_Finish"))
        title = _("Finish setting up software updates")
        #else:
        #    self.druid.finish.set_label(_("_Exit software update setup"))
        #    title = _("software updates setup unsuccessful")
        self.finishPagePrepare()
        self.mainWin.set_title(title)
        self.finishPage.set_title(title)

    def onFinishPageFinish(self, page, dummy=None):
        gtk.main_quit()

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

    gui = Gui()
    gtk.main()


if __name__ == "__main__":
    main()
