from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.entitlement import EntitlementService

from dbus import DBusException
log = logging.getLogger(__name__)

class EntitlementDBusObject(base_object.BaseObject):
    default_dbus_path = constants.ENTITLEMENT_DBUS_PATH
    interface_name = constants.ENTITLEMENT_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None, parser=None):
        self.service = EntitlementService()
        super(EntitlementDBusObject, self).__init__(conn=conn, 
                                                    object_path=object_path, 
                                                    bus_name=bus_name)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature="",
        out_signature="a{sv}")
    @util.dbus_handle_exceptions
    def GetStatus(self, sender=None):
        return dbus_utils.dict_to_variant_dict(self.service.get_status())

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='a{sv}',
        out_signature='a{sv}')
    @util.dbus_handle_exceptions
    def GetPools(self,dbus_options={}, sender=None):
        options = dbus_utils.dbus_to_python(dbus_options,dict)
        try:
            result = self.service.get_pools(**options)
        except connection.RestlibException as re:
            log.exception(re)
            raise dbus.DBusException(re.msg)
        
        return map(dbus_utils.dict_to_variant_dict, result)
