import sys
import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

import rhsm

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import autobind
from subscription_manager.certlib import ConsumerIdentity


class moduleClass(Module):

    def __init__(self):
        Module.__init__(self)

        self.priority = 200.3
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Confirm Subscriptions")

        self.screen = autobind.ConfirmSubscriptionsScreen(None)

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - try to register with the
        provided user credentials and return the appropriate result
        value.
        """

        self.interface = interface

        return RESULT_SUCCESS

    def createScreen(self):
        """
        Create a new instance of gtk.VBox, pulling in child widgets from the
        glade file.
        """
        self.vbox = gtk.VBox(spacing=10)
        widget = self.screen.get_main_widget()
        widget.reparent(self.vbox)


    def initializeUI(self):
        # Need to make sure that each time the UI is initialized we reset back to the
        # main register screen.
        #self._show_credentials_page()
        #self._clear_registration_widgets()
        #self.initializeConsumerName()
        self.vbox.show_all()

    def needsNetwork(self):
        """
        This lets firstboot know that networking is required, in order to
        talk to hosted UEP.
        """
        return True

    def shouldAppear(self):
        """
        Indicates to firstboot whether to show this screen.  In this case
        we want to skip over this screen if there is already an identity
        certificate on the machine (most likely laid down in a kickstart).
        """
        return not ConsumerIdentity.existsAndValid()

