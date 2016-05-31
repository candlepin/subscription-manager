# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import logging
import dbus.service
import dbus.server
import dbus.mainloop.glib
import rhsmlib.dbus as common

from gi.repository import GLib
from functools import partial

log = logging.getLogger(__name__)


class Server(object):
    def run(self, bus_class=None, bus_name=None, object_classes=None):
        """bus == dbus.SystemBus() etc.
        object_class is the the class implementing a DBus Object"""

        object_classes = object_classes or []
        bus_name = bus_name or common.BUS_NAME

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus.mainloop.glib.threads_init()

        bus_class = bus_class or dbus.SystemBus
        bus = bus_class()

        log.debug("object_classes=%s", object_classes)
        for clazz in object_classes:
            connection_name = dbus.service.BusName(bus_name, bus)
            clazz(object_path=clazz.default_dbus_path, bus_name=connection_name)

        mainloop = GLib.MainLoop()

        try:
            mainloop.run()
        except KeyboardInterrupt as e:
            log.exception(e)
        except SystemExit as e:
            log.exception(e)
            log.debug("system exit")
        except Exception as e:
            log.exception(e)
        finally:
            mainloop.quit()


class PrivateServer(object):
    @staticmethod
    def connection_added(service_class, conn):
        service_class(conn=conn)
        print("New connection")

    @staticmethod
    def connection_removed(conn):
        print("Connection closed")

    def create_server(self, object_classes=None):
        object_classes = object_classes or []
        server = dbus.server.Server("unix:tmpdir=/var/run")
        server.on_connection_removed.append(PrivateServer.connection_removed)
        log.debug("object_classes=%s", object_classes)

        for clazz in object_classes:
            server.on_connection_added.append(partial(PrivateServer.connection_added, clazz))
        return server

    def run(self, object_classes=None):
        """bus == dbus.SystemBus() etc.
        object_class is the the class implementing a DBus Object"""
        object_classes = object_classes or []

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dbus.mainloop.glib.threads_init()

        server = self.create_server(object_classes=object_classes)
        log.info("Server created: %s" % server.get_address())

        mainloop = GLib.MainLoop()

        try:
            mainloop.run()
        except KeyboardInterrupt as e:
            log.exception(e)
        except SystemExit as e:
            log.exception(e)
            log.debug("system exit")
        except Exception as e:
            log.exception(e)
        finally:
            mainloop.quit()
