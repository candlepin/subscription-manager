#! /usr/bin/env python
from rhsmlib.dbus.common import gi_kluge
gi_kluge.kluge_it()
from rhsmlib.dbus.private.register_service import RegisterService


from gi.repository import GLib

import dbus.server
import dbus.service
import dbus.mainloop.glib

from functools import partial

from rhsmlib.dbus.common import decorators


def connection_added(service_class, conn):
    service_class(conn=conn)
    print("New connection")

def connection_removed(conn):
    print("Connection closed")

def start_server():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    server = dbus.server.Server("unix:path=/tmp/subman.sock")
    server.on_connection_added.append(partial(connection_added, RegisterService))
    server.on_connection_removed.append(connection_removed)

    mainloop = GLib.MainLoop()

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

if __name__ == "__main__":
    start_server()
