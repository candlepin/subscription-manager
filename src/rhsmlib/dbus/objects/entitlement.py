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
import json
import logging

from datetime import datetime

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.entitlement import EntitlementService

from subscription_manager.injectioninit import init_dep_injection

init_dep_injection()

log = logging.getLogger(__name__)


class EntitlementDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to list, get status
    and remove pools.
    """
    default_dbus_path = constants.ENTITLEMENT_DBUS_PATH
    interface_name = constants.ENTITLEMENT_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(EntitlementDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetStatus(self, on_date, sender=None):
        """
        Get status of entitlements
        :param on_date: Date
        :param sender: Not used argument
        :return: String with JSON dump
        """
        try:
            on_date = dbus_utils.dbus_to_python(on_date)
            if on_date == "":
                on_date = None
            else:
                on_date = self._parse_date(on_date)

            # get_status doesn't need a Candlepin connection
            status = EntitlementService(None).get_status(on_date)
        except Exception as e:
            log.exception(e)
            raise dbus.DBusException(str(e))

        return json.dumps(status)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='a{sv}a{sv}',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetPools(self, options, proxy_options, sender=None):
        """
        Try to get pools installed/available/consumed at this system
        :param options: D-Bus object storing options of query
        :param proxy_options: D-Bus object with proxy configuration
        :param sender: Not used argument
        :return: String with JSON dump
        """
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)

        on_date = options.setdefault('on_date', "")
        if on_date != "":
            options['on_date'] = self._parse_date(on_date)

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        pools = entitlement_service.get_pools(**options)
        return json.dumps(pools)

    def _parse_date(self, on_date):
        on_date = datetime.strptime(on_date, '%Y-%m-%d')
        if on_date.date() < datetime.now().date():
            raise dbus.DBusException("Past dates are not allowed")

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='a{sv}',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def RemoveAllPools(self, proxy_options, sender=None):
        """
        Try to remove all subscriptions from the system
        :param proxy_options: Settings of proxy
        :param sender: Not used argument
        :return: Json string containing response
        """
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        result = entitlement_service.remove_all_pools()
        return json.dumps(result)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='asa{sv}',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def RemovePoolsByIds(self, pool_ids, proxy_options, sender=None):
        """
        Try to remove subscription by pool_id
        :param pool_ids: List of pool IDs
        :param proxy_options: Settings of proxy
        :param sender: Not used argument
        :return: List of removed pools represented by serial numbers
        """
        pool_ids = dbus_utils.dbus_to_python(pool_ids)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        removed_pools, unremoved_pools, removed_serials = entitlement_service.remove_pools_by_ids(pool_ids)

        return json.dumps(removed_serials)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='asa{sv}',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def RemovePoolsBySerials(self, serials, proxy_options, sender=None):
        """
        Try to remove subscription by pool_id
        :param serials: List of serial numbers of subscriptions
        :param proxy_options: Settings of proxy
        :param sender: Not used argument
        :return: List of removed pools represented by serial numbers
        """
        serials = dbus_utils.dbus_to_python(serials)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        removed_serials, unremoved_serials = entitlement_service.remove_pools_by_serials(serials)

        return json.dumps(removed_serials)
