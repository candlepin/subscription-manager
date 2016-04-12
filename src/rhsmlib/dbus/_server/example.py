from rhsmlib.dbus.common import gi_kluge
gi_kluge.kluge_it()

from gi.repository import GLib

import dbus.service
import dbus.server
import dbus.mainloop.glib
import dbus.connection

import slip.dbus
import slip.dbus.service


class DBusSocketServer(dbus.server.Server):

    def __new__(cls, address, connection_class=dbus.connection.Connection,
      mainloop=None, auth_mechanisms=None):
        return super(DBusSocketServer, cls).__new__(cls, address,
          connection_class, mainloop, auth_mechanisms)

    def __init__(self, *args, **kwargs):
        self.bus_connection = None
        self.__connections = []

    def connection_added(self, connection):
        self.__connections.append(connection)
        print "Connection Added"
        print self.__connections

    def connection_removed(self, connection):
        self.__connections.remove(connection)
        print "Connection Removed"
        print self.__connections

def run_server():
    # Taken mostly from base_server.py
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()
    socket_address = "/var/run/subman.sock"
    server = DBusSocketServer("unix:path=%s" % socket_address)

    mainloop = GLib.MainLoop()
    slip.dbus.service.set_mainloop(mainloop)

    mainloop.run()



if __name__ == '__main__':
    run_server()
