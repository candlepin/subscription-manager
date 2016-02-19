
import logging

import dbus

from rhsm.dbus.services import base_server
from rhsm.dbus.services.facts import constants
from rhsm.dbus.services.facts import root

log = logging.getLogger(__name__)


def run(bus_class=None, bus_name=None):
    bus_class = bus_class or dbus.SystemBus
    bus_name = bus_name or constants.FACTS_BUS_NAME

    service_classes = [root.FactsRoot]

    base_server.run_services(bus_class=bus_class,
                             bus_name=bus_name,
                             service_classes=service_classes)
