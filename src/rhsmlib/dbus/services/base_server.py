
import logging

from rhsm.dbus.common import gi_kluge
gi_kluge.kluge_it()

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.dbus.common import constants

log = logging.getLogger(__name__)


# factory?
def run_services(bus_class=None, bus_name=None, service_classes=None):
    """bus == dbus.SystemBus() etc.
    service_class is the the class implementing a DBus Object/service."""

    service_classes = service_classes or None
    bus_name = bus_name or constants.SERVICE_NAME

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    bus_class = bus_class or dbus.SystemBus
    bus = bus_class()

    log.debug("service_classes=%s", service_classes)
    for service_class in service_classes:
        connection_name = dbus.service.BusName(bus_name, bus)
        log.debug("service_class=%s", service_class)
        log.debug("service_class.default_dbus_path=%s", service_class.default_dbus_path)
        service = service_class(conn=connection_name,
                                object_path=service_class.default_dbus_path)

    mainloop = GLib.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    GLib.idle_add(start_signal_idle_callback, service)

    try:
        mainloop.run()
    except KeyboardInterrupt as e:
        log.exception(e)
    except SystemExit as e:
        log.exception(e)
        log.debug("system exit")
    except Exception as e:
        log.exception(e)

    if service:
        service.stop()


def start_signal_idle_callback(service):
    service.ServiceStarted()
    return False
