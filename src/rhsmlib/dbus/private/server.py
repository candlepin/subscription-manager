#! /usr/bin/env python
from rhsmlib.dbus.common import gi_kluge
from rhsmlib.dbus.private.register_service import RegisterService
gi_kluge.kluge_it()

from gi.repository import GLib

import dbus.server
import dbus.service
import dbus.mainloop.glib

from rhsmlib.dbus.common import decorators


def connection_added(conn):
    RegisterService(conn)
    print("New connection")


def connection_removed(conn):
    print("Connection closed")


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    server = dbus.server.Server("unix:path=/tmp/subman.sock")
    server.on_connection_added.append(connection_added)
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
