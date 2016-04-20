#! /usr/bin/env python
from rhsmlib.dbus.common import gi_kluge
gi_kluge.kluge_it()

from gi.repository import GLib

import dbus.service
import dbus.mainloop.glib

from rhsmlib.dbus.common import decorators

DBUS_NAME = "com.redhat.Subscriptions1.RegisterService"
DBUS_INTERFACE = "com.redhat.Subscriptions1.RegisterService"
DBUS_PATH = "/com/redhat/Subscriptions1/RegisterService"


class RegisterService(dbus.service.Object):
    def __init__(self, bus, object_path=DBUS_PATH):
        print "Created RegisterService"
        bus_name = dbus.service.BusName(DBUS_NAME, bus=bus)
        super(RegisterService, self).__init__(object_path=object_path, bus_name=bus_name)

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE, out_signature='s', in_signature='s')
    def reverse(self, text, sender=None):
        text = list(text)
        text.reverse()
        return ''.join(text)


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    bus = dbus.StarterBus()
    RegisterService(bus)

    try:
        mainloop.run()
    except KeyboardInterrupt as e:
        print(e)
    except SystemExit as e:
        print(e)
    except Exception as e:
        print(e)
    finally:
        mainloop.quit()
