
import sys
import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("firstboot", x)

sys.path.append("/usr/share/rhsm")
from gui import managergui
from certlib import ConsumerIdentity


class moduleClass(Module, managergui.ChooseEntitlement):

    def __init__(self):
        Module.__init__(self)
        managergui.ChooseEntitlement.__init__(self)

        self.priority = 2
        # ugh, what a horrible label FIXME
        self.sidebarTitle = _("Entitlement Selection")
#        self.title = _("Entitlement Selection")
        self.title = _("RHMS Entitlement Selection")

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.choose_dialog = managergui.rhsm_xml.get_widget("entitlementChooseVbox")
        self.choose_dialog.reparent(self.vbox)


        # default to local
        self.local_button.set_active(True)

        # FIXME: need to see if we are in reconfig mode too
        if managergui.UEP and not ConsumerIdentity.exists():
            self.rhesus_button.set_sensitive(True)
            self.rhesus_button.set_active(True)

    def apply(self, interface, testing=False):
        if self.rhesus_button.get_active():
            interface.moveToPage(moduleTitle=_("Entitlement Platform Registration"))
            return RESULT_JUMP

        if self.local_button.get_active():
            interface.moveToPage(moduleTitle=_("Subscription Manager"))
            return RESULT_JUMP

        if self.rhn_button.get_active():
            interface.moveToPage(moduleTitle=_("Set Up Software Updates"))
            return RESULT_JUMP

        return RESULT_SUCCESS

    def initializeUI(self):
        pass

    def needsNetwork(self):
        return True

    def shouldAppear(self):
        return True
