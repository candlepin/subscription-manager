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
import dbus.service
import rhsmlib.dbus as common


class PrivateService(dbus.service.Object):
    """ The base class for service objects to be exposed on either a private connection
        or a bus."""
    _interface_name = None
    _default_dbus_path = common.ROOT_DBUS_PATH
    _default_dbus_path += ("/" + _interface_name) if _interface_name else ""
    _default_bus_name = common.SERVICE_NAME

    def __init__(self, conn=None, bus=None, object_path=None):
        if object_path is None or object_path == "":
            # If not given a path to be exposed on, use class defaults
            _interface_name = self.__class__._interface_name
            object_path = self.__class__._default_dbus_path + \
                ("/" + _interface_name) if _interface_name else ""

        bus_name = None
        if bus is not None:
            # If we are passed in a bus, try to claim an appropriate bus name
            bus_name = dbus.service.BusName(self.__class__._default_bus_name, bus)

        super(PrivateService, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)
