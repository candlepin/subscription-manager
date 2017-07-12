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
import dbus
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.attach import AttachService

from subscription_manager.injectioninit import init_dep_injection

init_dep_injection()

log = logging.getLogger(__name__)


class AttachDBusObject(base_object.BaseObject):
    default_dbus_path = constants.ATTACH_DBUS_PATH
    interface_name = constants.ATTACH_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(AttachDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.ATTACH_INTERFACE,
        in_signature='sa{sv}',
        out_signature='aa{sv}')
    @util.dbus_handle_exceptions
    def AutoAttach(self, service_level, proxy_options, sender=None):
        self.ensure_registered()
        service_level = dbus_utils.dbus_to_python(service_level, str)

        proxy_options = self.build_proxy_information(proxy_options)
        attach_service = AttachService(proxy_options)

        try:
            result = attach_service.attach_auto(service_level)
        except Exception as e:
            log.exception(e)
            raise dbus.DBusException(str(e))

        return [dbus_utils.dict_to_variant_dict(x['pool']) for x in result]

    @util.dbus_service_method(
        constants.ATTACH_INTERFACE,
        in_signature='asia{sv}',
        out_signature='aa{sv}')
    @util.dbus_handle_exceptions
    def PoolAttach(self, pools, quantity, proxy_options, sender=None):
        self.ensure_registered()
        pools = dbus_utils.dbus_to_python(pools, list)
        quantity = dbus_utils.dbus_to_python(quantity, int)

        if quantity < 1:
            raise dbus.DBusException("Quantity must be a positive number.")

        proxy_options = self.build_proxy_information(proxy_options)
        attach_service = AttachService(proxy_options)

        try:
            result = []
            for pool in pools:
                ents = attach_service.attach_pool(pool, quantity)
                result.extend(ents)
        except Exception as e:
            log.exception(e)
            raise dbus.DBusException(str(e))

        return [dbus_utils.dict_to_variant_dict(x['pool']) for x in result]
