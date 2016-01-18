#!/usr/bin/python

import logging
import sys


RHSM_PYTHON_PATH = "/usr/share/rhsm"
sys.path.append(RHSM_PYTHON_PATH)

log = logging.getLogger("rhsm_dbus.facts_service")

from subscription_manager import logutil
logutil.init_logger()

from subscription_manager import ga_loader
ga_loader.init_ga()

from subscription_manager.ga import GObject as ga_GObject
from subscription_manager.ga import GLib as ga_GLib

import dbus
import dbus.service
import dbus.mainloop.glib
import pprint

import slip

# FIXME: hack, monkey patch slip._wrappers._gobject so it doesn't try to outsmart gobject import
import slip._wrappers
slip._wrappers._gobject = ga_GObject

import slip.dbus
import slip.dbus.service

#from subscription_manager.ga import gtk_compat

#gtk_compat.threads_init()


FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1"


class Facts(slip.dbus.service.Object):
    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)

    @dbus.service.method(dbus_interface=FACTS_DBUS_INTERFACE,
                        in_signature='ii',
                        out_signature='i')
    def AddInts(self, int_a, int_b):
        total = int_a + int_b
        return total

    def stop(self):
        log.debug("shutting down")


def run():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    bus_name = dbus.service.BusName(FACTS_DBUS_INTERFACE, bus=bus)
    service = Facts(bus_name, FACTS_DBUS_PATH)

    mainloop = ga_GObject.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    try:
        mainloop.run()
    except KeyboardInterrupt, e:
        log.exception(e)
    except Exception, e:
        log.exception(e)
    except SystemExit, e:
        log.exception(e)
        log.debug("system exit")

    if service:
        service.stop()


def main(args):
    run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
