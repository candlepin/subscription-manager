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
import dbus
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.config import Config

from dbus import DBusException
log = logging.getLogger(__name__)


class ConfigDBusObject(base_object.BaseObject):
    default_dbus_path = constants.CONFIG_DBUS_PATH
    interface_name = constants.CONFIG_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None, parser=None):
        self.config = Config(parser)
        super(ConfigDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='sv')
    @util.dbus_handle_exceptions
    def Set(self, property_name, new_value, sender=None):
        property_name = dbus_utils.dbus_to_python(property_name, str)
        new_value = dbus_utils.dbus_to_python(new_value, str)
        section, _dot, property_name = property_name.partition('.')

        if not property_name:
            raise DBusException("Setting an entire section is not supported.  Use 'section.property' format.")

        self.config[section][property_name] = new_value
        self.config.persist()

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='',
        out_signature='a{sv}')
    @util.dbus_handle_exceptions
    def GetAll(self, sender=None):
        d = dbus.Dictionary({}, signature='sv')
        for k, v in self.config.iteritems():
            d[k] = dbus.Dictionary({}, signature='ss')
            for kk, vv in v.iteritems():
                d[k][kk] = vv

        return d

    @util.dbus_service_method(
        constants.CONFIG_INTERFACE,
        in_signature='s',
        out_signature='v')
    @util.dbus_handle_exceptions
    def Get(self, property_name, sender=None):
        section, _dot, property_name = property_name.partition('.')

        if property_name:
            return self.config[section][property_name]
        else:
            return dbus.Dictionary(self.config[section], signature='sv')
