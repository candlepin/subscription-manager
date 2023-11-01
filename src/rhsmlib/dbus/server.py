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

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type

import dbus.service
import dbus.server
import dbus.mainloop.glib
import threading

from rhsmlib.dbus import constants

from rhsm import connection

from gi.repository import GLib
from functools import partial

from rhsmlib.services import config
from rhsmlib.dbus.dbus_utils import pid_of_sender
from rhsm.config import get_config_parser
from rhsmlib.file_monitor import create_filesystem_watcher, DirectoryWatch
from rhsmlib.file_monitor import (
    CONSUMER_WATCHER,
    ENTITLEMENT_WATCHER,
    CONFIG_WATCHER,
    PRODUCT_WATCHER,
    SYSPURPOSE_WATCHER,
)
from subscription_manager import injection as inj
from rhsm.logutil import init_logger

if TYPE_CHECKING:
    import dbus._dbus
    from rhsmlib.dbus.base_object import BaseObject


log = logging.getLogger(__name__)

parser = get_config_parser()
conf = config.Config(parser)


class Server:
    """
    Class used for rhsm.service providing D-Bus API
    """

    INSTANCE = None

    def __new__(cls, *args, **kwargs):
        """
        Function called, when new instance of Server is requested
        """
        cls.INSTANCE = object.__new__(cls)
        return cls.INSTANCE

    def __init__(
        self,
        bus_class: Optional["dbus._dbus.Bus"] = None,
        bus_name: Optional[str] = None,
        object_classes: List[Type["BaseObject"]] = None,
        bus_kwargs: Optional[dict] = None,
    ):
        """
        Create a connection to a bus defined by bus_class and bus_kwargs; instantiate objects in
        object_classes; expose them under bus_name and enter a GLib mainloop.  bus_kwargs are generally
        only necessary if you're using dbus.bus.BusConnection

        The object_classes argument is a list.  The list can contain either a class or a tuple consisting
        of a class and a dictionary of arguments to send that class's constructor.
        """

        # Do not allow reusing connection, because server uses multiple threads. If reusing connection
        # was used, then two threads could try to use the connection in the almost same time.
        # It means that one thread could send request and the second one could send second request
        # before the first thread received response. This could lead to raising exception CannotSendRequest.
        connection.REUSE_CONNECTION = False

        init_logger(parser)

        # Configure mainloop for threading.  We must do so in GLib and python-dbus.
        dbus.mainloop.glib.threads_init()

        self.bus_name = bus_name or constants.BUS_NAME
        bus_class = bus_class or dbus.SystemBus
        bus_kwargs = bus_kwargs or {}
        object_classes = object_classes or []
        self.objects = []
        self.object_map = {}

        try:
            self.bus = bus_class(**bus_kwargs)
        except dbus.exceptions.DBusException:
            log.exception("Could not create bus class")
            raise
        self.identity = inj.require(inj.IDENTITY)  # gives us consumer path
        config_cert_dir_path = "/etc/rhsm/rhsm.conf"
        products_cert_dir_path = conf["rhsm"]["productCertDir"]
        entitlement_cert_dir_path = conf["rhsm"]["entitlementCertDir"]
        syspurpose_cert_dir_path = "/etc/rhsm/syspurpose/syspurpose.json"

        self.connection_name = dbus.service.BusName(self.bus_name, self.bus)
        self.mainloop = GLib.MainLoop()

        for item in object_classes:
            clazz: Type[BaseObject]
            kwargs: Dict[str, Any]
            try:
                clazz, kwargs = item[0], item[1]
            except TypeError:
                clazz = item
                kwargs = {}

            clazz_instance: BaseObject = clazz(
                object_path=clazz.default_dbus_path, bus_name=self.connection_name, **kwargs
            )
            self.objects.append(clazz_instance)
            self.object_map[str(clazz.__name__)] = clazz_instance

        consumer_dir_list = []
        entitlement_dir_list = []
        config_dir_list = []
        products_dir_list = []
        syspurpose_dir_list = []
        if "EntitlementDBusObject" in self.object_map:
            entitlement_dir_list.append(self.object_map["EntitlementDBusObject"].reload)
            consumer_dir_list.append(self.object_map["EntitlementDBusObject"].reload)
            products_dir_list.append(self.object_map["EntitlementDBusObject"].reload)
            syspurpose_dir_list.append(self.object_map["EntitlementDBusObject"].reload)
            entitlement_dir_list.append(self.object_map["EntitlementDBusObject"].EntitlementChanged)
        if "ConsumerDBusObject" in self.object_map:
            consumer_dir_list.append(self.object_map["ConsumerDBusObject"].ConsumerChanged)
        if "ConfigDBusObject" in self.object_map:
            config_dir_list.append(self.object_map["ConfigDBusObject"].impl.reload)
            config_dir_list.append(self.object_map["ConfigDBusObject"].ConfigChanged)
        if "ProductsDBusObject" in self.object_map:
            products_dir_list.append(self.object_map["ProductsDBusObject"].InstalledProductsChanged)
        if "SyspurposeDBusObject" in self.object_map:
            syspurpose_dir_list.append(self.object_map["SyspurposeDBusObject"].SyspurposeChanged)

        consumer_dir_watch = DirectoryWatch(self.identity.cert_dir_path, consumer_dir_list)
        entitlement_dir_watch = DirectoryWatch(entitlement_cert_dir_path, entitlement_dir_list)
        config_dir_watch = DirectoryWatch(config_cert_dir_path, config_dir_list)
        products_dir_watch = DirectoryWatch(products_cert_dir_path, products_dir_list)
        syspurpose_dir_watch = DirectoryWatch(syspurpose_cert_dir_path, syspurpose_dir_list)

        self.filesystem_watcher = create_filesystem_watcher(
            {
                CONSUMER_WATCHER: consumer_dir_watch,
                ENTITLEMENT_WATCHER: entitlement_dir_watch,
                CONFIG_WATCHER: config_dir_watch,
                PRODUCT_WATCHER: products_dir_watch,
                SYSPURPOSE_WATCHER: syspurpose_dir_watch,
            }
        )
        self._thread = threading.Thread(
            target=self.filesystem_watcher.loop,
            name="Thread-FileSystemWatcher",
        )
        self._thread.start()

    def run(self, started_event=None, stopped_event=None):
        """
        The two arguments, started_event and stopped_event, should be instances of threading.
        Event that will be set when the mainloop has finished starting and stopping.
        """
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
            # Terminate loop of notifier
            self.filesystem_watcher.stop()
            if stopped_event:
                stopped_event.set()

    @staticmethod
    def notify_started(started_event):
        """
        This callback will be run once the mainloop is up and running. It's only purpose is to alert
        other blocked threads that the mainloop is ready.
        """
        if started_event:
            started_event.set()
        # Only run this callback once
        return False

    def shutdown(self):
        """
        This method is primarily intended for uses of Server in a thread such as during testing since
        in a single-threaded program, the execution would be blocked on the mainloop and therefore
        preclude even calling this method.
        """
        self.mainloop.quit()

        # Make sure loop is terminated
        self.filesystem_watcher.stop()
        # Wait for notification thread to join
        self._thread.join(2)

        # Unregister/remove everything.  Note that if you used dbus.SessionBus or dbus.SystemBus,
        # python-dbus will keep a cache of your old BusName objects even though we are releasing the name
        # here.  This will create a problem if you attempt to reacquire the BusName since python-dbus will
        # give you a stale reference.  Use dbus.Connection.BusConnection to avoid this problem.
        # See http://stackoverflow.com/questions/17446414/dbus-object-lifecycle
        for obj in self.objects:
            obj.remove_from_connection()

        log.debug(f"Releasing Bus name: {self.bus_name}")
        self.bus.release_name(self.bus_name)

    @classmethod
    def temporary_disable_dir_watchers(cls, watcher_set: set = None) -> None:
        """
        This function temporary disables file system directory watchers
        :param watcher_set: Set of watchers. If the watcher is None, then all watchers are disabled
        :return: None
        """
        server_instance = cls.INSTANCE
        if server_instance is None:
            return

        # Temporary disable watchers
        for dir_watcher_id, dir_watcher in server_instance.filesystem_watcher.dir_watches.items():
            # When watcher_set is not empty, then check if watcher_id is
            # included in the set
            if watcher_set is not None and dir_watcher_id not in watcher_set:
                continue
            log.debug(f"Disabling directory watcher: {dir_watcher_id}")
            dir_watcher.temporary_disable()

    @classmethod
    def enable_dir_watchers(cls, watcher_set: set = None) -> None:
        """
        This function enables file system directory watchers
        :param watcher_set: Set of watcher. If the watcher is None, then all watchers are enabled
        :return: None
        """
        server_instance = cls.INSTANCE
        if server_instance is None:
            return
        for dir_watcher_id, dir_watcher in server_instance.filesystem_watcher.dir_watches.items():
            if watcher_set is not None and dir_watcher_id not in watcher_set:
                continue
            log.debug(f"Enabling directory watcher: {dir_watcher_id}")
            dir_watcher.enable()


class DomainSocketServer:
    """This class sets up a DBus server on a domain socket. That server can then be used to perform
    registration. The issue is that we can't send registration credentials over the regular system or
    session bus since those aren't really locked down. The work-around is the client asks our service
    to open another server on a domain socket, gets socket information back, and then connects and sends
    the register command (with the credentials) to the server on the domain socket."""

    # FIXME Use `dir` instead.
    # `tmpdir` behaves differently from `dir` on old versions of dbus
    # (earlier than 1.12.24 and 1.14.4).
    # In newer versions we are not getting abstract socket anymore.
    _server_socket_iface: str = "unix:tmpdir="
    _server_socket_path: str = "/run"

    @property
    def _server_socket(self):
        return self._server_socket_iface + self._server_socket_path

    @staticmethod
    def connection_added(domain_socket_server, service_class, object_list, conn):
        obj = service_class(
            conn=conn,
            sender=domain_socket_server.sender,
            cmd_line=domain_socket_server.cmd_line,
        )
        log.debug("Instance: %s of %s created" % (obj, service_class))
        object_list.append(obj)
        with domain_socket_server.lock:
            domain_socket_server.connection_count += 1
        log.debug("New connection: %s", conn)

    @staticmethod
    def connection_removed(domain_socket_server, conn):
        log.debug("Closed connection: %s", conn)
        with domain_socket_server.lock:
            domain_socket_server.connection_count -= 1
            if domain_socket_server.connection_count == 0:
                log.debug("No connections remain")
            else:
                if domain_socket_server.connection_count == 1:
                    log.debug("Server still has one connection")
                else:
                    log.debug("Server still has %d connections" % domain_socket_server.connection_count)

    @property
    def address(self):
        if self._server:
            return self._server.address
        else:
            return None

    def __init__(self, object_classes=None, sender=None, cmd_line=None):
        """Create a connection to a bus defined by bus_class and bus_kwargs; instantiate objects in
        object_classes; expose them under bus_name and enter a GLib mainloop.  bus_kwargs are generally
        only necessary if you're using dbus.bus.BusConnection

        The object_classes argument is a list.  The list can contain either a class or a tuple consisting
        of a class and a dictionary of arguments to send that class's constructor.
        """
        self.object_classes = object_classes or []
        self.objects = []
        self._server = None
        self.sender = sender  # sender created the server
        self._senders = set()  # other senders using server
        log.debug(f"Adding sender {sender} to the set of senders")
        self._senders.add(sender)
        self.cmd_line = cmd_line

        self.lock = threading.Lock()
        with self.lock:
            self.connection_count = 0

    def add_sender(self, sender: str) -> None:
        """
        Add sender to the list of senders
        """
        self._senders.add(sender)

    def remove_sender(self, sender: str) -> bool:
        """
        Try to remove sender from the set of sender
        """
        try:
            self._senders.remove(sender)
        except KeyError:
            log.debug(f"Sender {sender} wasn't removed from the set of senders (not member of the set)")
            return False
        else:
            log.debug(f"Sender {sender} removed from the set of senders")
            return True

    def are_other_senders_still_running(self) -> bool:
        """
        Check if other users are still running. It sender in the set is not
        running, then remove sender from the set, because sender could
        crash, or it was terminated since it called Start() method.
        """
        is_one_sender_running = False
        not_running = set()
        bus = dbus.SystemBus()
        for sender in self._senders:
            pid = pid_of_sender(bus, sender)
            if pid is None:
                not_running.add(sender)
            else:
                is_one_sender_running = True
        self._senders = self._senders.difference(not_running)
        return is_one_sender_running

    def shutdown(self):
        for o in self.objects:
            o.remove_from_connection()
        self._server.disconnect()

        # Allow self.objects and self._server to get GCed
        self.objects = None
        self._server = None
        self.sender = None
        self.cmd_line = None

    def run(self):
        self._server = dbus.server.Server(self._server_socket)

        for clazz in self.object_classes:
            self._server.on_connection_added.append(
                partial(DomainSocketServer.connection_added, self, clazz, self.objects)
            )

        self._server.on_connection_removed.append(partial(DomainSocketServer.connection_removed, self))

        return self.address
