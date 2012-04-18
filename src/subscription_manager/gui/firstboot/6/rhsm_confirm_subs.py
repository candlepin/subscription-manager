import sys
import gtk

from firstboot.config import *
from firstboot.constants import *
from firstboot.functions import *
from firstboot.module import *
from firstboot.module import Module

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import autobind
from subscription_manager.certlib import ConsumerIdentity


class moduleClass(Module):

    def __init__(self):
        Module.__init__(self)

        self.priority = 200.4
        self.sidebarTitle = _("Entitlement Registration")
        self.title = _("Confirm Subscriptions")

        self.screen = autobind.ConfirmSubscriptionsScreen(None, None)

        # Used to determine if the user has selected a new SLA or reregistered
        # after a back button press
        self.old_consumer = None
        self.old_sla = None
        self.old_entitlements = []

    def apply(self, interface, testing=False):

        if self.old_consumer == self.screen.controller.consumer:
            if self.old_sla != self.screen.controller.selected_sla:
                self.old_sla = self.screen.controller.selected_sla
                # XXX need to unsubscribe from previously subscribed
                # entitlements here.
                for entitlement in self.old_entitlements:
                    self.screen.controller.backend.uep.unbindBySerial(
                            self.screen.controller.consumer.uuid, entitlement)
                self.old_entitlements = self.screen.forward()
            # otherwise both consumer and selected sla are the same. we can
            # just move forward.
        else:
            self.old_consumer = self.screen.controller.consumer
            self.old_sla = self.screen.controller.selected_sla
            # screen.forward takes care of subscribing.
            self.old_entitlements = self.screen.forward()

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

        if len(controller.suitable_slas) == 1:
            service_level = controller.suitable_slas.keys()[0]
        else:
            service_level = controller.selected_sla

        self.screen.load_data(controller.suitable_slas[service_level])

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
