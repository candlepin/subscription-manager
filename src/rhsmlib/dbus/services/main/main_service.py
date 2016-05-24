#!/bin/python
from rhsmlib.dbus.services import base_server
from rhsmlib.dbus.common import constants, log_init, decorators
from rhsmlib.dbus.services.base_service import BaseService
from rhsmlib.dbus.services.config.config_service import ConfigService
from rhsmlib.dbus.services.facts.host import FactsHost
from rhsmlib.dbus.private import server as private_server

from functools import partial

import dbus
import dbus.service
from gi.repository import GLib

log_init.init_root_logger()

class MainService(BaseService):
    _well_known_bus_name = constants.SERVICE_NAME
    _service_name = constants.MAIN_SERVICE_NAME
    _interface_name = constants.MAIN_SERVICE_INTERFACE


    def __init__(self, conn=None, object_path=None, bus_name=None, bus=None,
                 service_classes=None):

        self.service_classes = service_classes or []
        self.interface_to_service = {}

        # Create bus name
        if bus_name is None:

            # We cannot proceed without a bus
            assert bus is not None
            well_known_bus_name = self.__class__._well_known_bus_name
            bus_name = dbus.service.BusName(well_known_bus_name, bus)

        assert bus_name is not None
        self.bus_name = bus_name

        super(MainService, self).__init__(conn=conn,
                                          object_path=object_path,
                                          bus_name=bus_name)

        self._init_service_classes()


    def _init_service_classes(self):
        self.log.debug('Initializing service classes: %s',
                       self.service_classes)
        for service_class in self.service_classes:
            service_instance = service_class(bus_name=self.bus_name,
                                             base_object_path=self.object_path)
            self.interface_to_service[service_instance._interface_name] = \
                service_instance

    @dbus.service.method(dbus_interface=constants.MAIN_SERVICE_INTERFACE,
                         in_signature='s',
                         out_signature='o')
    def get_object_for_interface(self, interface):
        return self.interface_to_service.get(interface, None)


    @dbus.service.method(dbus_interface=constants.MAIN_SERVICE_INTERFACE,
                         out_signature='s')
    def start_registration(self):
        self.log.debug('start_registration called')
        server = self._create_registration_server()
        return server.address

    def _disconnect_on_last_connection(self, server, conn):
        self.log.debug('Checking if server "%s" has any remaining connections', server)
        if server._Server__connections:
            self.log.debug('Server still has connections')
            return

        self.log.debug('No connections remain, disconnecting')
        server.disconnect()
        del server

    def _create_registration_server(self):
        self.log.debug('Attempting to create new server')
        server = private_server.create_server()
        server.on_connection_removed.append(partial(self._disconnect_on_last_connection, server))
        self.log.debug('Server created and listening on "%s"', server.address)
        return server




if __name__ == "__main__":
    service_classes = [ConfigService, FactsHost]
    # bus_name = constants.SERVICE_NAME
    # bus_class = dbus.SessionBus
    #
    # base_server.run_services(bus_class=bus_class,
    #                          bus_name=bus_name,
    #                          service_classes=service_classes)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    bus = dbus.SystemBus()#SessionBus()
    service = MainService(bus=bus, service_classes=service_classes)

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
