
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


class moduleClass(Module, managergui.ManageSubscriptionPage):

    def __init__(self):
        Module.__init__(self)
        managergui.ManageSubscriptionPage.__init__(self)
        #this value is relative to when you want to load the screen
        # so check other modules before setting
        self.priority = 5
        self.sidebarTitle = _("RHSM Subscriptions Management")
        self.title = _("Subscription Manager")

    def apply(self, interface, testing=False):
        return RESULT_SUCCESS

    def show(self):
        # Override parent method to display separate window.
        pass

    def close_window(self):
        pass

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self._get_widget("main_vbox").reparent(self.vbox)

        self.gui_reload()

        # Clear out all the buttons on the bottom of the page
        self._get_widget('action_area').destroy()

    def initializeUI(self):
        pass

    def shouldAppear(self):
        return True

    def _get_widget(self, widget_name):
        """
        Returns a widget by name.
        """
        return managergui.rhsm_xml.get_widget(widget_name)
