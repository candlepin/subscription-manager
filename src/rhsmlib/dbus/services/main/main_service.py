#
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
import rhsmlib.dbus as common
import dbus.service

from rhsmlib.dbus.services import BaseService, private_server
from rhsmlib.dbus.services.config import ConfigService
from rhsmlib.dbus.services.facts import FactsHost

from functools import partial

common.init_root_logger()


class MainService(BaseService):
    _well_known_bus_name = common.SERVICE_NAME
    _interface_name = common.MAIN_INTERFACE
    _service_name = common.SERVICE_NAME

    def __init__(self, conn=None, object_path=None, bus_name=None, bus=None,
                 service_classes=None):
        # self.service_classes = service_classes or [ConfigService, FactsHost]
        self.service_classes = []
        self.interface_to_service = {}

        # Create bus name
        if bus_name is None:
            # We cannot proceed without a bus
            assert bus is not None
            well_known_bus_name = self.__class__._well_known_bus_name
            bus_name = dbus.service.BusName(well_known_bus_name, bus)

        assert bus_name is not None
        self.bus_name = bus_name
        super(MainService, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self._init_service_classes()

    def _init_service_classes(self):
        self.log.debug('Initializing service classes: %s', self.service_classes)
        for service_class in self.service_classes:
            service_instance = service_class(bus_name=self.bus_name, base_object_path=self.object_path)
            self.interface_to_service[service_instance._interface_name] = service_instance

    @dbus.service.method(
        dbus_interface=common.MAIN_INTERFACE,
        in_signature='s',
        out_signature='o')
    def get_object_for_interface(self, interface):
        return self.interface_to_service.get(interface, None)

    @dbus.service.method(
        dbus_interface=common.MAIN_INTERFACE,
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
