# Copyright (c) 2010 Red Hat, Inc.
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
import base64
import json
import logging
from typing import Optional, Dict

from subscription_manager.identity import ConsumerIdentity
from subscription_manager import utils

from rhsmlib.client_info import DBusSender

import rhsm.connection as connection

log = logging.getLogger(__name__)


class TokenAuthUnsupportedException(Exception):
    pass


class CPProvider:
    """
    CPProvider provides candlepin connections of varying authentication levels
    in order to avoid creating more than we need, and reuse the ones we have.

    Please try not to hold a self.cp or self.uep, instead the instance of CPProvider
    and use get_X_auth_cp() when a connection is needed.

    consumer_auth_cp: authenticates with consumer cert/key
    basic_auth_cp: also called admin_auth uses a username/password
    no_auth_cp: no authentication
    content_connection: ent cert based auth connection to cdn
    """

    consumer_auth_cp: Optional[connection.UEPConnection] = None
    basic_auth_cp: Optional[connection.UEPConnection] = None
    no_auth_cp: Optional[connection.UEPConnection] = None
    content_connection: Optional[connection.ContentConnection] = None
    keycloak_auth_cp: Optional[connection.UEPConnection] = None

    # Initialize with default connection info from the config file
    def __init__(self):
        # FIXME: This does not make much sense to call this method and then rewrite almost everything
        # with None
        self.set_connection_info()
        self.correlation_id: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.token: Optional[str] = None
        self.token_username: Optional[str] = None
        self.cdn_hostname: Optional[str] = None
        self.cdn_port: Optional[str] = None
        self.cert_file: str = ConsumerIdentity.certpath()
        self.key_file: str = ConsumerIdentity.keypath()
        self.server_hostname: Optional[str] = None
        self.server_port: Optional[int] = None
        self.server_prefix: Optional[str] = None
        self.proxy_hostname = None
        self.proxy_port: Optional[int] = None
        self.proxy_user: Optional[str] = None
        self.proxy_password: Optional[str] = None
        self.no_proxy: Optional[bool] = None

    # Reread the config file and prefer arguments over config values
    # then recreate connections
    def set_connection_info(
        self,
        host: Optional[str] = None,
        ssl_port: Optional[int] = None,
        handler: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        proxy_hostname_arg: Optional[str] = None,
        proxy_port_arg: Optional[int] = None,
        proxy_user_arg: Optional[str] = None,
        proxy_password_arg: Optional[str] = None,
        no_proxy_arg: Optional[bool] = None,
    ):
        self.cert_file = ConsumerIdentity.certpath()
        self.key_file = ConsumerIdentity.keypath()

        # only use what was passed in, let the lowest level deal with
        # no values and look elsewhere for them.
        self.server_hostname = host
        self.server_port = ssl_port
        self.server_prefix = handler
        self.proxy_hostname = proxy_hostname_arg
        self.proxy_port = proxy_port_arg
        self.proxy_user = proxy_user_arg
        self.proxy_password = proxy_password_arg
        self.no_proxy = no_proxy_arg
        self.clean()

    # Set username and password used for basic_auth without
    # modifying previously set options
    def set_user_pass(self, username: Optional[str] = None, password: Optional[str] = None) -> None:
        self.username = username
        self.password = password
        self.basic_auth_cp = None

    def _parse_token(self, token: str) -> Dict:
        # FIXME: make this more reliable
        _header, payload, _signature = token.split(".")
        payload += "=" * (4 - (len(payload) % 4))  # pad to the appropriate length
        return json.loads(base64.b64decode(payload))

    def set_token(self, token: Optional[str] = None) -> None:
        self.token = token
        # FIXME: make this more reliable
        if token:
            self.token_username = self._parse_token(token)["preferred_username"]
        else:
            self.token_username = None
        self.keycloak_auth_cp = None

    # set up info for the connection to the cdn for finding release versions
    def set_content_connection_info(self, cdn_hostname: Optional[str] = None, cdn_port: Optional[int] = None):
        self.cdn_hostname = cdn_hostname
        self.cdn_port = cdn_port
        self.content_connection = None

    def set_correlation_id(self, correlation_id: str):
        self.correlation_id = correlation_id

    # Force connections to be re-initialized
    def clean(self):
        self.consumer_auth_cp = None
        self.basic_auth_cp = None
        self.no_auth_cp = None
        self.keycloak_auth_cp = None

    @staticmethod
    def get_client_version() -> str:
        """
        Try to get version of subscription manager
        """
        return " subscription-manager/%s" % utils.get_client_versions()["subscription-manager"]

    @staticmethod
    def get_dbus_sender() -> str:
        """
        Try to get D-Bus sender
        """
        dbus_sender = DBusSender()
        if dbus_sender.cmd_line is not None:
            return " dbus_sender=%s" % dbus_sender.cmd_line
        else:
            return ""

    def close_all_connections(self) -> None:
        """
        Try to close all connections to candlepin server, CDN, etc.
        """
        if self.consumer_auth_cp is not None:
            log.debug("Closing auth/consumer connection...")
            self.consumer_auth_cp.conn.close_connection()
        if self.no_auth_cp is not None:
            log.debug("Closing no auth connection...")
            self.no_auth_cp.conn.close_connection()
        if self.basic_auth_cp is not None:
            log.debug("Closing auth/basic connection...")
            self.basic_auth_cp.conn.close_connection()
        if self.keycloak_auth_cp is not None:
            log.debug("Closing auth/keycloak connection...")
            self.keycloak_auth_cp.conn.close_connection()

    def get_consumer_auth_cp(self) -> connection.UEPConnection:
        if not self.consumer_auth_cp:
            self.consumer_auth_cp = connection.UEPConnection(
                host=self.server_hostname,
                ssl_port=self.server_port,
                handler=self.server_prefix,
                proxy_hostname=self.proxy_hostname,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
                cert_file=self.cert_file,
                key_file=self.key_file,
                correlation_id=self.correlation_id,
                no_proxy=self.no_proxy,
                client_version=self.get_client_version(),
                dbus_sender=self.get_dbus_sender(),
                auth_type=connection.ConnectionType.CONSUMER_CERT_AUTH,
            )
        return self.consumer_auth_cp

    def get_keycloak_auth_cp(self, token) -> connection.UEPConnection:
        if self.keycloak_auth_cp:
            return self.keycloak_auth_cp

        uep: connection.UEPConnection = self.get_no_auth_cp()

        if not uep.has_capability("keycloak_auth"):
            raise TokenAuthUnsupportedException

        # FIXME: make this more reliable
        token_type: str = self._parse_token(token)["typ"]
        if token_type.lower() == "bearer":
            access_token = token
        else:
            status: Dict = uep.getStatus()
            auth_url = status["keycloakAuthUrl"]
            realm = status["keycloakRealm"]
            resource = status["keycloakResource"]
            keycloak_instance = connection.KeycloakConnection(realm, auth_url, resource)

            access_token: str = keycloak_instance.get_access_token_through_refresh(token)

        self.set_token(access_token)

        self.keycloak_auth_cp = connection.UEPConnection(
            host=self.server_hostname,
            ssl_port=self.server_port,
            handler=self.server_prefix,
            proxy_hostname=self.proxy_hostname,
            proxy_port=self.proxy_port,
            proxy_user=self.proxy_user,
            proxy_password=self.proxy_password,
            username=None,
            password=None,
            correlation_id=self.correlation_id,
            no_proxy=self.no_proxy,
            token=self.token,
            client_version=self.get_client_version(),
            dbus_sender=self.get_dbus_sender(),
            auth_type=connection.ConnectionType.KEYCLOAK_AUTH,
        )
        return self.keycloak_auth_cp

    def get_basic_auth_cp(self) -> connection.UEPConnection:
        if not self.basic_auth_cp:
            self.basic_auth_cp = connection.UEPConnection(
                host=self.server_hostname,
                ssl_port=self.server_port,
                handler=self.server_prefix,
                proxy_hostname=self.proxy_hostname,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
                username=self.username,
                password=self.password,
                correlation_id=self.correlation_id,
                no_proxy=self.no_proxy,
                client_version=self.get_client_version(),
                dbus_sender=self.get_dbus_sender(),
                auth_type=connection.ConnectionType.BASIC_AUTH,
            )
        return self.basic_auth_cp

    def get_no_auth_cp(self) -> connection.UEPConnection:
        if not self.no_auth_cp:
            self.no_auth_cp = connection.UEPConnection(
                host=self.server_hostname,
                ssl_port=self.server_port,
                handler=self.server_prefix,
                proxy_hostname=self.proxy_hostname,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
                correlation_id=self.correlation_id,
                no_proxy=self.no_proxy,
                client_version=self.get_client_version(),
                dbus_sender=self.get_dbus_sender(),
                auth_type=connection.ConnectionType.NO_AUTH,
            )
        return self.no_auth_cp

    def get_content_connection(self) -> connection.ContentConnection:
        if not self.content_connection:
            self.content_connection = connection.ContentConnection(
                host=self.cdn_hostname,
                ssl_port=self.cdn_port,
                proxy_hostname=self.proxy_hostname,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
                no_proxy=self.no_proxy,
                client_version=self.get_client_version(),
                dbus_sender=self.get_dbus_sender(),
            )
        return self.content_connection
