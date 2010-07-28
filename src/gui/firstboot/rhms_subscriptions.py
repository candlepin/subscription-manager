
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

class moduleClass(Module,managergui.ManageSubscriptionPage):
    def __init__(self):
        Module.__init__(self)
#        self.register_init()
        managergui.ManageSubscriptionPage.__init__(self)
        self.priority = 51#this value is relative to when you want to load the screen
                        # so check other modules before setting
        self.sidebarTitle = _("RHSM Subscriptions Management Screen")
        self.title = _("Subscription Manager Screen")

    def apply(self, interface, testing=False):
        print "interface", interface
        print "testing", testing
#        self.register(testing=testing)
        return RESULT_SUCCESS
        # Screen setup and loads the logic to run the screen

    def show_all(self):
        print "show_all"
        
    def close_window(self):
        pass

    def gui_reload(self):
        print "gui_reload"

    def createScreen(self):
        print "createScreen"
        self.vbox = gtk.VBox(spacing=10)
        print "gh2"
        self.subscription_dialog = self.subsxml.get_widget("dialog-vbox2")
#        self.register_dialog.set_parent(None)
        print "gh3", self.subscription_dialog
        self.subscription_dialog.reparent(self.vbox)
        self.vbox.pack_start(self.subscription_dialog)
        print "gh4"
#        self.register_dialog.show()
        # Invoke your module here
        # self.mymodule = MyModule()
        self.show_all()
        print "ffffffffffffff"

    def initializeUI(self):
        pass
        # prepare your screen
        # self.mymodule.initialize()

    def shouldAppear(self):
        return True
        # A boolean return based on condition whether to load this screen or Not

