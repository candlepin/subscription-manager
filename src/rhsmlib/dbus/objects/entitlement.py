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
import datetime
from typing import Union

import dbus
import json
import logging

from rhsm.connection import UEPConnection
from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.entitlement import EntitlementService

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import Locale


init_dep_injection()

log = logging.getLogger(__name__)


class EntitlementDBusImplementation(base_object.BaseImplementation):
    def get_status(self, on_date: str) -> dict:
        """Get status of entitlements."""
        on_date: Union[str, datetime.datetime] = None if on_date == "" else self._parse_date(on_date)

        uep: UEPConnection = self.build_uep(options={})
        service = EntitlementService(uep)
        try:
            status: dict = service.get_status(on_date=on_date, force=True)
        except Exception as exc:
            log.exception(exc)
            raise dbus.DBusException(str(exc))

        return status

    def get_pools(self, options: dict, proxy_options: dict) -> dict:
        """Get pools that are installed, available and consumed by this system."""
        on_date: str = options.setdefault("on_date", "")
        if on_date != "":
            options["on_date"] = self._parse_date(on_date)

        after_date: str = options.setdefault("after_date", "")
        if after_date != "":
            options["after_date"] = self._parse_date(after_date)

        future: str = options.setdefault("future", "")
        if future != "":
            options["future"] = future

        uep: UEPConnection = self.build_uep(proxy_options, proxy_only=True)
        service = EntitlementService(uep)
        pools: dict = service.get_pools(**options)

        return pools

    def _parse_date(self, date_string: str) -> datetime.datetime:
        """
        Return new datetime parsed from date.

        This is a wrapper around EntitlementService.parse_date that raises
        a D-Bus exception instead of ValueError.

        :param date_string: String representing date
        :return: datetime.datetime structure representing date
        :raises dbus.DBusException: String cannot be converted
        """
        try:
            date = EntitlementService.parse_date(date_string)
        except ValueError as err:
            raise dbus.DBusException(err)
        return date


class EntitlementDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to list, get status
    and remove pools.
    """

    default_dbus_path = constants.ENTITLEMENT_DBUS_PATH
    interface_name = constants.ENTITLEMENT_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(EntitlementDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.impl = EntitlementDBusImplementation()

    @util.dbus_service_method(
        constants.ENTITLEMENT_INTERFACE,
        in_signature="ss",
        out_signature="s",
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

        Locale.set(locale)

        status: dict = self.impl.get_status(on_date)
        return json.dumps(status)

    @util.dbus_service_signal(
        constants.ENTITLEMENT_INTERFACE,
        signature="",
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
        in_signature="a{sv}a{sv}s",
        out_signature="s",
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

        pools: dict = self.impl.get_pools(options, proxy_options)
        return json.dumps(pools)

    @staticmethod
    def reload():
        entitlement_service = EntitlementService()
        # TODO: find better solution
        entitlement_service.identity.reload()
        entitlement_service.reload()
