
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

        self._destroy_widget('close_button')

    def apply(self, interface, testing=False):
        return RESULT_SUCCESS

    def show_all(self):
        print "show_all"

    def close_window(self):
        pass

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.subscription_dialog = managergui.rhsm_xml.get_widget(
                "main_vbox")
        self.subscription_dialog.reparent(self.vbox)

    def initializeUI(self):
        self.gui_reload()

    def shouldAppear(self):
        return True

    def _destroy_widget(self, widget_name):
        """
        Destroy a widget by name.

        See gtk.Widget.destroy()
        """
        widget = managergui.rhsm_xml.get_widget(widget_name)
        widget.destroy()
