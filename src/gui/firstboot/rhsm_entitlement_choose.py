
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

class moduleClass(Module):

    def __init__(self):
        Module.__init__(self)

        self.priority = 1.1
        # ugh, what a horrible label FIXME
        self.sidebarTitle = _("Entitlement Selection")
        self.title = _("RHSM Entitlement Selection")

        self.vbox = managergui.rhsm_xml.get_widget("entitlementChooseVbox")
        self.choose_win = managergui.rhsm_xml.get_widget("entitlement_selection")
        self.rhesus_button = managergui.rhsm_xml.get_widget("rhesus_button")
        self.rhn_button = managergui.rhsm_xml.get_widget("rhn_button")
        self.local_button = managergui.rhsm_xml.get_widget("local_button")

    def createScreen(self):
        self.vbox = gtk.VBox(spacing=10)
        self.choose_dialog = managergui.rhsm_xml.get_widget(
                "entitlementChooseVbox")
        self.choose_dialog.reparent(self.vbox)

    def apply(self, interface, testing=False):
        if self.rhesus_button.get_active():
            interface.moveToPage(
                    moduleTitle=_("Entitlement Platform Registration"))
            return RESULT_JUMP

        if self.local_button.get_active():
            subPage = interface.titleToPageNum(_("Subscription Manager"),
                                               interface.moduleList)
            interface.moveToPage(pageNum=subPage + 1)
            return RESULT_JUMP

        if self.rhn_button.get_active():
            interface.moveToPage(moduleTitle=_("Set Up Software Updates"))
            return RESULT_JUMP

        # if none of these have been selected, then 
        # we can't go any further
        return RESULT_FAILURE

    def initializeUI(self):
        pass

    def needsNetwork(self):
        # Technically, this module does NOT need networking,
        # but both the UEP and RHN choices do - so we just
        # skip this module altogether if there is no network
        # available
        return True

    def shouldAppear(self):
        return not ConsumerIdentity.exists()
