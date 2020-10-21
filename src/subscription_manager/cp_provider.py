from __future__ import print_function, division, absolute_import

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

from subscription_manager.identity import ConsumerIdentity
from subscription_manager import utils
import rhsm.connection as connection


class TokenAuthUnsupportedException(Exception):
    pass


class CPProvider(object):
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

    consumer_auth_cp = None
    basic_auth_cp = None
    no_auth_cp = None
    content_connection = None
    keycloak_auth_cp = None

    # Initialize with default connection info from the config file
    def __init__(self):
        self.correlation_id = None
        self.username = None
        self.password = None
        self.token = None
        self.token_username = None
        self.cdn_hostname = None
        self.cdn_port = None
        self.cert_file = ConsumerIdentity.certpath()
        self.key_file = ConsumerIdentity.keypath()
        self.server_hostname = None
        self.server_port = None
        self.server_prefix = None
        self.proxy_hostname = None
        self.proxy_port = None
        self.proxy_user = None
        self.proxy_password = None
        self.no_proxy = None
        self.restlib_class = None

    # Reread the config file and prefer arguments over config values
    # then recreate connections
    def set_connection_info(self,
                host=None,
                ssl_port=None,
                handler=None,
                cert_file=None,
                key_file=None,
                proxy_hostname_arg=None,
                proxy_port_arg=None,
                proxy_user_arg=None,
                proxy_password_arg=None,
                no_proxy_arg=None,
                restlib_class=connection.Restlib):
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
        self.restlib_class = restlib_class
        self.clean()

    # Set username and password used for basic_auth without
    # modifying previously set options
    def set_user_pass(self, username=None, password=None):
        self.username = username
        self.password = password
        self.basic_auth_cp = None

    def _parse_token(self, token):
        _header, payload, _signature = token.split(".")
        payload += "=" * (4 - (len(payload) % 4))  # pad to the appropriate length
        return json.loads(base64.b64decode(payload))

    def set_token(self, token=None):
        self.token = token
        if token:
            self.token_username = self._parse_token(token)['preferred_username']
        else:
            self.token_username = None
        self.keycloak_auth_cp = None

    # set up info for the connection to the cdn for finding release versions
    def set_content_connection_info(self, cdn_hostname=None, cdn_port=None):
        self.cdn_hostname = cdn_hostname
        self.cdn_port = cdn_port
        self.content_connection = None

    def set_correlation_id(self, correlation_id):
        self.correlation_id = correlation_id

    # Force connections to be re-initialized
    def clean(self):
        self.consumer_auth_cp = None
        self.basic_auth_cp = None
        self.no_auth_cp = None
        self.keycloak_auth_cp = None

    def get_client_version(self):
        """
        Try to get version of subscription manager
        :return: string with version of subscription-manager
        """
        return " subscription-manager/%s" % utils.get_client_versions()['subscription-manager']

    def get_consumer_auth_cp(self):
        if not self.consumer_auth_cp:
            self.consumer_auth_cp = connection.UEPConnection(
                    host=self.server_hostname,
                    ssl_port=self.server_port,
                    handler=self.server_prefix,
                    proxy_hostname=self.proxy_hostname,
                    proxy_port=self.proxy_port,
                    proxy_user=self.proxy_user,
                    proxy_password=self.proxy_password,
                    cert_file=self.cert_file, key_file=self.key_file,
                    correlation_id=self.correlation_id,
                    no_proxy=self.no_proxy,
                    restlib_class=self.restlib_class,
                    client_version=self.get_client_version()
            )
        return self.consumer_auth_cp

    def get_keycloak_auth_cp(self, token):
        if self.keycloak_auth_cp:
            return self.keycloak_auth_cp

        uep = self.get_no_auth_cp()

        if not uep.has_capability('keycloak_auth'):
            raise TokenAuthUnsupportedException

        # check type
        token_type = self._parse_token(token)['typ']
        if token_type.lower() == 'bearer':
            access_token = token
        else:
            status = uep.getStatus()
            auth_url = status['keycloakAuthUrl']
            realm = status['keycloakRealm']
            resource = status['keycloakResource']
            keycloak_instance = connection.KeycloakConnection(realm, auth_url, resource)

            access_token = keycloak_instance.get_access_token_through_refresh(token)

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
                restlib_class=self.restlib_class,
                token=self.token,
                client_version=self.get_client_version()
        )
        return self.keycloak_auth_cp

    def get_basic_auth_cp(self):
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
                    restlib_class=self.restlib_class,
                    client_version=self.get_client_version()
            )
        return self.basic_auth_cp

    def get_no_auth_cp(self):
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
                    restlib_class=self.restlib_class,
                    client_version=self.get_client_version()
            )
        return self.no_auth_cp

    def get_content_connection(self):
        if not self.content_connection:
            self.content_connection = connection.ContentConnection(
                host=self.cdn_hostname,
                ssl_port=self.cdn_port,
                proxy_hostname=self.proxy_hostname,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
                no_proxy=self.no_proxy,
                client_version=self.get_client_version()
            )
        return self.content_connection
