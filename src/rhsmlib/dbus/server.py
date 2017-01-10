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
import threading

from rhsmlib.dbus import constants

from subscription_manager import ga_loader
ga_loader.init_ga()
from subscription_manager.ga import GLib

from functools import partial

log = logging.getLogger(__name__)


class Server(object):
    def __init__(self, bus_class=None, bus_name=None, object_classes=None, bus_kwargs=None):
        """Create a connection to a bus defined by bus_class and bus_kwargs; instantiate objects in
        object_classes; expose them under bus_name and enter a GLib mainloop.  bus_kwargs are generally
        only necessary if you're using dbus.bus.BusConnection

        The object_classes argument is a list.  The list can contain either a class or a tuple consisting
        of a class and a dictionary of arguments to send that class's constructor.
        """

        # Configure mainloop for threading.  We must do so in GLib and python-dbus.
        GLib.threads_init()
        dbus.mainloop.glib.threads_init()

        self.bus_name = bus_name or constants.BUS_NAME
        bus_class = bus_class or dbus.SystemBus
        bus_kwargs = bus_kwargs or {}
        object_classes = object_classes or []
        self.objects = []

        try:
            self.bus = bus_class(**bus_kwargs)
        except dbus.exceptions.DBusException:
            log.exception("Could not create bus class")
            raise

        self.connection_name = dbus.service.BusName(self.bus_name, self.bus)
        self.mainloop = GLib.MainLoop()

        for item in object_classes:
            try:
                clazz, kwargs = item[0], item[1]
            except TypeError:
                clazz = item
                kwargs = {}

            self.objects.append(
                clazz(object_path=clazz.default_dbus_path, bus_name=self.connection_name, **kwargs)
            )

    def run(self, started_event=None, stopped_event=None):
        """The two arguments, started_event and stopped_event, should be instances of threading.Event that
        will be set when the mainloop has finished starting and stopping."""
        try:
            GLib.idle_add(self.notify_started, started_event)
            self.mainloop.run()
        except KeyboardInterrupt as e:
            log.exception(e)
        except SystemExit as e:
            log.exception(e)
        except Exception as e:
            log.exception(e)
        finally:
            if stopped_event:
                stopped_event.set()

    def notify_started(self, started_event):
        """This callback will be run once the mainloop is up and running.  It's only purpose is to alert
        other blocked threads that the mainloop is ready."""
        log.debug("Start notification sent")
        if started_event:
            started_event.set()
        # Only run this callback once
        return False

    def shutdown(self):
        """This method is primarily intended for uses of Server in a thread such as during testing since
        in a single-threaded program, the execution would be blocked on the mainloop and therefore
        preclude even calling this method."""
        self.mainloop.quit()

        # Unregister/remove everything.  Note that if you used dbus.SessionBus or dbus.SystemBus,
        # python-dbus will keep a cache of your old BusName objects even though we are releasing the name
        # here.  This will create a problem if you attempt to reacquire the BusName since python-dbus will
        # give you a stale reference.  Use dbus.Connection.BusConnection to avoid this problem.
        # See http://stackoverflow.com/questions/17446414/dbus-object-lifecycle
        map(lambda x: x.remove_from_connection(), self.objects)
        self.bus.release_name(self.bus_name)


class DomainSocketServer(object):
    """This class sets up a DBus server on a domain socket. That server can then be used to perform
    registration. The issue is that we can't send registration credentials over the regular system or
    session bus since those aren't really locked down. The work-around is the client asks our service
    to open another server on a domain socket, gets socket information back, and then connects and sends
    the register command (with the credentials) to the server on the domain socket."""
    @staticmethod
    def connection_added(domain_socket_server, service_class, object_list, conn):
        object_list.append(service_class(conn=conn))
        with domain_socket_server.lock:
            domain_socket_server.connection_count += 1
        log.info("New connection: %s", conn)

    @staticmethod
    def connection_removed(domain_socket_server, conn):
        log.debug("Closed connection: %s", conn)
        with domain_socket_server.lock:
            domain_socket_server.connection_count -= 1
            if domain_socket_server.connection_count == 0:
                log.debug('No connections remain')
            else:
                log.debug('Server still has connections')

    @property
    def address(self):
        if self._server:
            return self._server.address
        else:
            return None

    def __init__(self, object_classes=None):
        """Create a connection to a bus defined by bus_class and bus_kwargs; instantiate objects in
        object_classes; expose them under bus_name and enter a GLib mainloop.  bus_kwargs are generally
        only necessary if you're using dbus.bus.BusConnection

        The object_classes argument is a list.  The list can contain either a class or a tuple consisting
        of a class and a dictionary of arguments to send that class's constructor.
        """
        self.object_classes = object_classes or []
        self.objects = []

        self.lock = threading.Lock()
        with self.lock:
            self.connection_count = 0

    def shutdown(self):
        map(lambda x: x.remove_from_connection(), self.objects)
        self._server.disconnect()

        # Allow self.objects and self._server to get GCed
        self.objects = None
        self._server = None

    def run(self):
        try:
            self._server = dbus.server.Server("unix:tmpdir=/var/run")

            for clazz in self.object_classes:
                self._server.on_connection_added.append(
                    partial(DomainSocketServer.connection_added, self, clazz, self.objects)
                )

            self._server.on_connection_removed.append(
                partial(DomainSocketServer.connection_removed, self)
            )

            return self.address
        except Exception as e:
            log.exception(e)
