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
from typing import List

import dbus
import json
import logging

from rhsm.connection import UEPConnection
from subscription_manager import entcertlib
from subscription_manager.i18n import Locale

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.attach import AttachService

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.utils import is_simple_content_access

init_dep_injection()

log = logging.getLogger(__name__)


class AttachDBusImplementation(base_object.BaseImplementation):
    def auto_attach(self, service_level: str, proxy_options: dict) -> dict:
        self.ensure_registered()

        uep: UEPConnection = self.build_uep(proxy_options, proxy_only=True)

        # TODO Change log.info()
        #  to raise dbus.DBusException('Auto-attaching is not allowed in simple content access mode')
        #  in next minor subscription-manager release
        if is_simple_content_access(uep=uep):
            log.info(
                "Calling D-Bus method AutoAttach() is deprecated, when Simple Content Access mode "
                "is used and it will be not be supported in the next minor release of "
                "subscription-manager"
            )

        service = AttachService(uep)
        try:
            response: dict = service.attach_auto(service_level)
        except Exception as exc:
            log.exception(exc)
            raise dbus.DBusException(str(exc))

        # TODO This should probably be called only if something is actually attached
        entcertlib.EntCertActionInvoker().update()
        return response

    def pool_attach(self, pools: List[str], quantity: int, proxy_options: dict) -> List[dict]:
        self.ensure_registered()

        if quantity < 1:
            raise dbus.DBusException("Quantity must be a positive number.")

        uep: UEPConnection = self.build_uep(proxy_options, proxy_only=True)

        # TODO Change log.info()
        #  to raise dbus.DBusException('Auto-attaching is not allowed in simple content access mode')
        #  in next minor subscription-manager release
        if is_simple_content_access(uep=uep):
            log.info(
                "Calling D-Bus method AutoAttach() is deprecated, when Simple Content Access mode "
                "is used and it will be not be supported in the next minor release of "
                "subscription-manager"
            )

        service = AttachService(uep)
        try:
            results: List[dict] = []
            for pool in pools:
                response = service.attach_pool(pool, quantity)
                results.append(response)
        except Exception as exc:
            log.exception(exc)
            raise dbus.DBusException(str(exc))

        # TODO This should probably be called only if something is actually attached
        entcertlib.EntCertActionInvoker().update()
        return results


class AttachDBusObject(base_object.BaseObject):
    """
    A DBus object that interacts with subscription-manager to attach various
    subscriptions.  Results are either a JSON string or a list of JSON strings.
    We don't return the JSON in an actual dictionary because deeply nested structures
    are a nightmare in DBus land.  See https://stackoverflow.com/questions/31658423/
    """

    default_dbus_path = constants.ATTACH_DBUS_PATH
    interface_name = constants.ATTACH_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(AttachDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.impl = AttachDBusImplementation()

    @util.dbus_service_method(
        constants.ATTACH_INTERFACE,
        in_signature="sa{sv}s",
        out_signature="s",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def AutoAttach(self, service_level, proxy_options, locale, sender=None):
        service_level = dbus_utils.dbus_to_python(service_level, expected_type=str) or None
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        result: dict = self.impl.auto_attach(service_level, proxy_options)
        return json.dumps(result)

    @util.dbus_service_method(
        constants.ATTACH_INTERFACE,
        in_signature="asia{sv}s",
        out_signature="as",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def PoolAttach(self, pools, quantity, proxy_options, locale, sender=None):
        pools = dbus_utils.dbus_to_python(pools, expected_type=list)
        quantity = dbus_utils.dbus_to_python(quantity, expected_type=int)
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)

        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        result: List[dict] = self.impl.pool_attach(pools, quantity, proxy_options)
        return [json.dumps(item) for item in result]
