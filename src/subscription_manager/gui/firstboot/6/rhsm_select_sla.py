import sys
import gtk

from firstboot.constants import RESULT_SUCCESS
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)


sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import autobind
from subscription_manager.certlib import ConsumerIdentity


class moduleClass(Module):

    def __init__(self):
        Module.__init__(self)

        self.priority = 200.3
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Service Level")

        self.screen = autobind.SelectSLAScreen(None, None)

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - autobind controller
        will have already stored the selected sla
        """
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
        self.vbox.show_all()

        # lazy initialize this, so its created in rhsm_login
        controller = autobind.get_controller()
        self.screen.controller = controller

        self.screen.load_data(
                set(controller.sorter.unentitled_products.values()),
                controller.suitable_slas)

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
