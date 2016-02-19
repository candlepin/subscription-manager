
import logging

import dbus

from rhsm.dbus.services import base_server
from rhsm.dbus.services.facts import service

log = logging.getLogger(__name__)


def run(bus_class=None, bus_name=None):
    bus_class = bus_class or dbus.SystemBus

    bus_name = bus_name or "com.redhat.Subscriptions1.Facts"

    service_classes = [service.FactsRoot]

    base_server.run_services(bus_class=bus_class,
                             bus_name=bus_name,
                             services_classes=service_classes)
