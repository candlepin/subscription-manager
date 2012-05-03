import sys
import gtk
import logging

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

sys.path.append("/usr/share/rhsm")
from subscription_manager.gui import autobind
from rhsm.connection import RestlibException
from subscription_manager.gui.firstboot_base import RhsmFirstbootModule


log = logging.getLogger('rhsm-app.' + __name__)


class moduleClass(RhsmFirstbootModule):

    def __init__(self):
        RhsmFirstbootModule.__init__(self,
                _("Confirm Subscriptions"),
                _("Entitlement Registration"),
                200.4, 109.13)

        self.screen = autobind.ConfirmSubscriptionsScreen(None, None)

        # Used to determine if the user has selected a new SLA or reregistered
        # after a back button press
        self.old_consumer = None
        self.old_sla = None
        self.old_entitlements = []

    def apply(self, interface, testing=False):
        # if we have an old_consumer and it's id is different than the current one
        # we are in a reregister case. See rhbz #811952
        if self.old_consumer and self.old_consumer.getConsumerId() == \
                self.screen.controller.consumer.getConsumerId():
            if self.old_sla != self.screen.controller.selected_sla:
                self.old_sla = self.screen.controller.selected_sla
                # XXX need to unsubscribe from previously subscribed
                # entitlements here.
                for entitlement in self.old_entitlements:
                    try:
                        self.screen.controller.backend.uep.unbindBySerial(
                            self.screen.controller.consumer.uuid, entitlement)
                    except RestlibException, e:
                        # we can get into this scenario with back/forward
                        # since we can unregister if we get back to the login
                        # screen. See rhbz #811952
                        log.info("Error while unsubscribing: %s" % e)
                self.old_entitlements = self.screen.forward()
            # otherwise both consumer and selected sla are the same. we can
            # just move forward.
        else:
            self.old_consumer = self.screen.controller.consumer
            self.old_sla = self.screen.controller.selected_sla
            # screen.forward takes care of subscribing.
            self.old_entitlements = self.screen.forward()

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

        if len(controller.suitable_slas) == 1:
            service_level = controller.suitable_slas.keys()[0]
        else:
            service_level = controller.selected_sla

        self.screen.load_data(controller.suitable_slas[service_level])


# for el5
childWindow = moduleClass
