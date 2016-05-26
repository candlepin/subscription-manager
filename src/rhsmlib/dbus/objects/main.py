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
import rhsmlib.dbus as common

from rhsmlib.dbus.server import PrivateServer
from rhsmlib.dbus.objects.private import RegisterService

from functools import partial

log = logging.getLogger(__name__)


class Main(dbus.service.Object):
    default_dbus_path = common.MAIN_DBUS_PATH

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
        log.debug('start_registration called')
        server = self._create_registration_server()
        return server.address

    def _disconnect_on_last_connection(self, server, conn):
        log.debug('Checking if server "%s" has any remaining connections', server)
        if server._Server__connections:
            log.debug('Server still has connections')
            return

        log.debug('No connections remain, disconnecting')
        server.disconnect()
        del server

    def _create_registration_server(self):
        log.debug('Attempting to create new server')
        server = PrivateServer().run([RegisterService])
        server.on_connection_removed.append(partial(self._disconnect_on_last_connection, server))
        log.debug('Server created and listening on "%s"', server.address)
        return server
