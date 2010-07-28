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
        self.priority = 50    #this value is relative to when you want to load the screen
                              # so check other modules before setting
        self.sidebarTitle = _("RHSM Login Screen")
        self.title = _("Subscription Manager Screen")

    def register_init(self):
        managergui.UEP = managergui.connection.UEPConnection(  \
            managergui.cfg['hostname'] or 'localhost',         \
            ssl_port=managergui.cfg['port'])

    def apply(self, interface, testing=False):
        valid_registration = self.register(testing=testing)

        if valid_registration:
            return RESULT_SUCCESS
        else:
            return RESULT_FAILURE

    def close_window(self):
        pass

    def cancel(self, button):
        # Ignore this for now
        pass

    def createScreen(self):
        self.registerxml = gtk.glade.XML(managergui.gladexml, "register_dialog", domain="subscription-manager")

        self.vbox = gtk.VBox(spacing=10)
        self.register_dialog = self.registerxml.get_widget("dialog-vbox3")
        self.register_dialog.reparent(self.vbox)

        self._destroy_widget('register_button')
        self._destroy_widget('cancel_reg_button1')

    def initializeUI(self):
        pass

    def focus(self):
        # FIXME:  This is currently broken
        login_text = self.registerxml.get_widget("account_login")
        login_text.grab_focus()

    def _destroy_widget(self, widget_name):
        widget = self.registerxml.get_widget(widget_name)
        widget.destroy()

