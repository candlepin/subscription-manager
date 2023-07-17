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
from typing import TYPE_CHECKING

from subscription_manager import utils
from subscription_manager import injection as inj
from subscription_manager.injectioninit import init_dep_injection

from rhsmlib.dbus import constants, exceptions, util
from rhsmlib.services import config
import rhsm.config

if TYPE_CHECKING:
    from dbus.service import BusName
    from rhsm.connection import UEPConnection
    from subscription_manager.cp_provider import CPProvider
    from subscription_manager.identity import Identity

init_dep_injection()

log = logging.getLogger(__name__)


class BaseImplementation:
    """Core implementation for subscription-manager D-Bus API.

    This base class allows us to contain useful functions in one place, without
    having to duplicate the work. Individual D-Bus object implementations
    subclass this base.
    """

    def is_registered(self) -> bool:
        """Uses the Identity class to determine if the system is registered or not."""
        identity: Identity = inj.require(inj.IDENTITY)
        return identity.is_valid()

    def ensure_registered(self) -> None:
        """Raise a D-Bus exception if the system is not registered."""
        if not self.is_registered():
            raise dbus.DBusException(
                "This object requires the consumer to be registered before it can be used."
            )

    def _validate_only_proxy_options(self, proxy_options: dict) -> None:
        """Ensure that the dictionary only contains keys related to proxy configuration.

        :raises exceptions.Failed: Some key is not a proxy option.
        """
        for key in proxy_options.keys():
            if key not in ["proxy_hostname", "proxy_port", "proxy_user", "proxy_password", "no_proxy"]:
                raise exceptions.Failed(f"Error: {key} is not a valid proxy option")

    def build_uep(
        self, options: dict, proxy_only: bool = False, basic_auth_method: bool = False
    ) -> "UEPConnection":
        """Create a UEPConnection object.

        Takes connection options and returns appropriate connection object,
        depending on the system registration status and the options provided
        in the dictionary.
        """
        conf = config.Config(rhsm.config.get_config_parser())
        # Some commands/services only allow manipulation of the proxy information for a connection
        cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        if proxy_only:
            self._validate_only_proxy_options(options)

        connection_info = {}

        server_sec = conf["server"]
        connection_info["host"] = options.get("host", server_sec["hostname"])
        connection_info["ssl_port"] = options.get("port", server_sec.get_int("port"))
        connection_info["handler"] = options.get("handler", server_sec["prefix"])

        connection_info["proxy_hostname_arg"] = options.get("proxy_hostname", server_sec["proxy_hostname"])
        connection_info["proxy_port_arg"] = options.get("proxy_port", server_sec.get_int("proxy_port"))
        connection_info["proxy_user_arg"] = options.get("proxy_user", server_sec["proxy_user"])
        connection_info["proxy_password_arg"] = options.get("proxy_password", server_sec["proxy_password"])
        connection_info["no_proxy_arg"] = options.get("no_proxy", server_sec["no_proxy"])

        cp_provider.set_connection_info(**connection_info)
        cp_provider.set_correlation_id(utils.generate_correlation_id())

        if self.is_registered() and basic_auth_method is False:
            return cp_provider.get_consumer_auth_cp()
        elif "username" in options and "password" in options:
            cp_provider.set_user_pass(options["username"], options["password"])
            return cp_provider.get_basic_auth_cp()
        else:
            return cp_provider.get_no_auth_cp()


class BaseObject(dbus.service.Object):
    """Core implementation for subscription-manager D-Bus API.

    This base class provides a common way of publishing the individual D-Bus
    objects to the API. Individual D-Bus objects subclass this base.
    """

    # Name of the DBus interface provided by this object
    interface_name = constants.INTERFACE_BASE
    default_dbus_path = constants.ROOT_DBUS_PATH

    def __init__(self, conn=None, object_path: str = None, bus_name: "BusName" = None):
        if object_path is None:
            object_path = self.default_dbus_path
        super().__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.DBUS_PROPERTIES_INTERFACE,
        in_signature="s",
        out_signature="a{sv}",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetAll(self, _, sender=None):
        """Announce that our API does not have any properties/attributes.

        This is part of the specification:
        > If org.freedesktop.DBus.Properties.GetAll is called with a valid
        > interface name which contains no properties, an empty array should
        > be returned.
        https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties
        """
        return dbus.Dictionary({}, signature="sv")
