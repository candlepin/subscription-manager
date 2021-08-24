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

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.entitlement import EntitlementService

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import Locale


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
        in_signature='ss',
        out_signature='s'
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetStatus(self, on_date, locale, sender=None):
        """
        Get status of entitlements
        :param on_date: Date
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        :return: String with JSON dump
        """
        on_date = dbus_utils.dbus_to_python(on_date, expected_type=str)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        if on_date == "":
            on_date = None
        else:
            on_date = self._parse_date(on_date)
        Locale.set(locale)

        try:
            cp = self.build_uep(options={})
            status = EntitlementService(cp).get_status(on_date=on_date, force=True)
        except Exception as e:
            log.exception(e)
            raise dbus.DBusException(str(e))

        return json.dumps(status)

    @util.dbus_service_signal(
        constants.ENTITLEMENT_INTERFACE,
        signature=''
    )
    @util.dbus_handle_exceptions
    def EntitlementChanged(self):
        """
        Signal fired, when entitlement is created/deleted/changed
        :return: None
        """

        log.debug("D-Bus signal %s emitted" % constants.ENTITLEMENT_INTERFACE)
        return None

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='a{sv}a{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetPools(self, options, proxy_options, locale, sender=None):
        """
        Try to get pools installed/available/consumed at this system
        :param options: D-Bus object storing options of query
        :param proxy_options: D-Bus object with proxy configuration
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        :return: String with JSON dump
        """
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)

        on_date = options.setdefault('on_date', "")
        if on_date != "":
            options['on_date'] = self._parse_date(on_date)

        after_date = options.setdefault("after_date", "")
        if after_date != "":
            options["after_date"] = self._parse_date(after_date)

        future = options.setdefault("future", "")
        if future != "":
            options["future"] = future

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        pools = entitlement_service.get_pools(**options)
        return json.dumps(pools)

    @staticmethod
    def _parse_date(on_date):
        """
        Return new datetime parsed from date
        :param on_date: String representing date
        :return It returns datetime.datime structure representing date
        """
        try:
            on_date = EntitlementService.parse_date(on_date)
        except ValueError as err:
            raise dbus.DBusException(err)
        return on_date

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='a{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def RemoveAllEntitlements(self, proxy_options, locale, sender=None):
        """
        Try to remove all entitlements (subscriptions) from the system
        :param proxy_options: Settings of proxy
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        :return: Json string containing response
        """
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        cp = self.build_uep(proxy_options, proxy_only=True)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        entitlement_service = EntitlementService(cp)
        result = entitlement_service.remove_all_entitlements()
        return json.dumps(result)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='asa{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def RemoveEntitlementsByPoolIds(self, pool_ids, proxy_options, locale, sender=None):
        """
        Try to remove entitlements (subscriptions) by pool_ids
        :param pool_ids: List of pool IDs
        :param proxy_options: Settings of proxy
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        :return: Json string representing list of serial numbers
        """
        pool_ids = dbus_utils.dbus_to_python(pool_ids, expected_type=list)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        removed_pools, unremoved_pools, removed_serials = entitlement_service.remove_entilements_by_pool_ids(pool_ids)

        return json.dumps(removed_serials)

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature='asa{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def RemoveEntitlementsBySerials(self, serials, proxy_options, locale, sender=None):
        """
        Try to remove entitlements (subscriptions) by serials
        :param serials: List of serial numbers of subscriptions
        :param proxy_options: Settings of proxy
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        :return: Json string representing list of serial numbers
        """
        serials = dbus_utils.dbus_to_python(serials, expected_type=list)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)

        cp = self.build_uep(proxy_options, proxy_only=True)
        entitlement_service = EntitlementService(cp)
        removed_serials, unremoved_serials = entitlement_service.remove_entitlements_by_serials(serials)

        return json.dumps(removed_serials)

    @staticmethod
    def reload():
        entitlement_service = EntitlementService()
        # TODO: find better solution
        entitlement_service.identity.reload()
        entitlement_service.reload()
