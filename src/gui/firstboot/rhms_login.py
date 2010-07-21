
import sys

import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module


import gettext
_ = lambda x: gettext.ldgettext("firstboot", x)
N_ = lambda x: x

sys.path.append("/usr/share/rhsm")
print sys.path
from gui import managergui

class moduleClass(Module,managergui.RegisterScreen):
    def __init__(self):
        Module.__init__(self)
        self.register_init()
#        managergui.RegisterScreen.__init__(self)
        self.priority = 50#this value is relative to when you want to load the screen
                        # so check other modules before setting
        self.sidebarTitle = _("RHSM Login Screen")
        self.title = _("Subscription Manager Screen")

    def register_init(self):
        UEP = managergui.connection.UEPConnection(managergui.cfg['hostname'] or 'localhost', ssl_port=managergui.cfg['port'])
        

        self.registerxml = gtk.glade.XML(managergui.gladexml, "register_dialog", domain="subscription-manager")
        dic = { "on_close_clicked" : self.cancel,
                "on_register_button_clicked" : self.onRegisterAction, 
            }
        self.registerxml.signal_autoconnect(dic)
#        print self.registerxml.get_widget("dialog-vbox3")
#        self.registerWin = self.registerxml.get_widget("register_dialog")
#        self.registerWin.connect("hide", self.cancel)
#        self.registerWin.show_all()

    def apply(self, interface, testing=False):
        self.register(testing=testing)
        return RESULT_SUCCESS
        # Screen setup and loads the logic to run the screen

    def close_window(self):
        pass

    def createScreen(self):
        print "createScreen"
        self.vbox = gtk.VBox(spacing=10)
        label = gtk.Label("This is a test label. Blippy. Foobar")
        label.set_line_wrap(True)
#        self.vbox.pack_start(label, expand=True, fill=True)
        print "gh2"
        self.register_dialog = self.registerxml.get_widget("dialog-vbox3")
        print "gh3"
#        self.register_dialog.set_parent(None)
        self.register_dialog.reparent(self.vbox)
        self.vbox.pack_start(self.register_dialog)
#        self.register_dialog.show()
        # Invoke your module here
        # self.mymodule = MyModule()

    def initializeUI(self):
        pass
        # prepare your screen
        # self.mymodule.initialize()

    def shouldAppear(self):
        return True
        # A boolean return based on condition whether to load this screen or Not

