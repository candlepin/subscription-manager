import sys
import gtk

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import autobind
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule


class moduleClass(RhsmFirstbootModule):

    def __init__(self):
        RhsmFirstbootModule.__init__(self,
        # Firstboot module title
        # Note: translated title needs to be unique across all
        # firstboot modules, not just the rhsm ones. See bz #828042
                _("Service Level"),
                _("Entitlement Registration"),
                200.3, 109.12)

        self.screen = autobind.SelectSLAScreen(None, None)

    def apply(self, interface, testing=False):
        """
        'Next' button has been clicked - autobind controller
        will have already stored the selected sla
        """
        return self._RESULT_SUCCESS

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


# for el5
childWindow = moduleClass
