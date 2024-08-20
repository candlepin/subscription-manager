# A proxy interface to initiate and interact with candlepin.
#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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
from rhsm import certificate
import datetime
import dateutil.parser
import locale
import logging
import os
import socket
import sys
import time
import traceback
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from pathlib import Path
import re
import enum

from email.utils import format_datetime

from rhsm.https import httplib, ssl

from urllib.request import proxy_bypass
from urllib.parse import urlencode, urlparse, quote, quote_plus

from rhsm.config import get_config_parser
from rhsm import ourjson as json
from rhsm import utils

try:
    import subscription_manager.version

    subman_version = subscription_manager.version.pkg_version
except ImportError:
    subman_version = "unknown"

try:
    from subscription_manager.i18n import ugettext as _
except ImportError:

    def _(message: str):
        return message


config = get_config_parser()
MULTI_ENV = "multi_environment"

REUSE_CONNECTION = True


def safe_int(value: Any, safe_value: Any = None) -> Union[int, None, Any]:
    try:
        return int(value)
    except Exception:
        return safe_value


def normalized_host(host: str) -> str:
    """
    When you want to use IPv6 address and port in e.g. HTTP header, then you cannot use following
    notation common for IPv4 (147.230.16.1:53). You have to use following notation for IPv6
    [2001:718:1c01:16::aa]:53.
    :param host: hostname or IPv4 or IPv6 address
    :return: When host is IPv6 address, then it encapsulated in [] brackets
    """
    if ":" in host:
        return "[%s]" % host
    else:
        return host


def get_time_drift(timestamp: str) -> datetime.timedelta:
    """Get a difference between server and local clock.

    :param timestamp: A timezone-unaware timestamp in RFC 1123 format.
    :returns: Absolute difference between server and local time.
    """
    # RFC 1123: 'Fri, 12 Jan 2024 08:10:46 GMT'
    timestamp: datetime.datetime = dateutil.parser.parse(timestamp)
    if timestamp.tzinfo.tzname(timestamp) != "UTC":
        log.warning(f"Expected UTC timestamp, got '{timestamp}', drift check may be off.")
    # dateutil has its own tzinfo object representing UTC
    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    drift: datetime.timedelta = abs(timestamp - now)
    return drift


class NullHandler(logging.Handler):
    def emit(self, record: Any) -> None:
        pass


h = NullHandler()
logging.getLogger("rhsm").addHandler(h)

log = logging.getLogger(__name__)


class NoValidEntitlement(Exception):
    """Throw when there is no valid entitlement certificate for accessing CDN"""

    pass


class ConnectionException(Exception):
    pass


class ProxyException(Exception):
    """
    Thrown in case of errors related to the proxy server.
    """

    def __init__(self, hostname: str = None, port: int = None, exc: Optional[Exception] = None):
        self._hostname = hostname
        self.port = port
        self.exc = exc

    @property
    def hostname(self) -> str:
        return normalized_host(self._hostname)

    @property
    def address(self) -> str:
        return f"{self.hostname}:{self.port}"

    def __str__(self) -> str:
        addr = self.address
        err = f"Proxy error at {addr}"
        if self.exc is not None:
            err = f"{err}: {self.exc}"
        return err


class ConnectionSetupException(ConnectionException):
    pass


class BadCertificateException(ConnectionException):
    """Thrown when an error parsing a certificate is encountered."""

    def __init__(self, cert_path: str, ssl_exc: ssl.SSLError) -> None:
        """Pass the full path to the bad certificate."""
        self.cert_path = cert_path
        self.ssl_exc = ssl_exc

    def __str__(self) -> str:
        return "Bad certificate at %s" % self.cert_path


class ConnectionOSErrorException(ConnectionException):
    """
    Thrown in case of OSError during the connect() of HTTPSConnection,
    in case the OSError does not come from a syscall failure (and thus
    its 'errno' attribute is None.
    """

    def __init__(self, host: str, port: int, handler: str, exc: OSError):
        self._host = host
        self.port = port
        self.handler = handler
        self.exc = exc

    @property
    def host(self) -> str:
        return normalized_host(self._host)


class ConnectionType(enum.Enum):
    """
    Enumerate of allowed connection types
    """

    # Connection uses no authentication
    NO_AUTH = enum.auto()

    # Connection uses basic authentication (username and password)
    BASIC_AUTH = enum.auto()

    # Connection uses consumer certificate for authentication
    CONSUMER_CERT_AUTH = enum.auto()

    # Connection uses Keycloak token
    KEYCLOAK_AUTH = enum.auto()


class BaseConnection:
    def __init__(
        self,
        host: Optional[str] = None,
        ssl_port: Optional[int] = None,
        handler: Optional[str] = None,
        ca_dir: Optional[str] = None,
        insecure: Optional[bool] = None,
        proxy_hostname: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_user: Optional[str] = None,
        proxy_password: Optional[str] = None,
        no_proxy: Optional[bool] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        cert_dir: Optional[str] = None,
        token: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        timeout: Optional[int] = None,
        auth_type: Optional[ConnectionType] = None,
        **kwargs,
    ) -> None:
        self.host = host or config.get("server", "hostname")
        self.handler = handler or config.get("server", "prefix")
        self.ssl_port = ssl_port or safe_int(config.get("server", "port"))
        self.timeout = timeout or safe_int(config.get("server", "server_timeout"))

        # allow specifying no_proxy via api or config
        no_proxy_override = no_proxy or config.get("server", "no_proxy")
        if no_proxy_override:
            os.environ["no_proxy"] = no_proxy_override

        utils.fix_no_proxy()
        log.debug("Environment variable NO_PROXY=%s will be used" % no_proxy_override)

        # honor no_proxy environment variable
        if proxy_bypass(self.host):
            self.proxy_hostname = None
            self.proxy_port = None
            self.proxy_user = None
            self.proxy_password = None
        else:
            info = utils.get_env_proxy_info()

            if proxy_hostname is not None:
                self.proxy_hostname = proxy_hostname
            else:
                self.proxy_hostname = config.get("server", "proxy_hostname") or info["proxy_hostname"]
            if proxy_port is not None:
                self.proxy_port = proxy_port
            else:
                self.proxy_port = config.get("server", "proxy_port") or info["proxy_port"]
            if proxy_user is not None:
                self.proxy_user = proxy_user
            else:
                self.proxy_user = config.get("server", "proxy_user") or info["proxy_username"]
            if proxy_password is not None:
                self.proxy_password = proxy_password
            else:
                self.proxy_password = config.get("server", "proxy_password") or info["proxy_password"]

        self.cert_file = cert_file
        self.key_file = key_file
        self.username = username
        self.password = password
        self.token = token
        self.auth_type = auth_type

        self.ca_dir = ca_dir or config.get("rhsm", "ca_cert_dir")

        self.insecure = insecure
        if insecure is None:
            self.insecure = False
            config_insecure = safe_int(config.get("server", "insecure"))
            if config_insecure:
                self.insecure = True

        using_basic_auth = False
        using_id_cert_auth = False
        using_ent_cert_auth = False
        using_keycloak_auth = False

        if username and password:
            using_basic_auth = True
        elif cert_file and key_file:
            using_id_cert_auth = True
        elif cert_dir:
            using_ent_cert_auth = True
        elif token:
            using_keycloak_auth = True

        if (
            len(
                [
                    value
                    for value in (
                        using_basic_auth,
                        using_id_cert_auth,
                        using_keycloak_auth,
                        using_ent_cert_auth,
                    )
                    if value
                ]
            )
            > 1
        ):
            raise Exception("Cannot specify multiple auth types")

        proxy_description = None
        if self.proxy_hostname and self.proxy_port:
            proxy_description = "http_proxy=%s:%s " % (
                normalized_host(self.proxy_hostname),
                safe_int(self.proxy_port),
            )
        # initialize connection
        self.conn: BaseRestLib = BaseRestLib(
            self.host,
            self.ssl_port,
            self.handler,
            username=self.username,
            password=self.password,
            token=self.token,
            cert_file=self.cert_file,
            key_file=self.key_file,
            proxy_hostname=self.proxy_hostname,
            proxy_port=self.proxy_port,
            proxy_user=self.proxy_user,
            proxy_password=self.proxy_password,
            ca_dir=self.ca_dir,
            insecure=self.insecure,
            cert_dir=cert_dir,
            timeout=self.timeout,
            correlation_id=correlation_id,
            user_agent=user_agent,
            auth_type=auth_type,
        )

        if using_keycloak_auth:
            auth_description = "auth=bearer %s" % token
        elif using_basic_auth:
            auth_description = "auth=basic username=%s" % username
        elif using_id_cert_auth:
            auth_description = "auth=identity_cert ca_dir=%s insecure=%s" % (self.ca_dir, self.insecure)
        elif using_ent_cert_auth:
            auth_description = "auth=entitlement_certs"
        else:
            auth_description = "auth=none"

        self.resources = None
        self.capabilities = None
        connection_description = ""
        if proxy_description:
            connection_description += proxy_description
        connection_description += "host=%s port=%s handler=%s %s" % (
            normalized_host(self.host),
            safe_int(self.ssl_port),
            self.handler,
            auth_description,
        )
        log.debug("Connection built: %s", connection_description)


class TokenAuthException(Exception):
    pass


class KeycloakConnection(BaseConnection):
    """
    Keycloak Based Authentication
    """

    def __init__(self, realm: Any, auth_url: str, resource: Any, **kwargs) -> None:
        host = urlparse(auth_url).hostname or ""
        handler = urlparse(auth_url).path
        ssl_port = urlparse(auth_url).port or 443
        super(KeycloakConnection, self).__init__(host=host, ssl_port=ssl_port, handler=handler, **kwargs)
        self.realm = realm
        self.resource = resource

    def get_access_token_through_refresh(self, refreshtoken: Any) -> Optional[Any]:
        # Get access token in exchange for refresh token
        method = "/realms/" + self.realm + "/protocol/openid-connect/token"
        params = {"client_id": self.resource, "grant_type": "refresh_token", "refresh_token": refreshtoken}
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            data = self.conn.request_post(method, params, headers)
            return data["access_token"]
        except RestlibException as e:
            if e.code == 400:
                raise TokenAuthException(e.msg)
            raise


class RestlibException(ConnectionException):
    """
    Raised when a response with a valid json body is received along with a status code
    that is not in [200, 202, 204, 410, 429]
    See BaseRestLib.validateResult to see when this and other exceptions are raised.
    """

    def __init__(self, code: int, msg: str = None, headers: dict = None) -> None:
        self.code = code
        self.msg = msg or ""
        self.headers = headers or {}

    @property
    def title(self) -> str:
        return httplib.responses.get(self.code, "Unknown")

    def __str__(self) -> str:
        return f"HTTP error ({self.code} - {self.title}): {self.msg}"


class GoneException(RestlibException):
    """
    GoneException is used to detect when a consumer has been deleted on the candlepin side.

    A client handling a GoneException should verify that GoneException.deleted_id
    matches the consumer uuid before taking any action (like deleting the consumer
    cert from disk).

    This is to prevent an errant 410 response from candlepin (or a reverse_proxy in
    front of it, or it's app server, or an injected response) from causing
    accidental consumer cert deletion.
    """

    def __init__(self, code: int, msg: str, deleted_id: Any):
        # Exception doesn't inherit from object on el5 python version
        RestlibException.__init__(self, code, msg)
        self.deleted_id = deleted_id


class UnknownContentException(ConnectionException):
    """
    Thrown when the response of a request has no valid json content
    and the http status code is anything other than the following:
    [200, 202, 204, 401, 403, 410, 429, 500, 502, 503, 504]
    """

    def __init__(self, code: int, content_type: Optional[str] = None, content: Optional[str] = None) -> None:
        self.code = code
        self.content_type = content_type
        self.content = content

    @property
    def title(self) -> str:
        return httplib.responses.get(self.code, "Unknown")

    def __str__(self) -> str:
        s = f"Unknown content error (HTTP {self.code} - {self.title}"
        if self.content_type is not None:
            s += f", type {self.content_type}"
        if self.content is not None:
            s += f", len {len(self.content)}"
        s += ")"
        return s


class RemoteServerException(ConnectionException):
    """
    Thrown when the response to a request has no valid json content and
    one of these http status codes: [404, 410, 500, 502, 503, 504]
    """

    def __init__(self, code: int, request_type: str = None, handler: str = None) -> None:
        self.code = code
        self.request_type = request_type
        self.handler = handler

    def __str__(self) -> str:
        if self.request_type and self.handler:
            return "Server error attempting a %s to %s returned status %s" % (
                self.request_type,
                self.handler,
                self.code,
            )
        return "Server returned %s" % self.code


class AuthenticationException(RemoteServerException):
    prefix = "Authentication error"

    def __str__(self) -> str:
        buf = super(AuthenticationException, self).__str__()
        buf += "\n"
        buf += "%s: Invalid credentials for request." % self.prefix
        return buf


class RateLimitExceededException(RestlibException):
    """
    Thrown in response to a http code 429.
    This means that too many requests have been made in a given time period.
    The retry_after attribute is an int of seconds to retry the request after.
    The retry_after attribute may not be included in the response.
    """

    def __init__(self, code: int, msg: str = None, headers: str = None) -> None:
        super(RateLimitExceededException, self).__init__(code, msg)
        self.headers = headers or {}
        self.retry_after = safe_int(self.headers.get("retry-after"))
        self.msg = msg or "Access rate limit exceeded"
        if self.retry_after is not None:
            self.msg += ", retry access after: %s seconds." % self.retry_after


class UnauthorizedException(AuthenticationException):
    """
    Thrown in response to http status code 401 with no valid json content
    """

    prefix = "Unauthorized"


class ForbiddenException(AuthenticationException):
    """
    Thrown in response to http status code 403 with no valid json content
    """

    prefix = "Forbidden"


class ExpiredIdentityCertException(ConnectionException):
    pass


def _encode_auth(username, password):
    encoded = base64.b64encode(":".join((username, password)).encode("utf-8")).decode("utf-8")
    return "Basic %s" % encoded


# FIXME: this is terrible, we need to refactor
# Restlib to be Restlib based on a https client class
class ContentConnection(BaseConnection):
    def __init__(self, cert_dir: str = None, **kwargs) -> None:
        log.debug("ContentConnection")
        user_agent = "RHSM-content/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)
        if "client_version" in kwargs:
            user_agent += kwargs["client_version"]
        cert_dir = cert_dir or "/etc/pki/entitlement"
        super(ContentConnection, self).__init__(
            handler="/", cert_dir=cert_dir, user_agent=user_agent, **kwargs
        )

    def get_versions(self, path: str, cert_key_pairs: Iterable[Tuple[str, str]] = None) -> Union[dict, None]:
        """
        Get list of available release versions from the given path
        :param path: path, where is simple text file containing supported release versions
        :param cert_key_pairs: optional argument including list of supported cert and keys
            to reduce number of failed http requests.
        :return:
        """
        handler = "%s/%s" % (self.handler, path)
        result = self.conn.request_get(handler, cert_key_pairs=cert_key_pairs)

        return result

    def _get_versions_for_product(self, product_id) -> None:
        pass


def _get_locale() -> Union[None, str]:
    new_locale = None
    try:
        new_locale = locale.getlocale()
    except (locale.Error, ValueError):
        try:
            new_locale = locale.getdefaultlocale()
        except locale.Error:
            pass
        except ValueError:
            pass

    if new_locale and new_locale != (None, None):
        return new_locale[0]

    return None


class BaseRestLib:
    """
    A low-level wrapper around httplib
    to make rest calls easy and expose the details of
    responses
    """

    __conn = None

    ALPHA: float = 0.9

    # Default value of timeout. This value is set according observed timeout
    # on typical installations of candlepin server (hosted 75 seconds,
    # tomcat 60 seconds)
    KEEP_ALIVE_TIMEOUT: int = 50

    def __init__(
        self,
        host: str,
        ssl_port: int,
        apihandler: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        proxy_hostname: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_user: Optional[str] = None,
        proxy_password: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        cert_dir: Optional[str] = None,
        ca_dir: Optional[str] = None,
        insecure: Optional[bool] = False,
        timeout: Optional[int] = None,
        correlation_id: Optional[str] = None,
        token: Optional[str] = None,
        user_agent: Optional[str] = None,
        auth_type: Optional[ConnectionType] = None,
    ) -> None:
        log.debug("Creating new BaseRestLib instance")
        self.host = host
        self.ssl_port = ssl_port
        self.apihandler = apihandler

        # Default, updated by UepConnection
        self.user_agent = user_agent or "python-rhsm-user-agent"

        self.headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "x-subscription-manager-version": subman_version,
        }

        if correlation_id:
            self.headers["X-Correlation-ID"] = correlation_id

        self.cert_file = cert_file
        self.key_file = key_file
        self.cert_dir = cert_dir
        self.ca_dir = ca_dir
        self.insecure = insecure
        self.username = username
        self.password = password
        self.timeout = timeout
        self.proxy_hostname = proxy_hostname
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password
        self.smoothed_rt = None
        self.token = token
        self.auth_type = auth_type
        # We set this to None, because we don't know the truth unless we get
        # first response from the server using cert/key connection
        self.is_consumer_cert_key_valid = None

        # Setup basic authentication if specified:
        if username and password:
            self.headers["Authorization"] = _encode_auth(username, password)
        elif token:
            self.headers["Authorization"] = "Bearer " + token

    def close_connection(self) -> None:
        """
        Try to close connection to server
        :return: None
        """
        if self.__conn is not None:
            # Do proper TLS shutdown handshake (TLS tear down) first
            if self.__conn.sock is not None:
                log.debug(f"Closing HTTPS connection {self.__conn.sock}")
                try:
                    self.__conn.sock.unwrap()
                except ssl.SSLError as err:
                    log.debug(f"Unable to close TLS connection properly: {err}")
                else:
                    log.debug("TLS connection closed")
            # Then it is possible to close TCP connection
            self.__conn.close()
        self.__conn = None

    def _get_cert_key_list(self) -> List[Tuple[str, str]]:
        """
        Create list of cert-key pairs to be used with the connection
        """

        cert_key_pairs = []

        if self.cert_dir is None:
            return [(self.cert_file, self.key_file)]

        for cert_file in os.listdir(self.cert_dir):
            if cert_file.endswith(".pem") and not cert_file.endswith("-key.pem"):
                cert_path = os.path.join(self.cert_dir, cert_file)
                key_path = os.path.join(self.cert_dir, "%s-key.pem" % cert_file.split(".", 1)[0])
                cert_key_pairs.append((cert_path, key_path))

        return cert_key_pairs

    def _load_ca_certificates(self, context: ssl.SSLContext) -> None:
        """
        Tries to load CA certificates to SSL context
        :param context: SSL context
        :return: None
        """
        if not os.path.isdir(self.ca_dir):
            log.warning('Directory "%s" with CA certificates is missing' % self.ca_dir)
            return None

        loaded_ca_certs = []
        cert_path = ""
        try:
            for cert_file in os.listdir(self.ca_dir):
                if cert_file.endswith(".pem"):
                    cert_path = os.path.join(self.ca_dir, cert_file)
                    context.load_verify_locations(cert_path)
                    loaded_ca_certs.append(cert_file)
        except ssl.SSLError as exc:
            raise BadCertificateException(cert_path, exc)
        except OSError as e:
            raise ConnectionSetupException(e.strerror)

        if loaded_ca_certs:
            log.debug("Loaded CA certificates from %s: %s" % (self.ca_dir, ", ".join(loaded_ca_certs)))
        else:
            log.warning("Unable to load any CA certificate from: %s" % self.ca_dir)

    def _create_connection(self, cert_file: str = None, key_file: str = None) -> httplib.HTTPSConnection:
        """
        This method tries to return existing connection, when connection exists and limit of connection
        has not been reached (timeout, max number of requests). When no connection exists, then this
        method creates new TCP and TLS connection.
        """

        if self.__conn is not None:
            # Check if it is still possible to use existing connection
            now = time.time()
            if now - self.__conn.last_request_time > self.__conn.keep_alive_timeout:
                log.debug(f"Connection timeout {self.__conn.keep_alive_timeout}. Closing connection...")
                self.close_connection()
            elif (
                self.__conn.max_requests_num is not None
                and self.__conn.requests_num > self.__conn.max_requests_num
            ):
                log.debug(
                    f"Maximal number of requests ({self.__conn.max_requests_num}) reached. "
                    "Closing connection..."
                )
                self.close_connection()
            else:
                log.debug("Reusing connection: %s", self.__conn.sock)
                return self.__conn

        log.debug("Creating new connection")

        # Select the highest TLS version supported by both the client and the server.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        if self.insecure:
            # Allow clients to connect to servers with missing or invalid certificates.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context.verify_mode = ssl.CERT_REQUIRED
            if self.ca_dir is not None:
                self._load_ca_certificates(context)
        if cert_file and os.path.exists(cert_file):
            context.load_cert_chain(cert_file, keyfile=key_file)

        if self.proxy_hostname and self.proxy_port:
            log.debug(
                "Using proxy: %s:%s" % (normalized_host(self.proxy_hostname), safe_int(self.proxy_port))
            )
            proxy_headers = {
                "User-Agent": self.user_agent,
                "Host": "%s:%s" % (normalized_host(self.host), safe_int(self.ssl_port)),
            }
            if self.proxy_user and self.proxy_password:
                proxy_headers["Proxy-Authorization"] = _encode_auth(self.proxy_user, self.proxy_password)

            # Note: we use only HTTPS for connection with proxy server, and we ignore proxy_scheme setting
            # from rhsm.conf here. The proxy_scheme is used only for generating redhat.repo. It is even worse.
            # The default value of proxy_scheme is http (not https). It could be very confusing.
            conn = httplib.HTTPSConnection(
                self.proxy_hostname, self.proxy_port, context=context, timeout=self.timeout
            )
            conn.set_tunnel(self.host, safe_int(self.ssl_port), proxy_headers)
            self.headers["Host"] = "%s:%s" % (normalized_host(self.host), safe_int(self.ssl_port))
        else:
            conn = httplib.HTTPSConnection(self.host, self.ssl_port, context=context, timeout=self.timeout)

        # Set default keep-alive connection timeout in case server does not
        # send HTTP header Keep-Alive with information about timeout
        conn.keep_alive_timeout = self.KEEP_ALIVE_TIMEOUT
        # Number of requests
        conn.requests_num = 0
        # Maximal number of requests. None means no limits, when server does not
        conn.max_requests_num = None

        # Do TCP and TLS handshake here before we make any request
        try:
            conn.connect()
        except OSError as e:
            # in case this OSError does not have an errno set, it means it was
            # not a syscall failure; mostly (if at all) this is raisen on proxy
            # connection failures
            if e.errno is None:
                # wrap this to carry also the details on the destination host
                raise ConnectionOSErrorException(self.host, self.ssl_port, self.apihandler, e)
            raise
        log.debug(f"Created connection: {conn.sock}")

        # Store connection object only in the case, when it is not forbidden
        if REUSE_CONNECTION is True:
            self.__conn = conn

        return conn

    def _print_debug_info_about_request(
        self, request_type: str, handler: str, final_headers: dict, body: Union[dict, Any]
    ) -> None:
        """
        This method can print debug information about sent http request. We do not use
        httplib.HTTPConnection.debuglevel = 1, because it doesn't provide control about displayed information.
        The debug print is printed to stdout, when environment variable SUBMAN_DEBUG_PRINT_REQUEST is set.
        Output can be modified with following environment variables:
         * SUBMAN_DEBUG_PRINT_REQUEST_HEADER
         * SUBMAN_DEBUG_PRINT_REQUEST_BODY
        :param request_type: (GET, POST, PUT, ...)
        :param handler: e.g. /candlepin/status
        :param final_headers: HTTP headers used by request
        :param body: request can contain body. It is usually dictionary, but it can be anything that
            can be serialized by json.dumps()
        :return: None
        """

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST", "") == "":
            return

        print()

        # Print information about TCP/IP layer
        if (
            os.environ.get("SUBMAN_DEBUG_TCP_IP", "")
            and self.__conn is not None
            and self.__conn.sock is not None
        ):
            print(utils.colorize("TCP socket:", utils.COLOR.GREEN))
            print(utils.colorize(f"{self.__conn.sock}", utils.COLOR.BLUE))

        # When proxy server is used, then print some additional information about proxy connection
        if self.proxy_hostname and self.proxy_port:
            print(utils.colorize("Proxy:", utils.COLOR.GREEN))
            # Note: using only https:// is not a mistake. We use only https for proxy connection.
            proxy_msg: str = "https://"
            # Print username and eventually password
            if self.proxy_user:
                if self.proxy_user and self.proxy_password:
                    proxy_msg += f"{self.proxy_user}:{self.proxy_password}@"
                elif self.proxy_user and not self.proxy_password:
                    proxy_msg += f"{self.proxy_user}@"
            # Print hostname and port
            proxy_msg += f"{normalized_host(self.proxy_hostname)}:{safe_int(self.proxy_port)}"
            print(utils.colorize(proxy_msg, utils.COLOR.MAGENTA))

            # Print HTTP headers used for proxy connection
            tunnel_msg = ""
            tunnel_headers = None
            if self.__conn is not None and hasattr(self.__conn, "_tunnel_headers"):
                tunnel_headers = getattr(self.__conn, "_tunnel_headers")
            if tunnel_headers is not None:
                tunnel_msg = f"{tunnel_headers}"
            if tunnel_msg:
                print(utils.colorize(tunnel_msg, utils.COLOR.BLUE))

        auth = ""
        if self.insecure:
            auth = "insecure "
        if self.auth_type == ConnectionType.KEYCLOAK_AUTH:
            auth += "keycloak auth"
        elif self.auth_type == ConnectionType.BASIC_AUTH:
            auth += "basic auth"
        elif self.auth_type == ConnectionType.CONSUMER_CERT_AUTH:
            auth += "consumer auth"
        elif self.auth_type == ConnectionType.NO_AUTH:
            auth += "no auth"
        else:
            auth += "undefined auth"

        print(utils.colorize("Request:", utils.COLOR.GREEN))
        print(
            utils.colorize(
                f"{request_type} "
                + "https://"
                + f"{normalized_host(self.host)}:{safe_int(self.ssl_port)}{handler}",
                utils.COLOR.RED,
            )
            + " using "
            + utils.colorize(f"{auth}", utils.COLOR.BLUE)
        )

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST_HEADER", ""):
            print(utils.colorize("Request headers:", utils.COLOR.GREEN))
            print(utils.colorize(f"{final_headers}", utils.COLOR.BLUE))

        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST_BODY", "") and body is not None:
            print(utils.colorize("Request body:", utils.COLOR.GREEN))
            print(utils.colorize(f"{body}", utils.COLOR.YELLOW))

        if os.environ.get("SUBMAN_DEBUG_PRINT_TRACEBACKS", ""):
            print(utils.colorize("Current call stack:", utils.COLOR.GREEN))
            traceback.print_stack(file=sys.stdout)

        if os.environ.get("SUBMAN_DEBUG_SAVE_TRACEBACKS", ""):
            debug_dir = Path("/tmp/rhsm/")
            debug_dir.mkdir(exist_ok=True)

            timestamp: str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # make sure we don't overwrite previous logs
            i = 0
            while True:
                filename = Path(f"{timestamp}_{i}.log")
                debug_log = debug_dir / filename
                if not debug_log.exists():
                    break
                i += 1

            with debug_log.open("w", encoding="utf-8") as handle:
                traceback.print_stack(file=handle)

            print(utils.colorize("Call stack file:", utils.COLOR.GREEN))
            print(f"{str(debug_log)}")

        print()

    @staticmethod
    def _print_debug_info_about_response(result: dict) -> None:
        """
        This method can print result of HTTP request to stdout, when
        environment variable SUBMAN_DEBUG_PRINT_RESPONSE is set
        :param result: response from candlepin server
        :return: None
        """

        if os.environ.get("SUBMAN_DEBUG_PRINT_RESPONSE", ""):
            print(utils.colorize("Response:", utils.COLOR.GREEN))
            print(utils.colorize(f"{result['status']}", utils.COLOR.RED))

            print(utils.colorize("Response headers:", utils.COLOR.GREEN))
            print(utils.colorize(f"{result['headers']}", utils.COLOR.BLUE))

            if result["content"]:
                print(utils.colorize("Response body:", utils.COLOR.GREEN))
                print(utils.colorize(f"{result['content']}", utils.COLOR.YELLOW))

            print()

    def _set_accept_language_in_header(self) -> None:
        """
        Set accepted language in http header according current settings or environment variable
        :return: None
        """
        try:
            import subscription_manager.i18n

            try:
                language = subscription_manager.i18n.LOCALE.language
            except AttributeError:
                language = None
        except ImportError:
            language = None

        if language is None:
            lc = _get_locale()
        else:
            lc = language

        if lc:
            self.headers["Accept-Language"] = lc.lower().replace("_", "-").split(".", 1)[0]

    @staticmethod
    def parse_keep_alive_header(keep_alive_header: str) -> Tuple[Union[None, int], Union[None, int]]:
        """
        Try to parse 'Keep-Alive' header received from candlepin server
        :param keep_alive_header: string with value of the header
        :return: Tuple containing connection timeout and maximal number of requests
        """
        keep_alive_timeout = None
        max_requests_num = None
        # Regular expression pattern represents: key=number
        pattern = re.compile(r"^(.*)=(\d+)[,;]*$")

        items = keep_alive_header.split()

        for item in items:
            search_result = pattern.search(item)
            if search_result is not None:
                key, value = search_result.groups()
                # Timeout of connection using keep-alive
                if key == "timeout":
                    keep_alive_timeout = int(search_result.groups()[1])
                # Maximal number of request on one connection
                elif key == "max":
                    max_requests_num = int(search_result.groups()[1])
                # Any other argument
                else:
                    log.debug(f"Unknown Keep-Alive argument: {key}")
            else:
                log.debug(f"Unable to parse value of Keep-Alive HTTP header: {item}")

        return keep_alive_timeout, max_requests_num

    def _make_request(
        self,
        request_type: str,
        handler: str,
        final_headers: dict,
        body: str,
        cert_key_pairs: List[Tuple[str, str]],
        description: Optional[str] = None,
    ) -> Tuple[Union[Dict[str, Any], None], Union[httplib.HTTPResponse, None]]:
        """
        Try to do HTTP request
        :param request_type: string representing request type
        :param handler: path of the request
        :param final_headers: dictionary with HTTP headers
        :param body: body of request if any
        :param cert_key_pairs: list of tuples. Tuple contain cert and key
        :param description: description of request
        :return: tuple of two items. First is dictionary (content, status and header) of response.
            Second item is response from server.
        """
        response = None
        result = None
        with utils.LiveStatusMessage(description):
            for cert_file, key_file in cert_key_pairs:
                try:
                    conn = self._create_connection(cert_file=cert_file, key_file=key_file)

                    self._print_debug_info_about_request(request_type, handler, final_headers, body)

                    ts_start = time.time()
                    conn.last_request_time = ts_start
                    conn.request(request_type, handler, body=body, headers=final_headers)
                    ts_end = time.time()
                    response = conn.getresponse()
                    self._update_smoothed_response_time(ts_end - ts_start)

                    result = {
                        "content": response.read().decode("utf-8"),
                        "status": response.status,
                        "headers": dict(response.getheaders()),
                    }
                    if response.status == 200:
                        self.is_consumer_cert_key_valid = True
                        break  # this client cert worked, no need to try more
                    elif self.cert_dir:
                        log.debug(
                            "Unable to get valid response: %s from CDN: %s"
                            % (result, normalized_host(self.host))
                        )
                except ssl.SSLError:
                    if self.cert_file and not self.cert_dir:
                        id_cert = certificate.create_from_file(self.cert_file)
                        if not id_cert.is_valid():
                            self.is_consumer_cert_key_valid = False
                            raise ExpiredIdentityCertException()
                    if not self.cert_dir:
                        raise
                except socket.gaierror as err:
                    if self.proxy_hostname and self.proxy_port:
                        raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port, exc=err)
                    raise
                except (socket.error, OSError) as err:
                    # If we get a ConnectionError here and we are using a proxy,
                    # then the issue was the connection to the proxy, not to the
                    # destination host.
                    if isinstance(err, ConnectionError) and self.proxy_hostname and self.proxy_port:
                        raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port, exc=err)
                    code = httplib.PROXY_AUTHENTICATION_REQUIRED.value
                    if str(code) in str(err):
                        raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port, exc=err)
                    raise
            else:
                if self.cert_dir:
                    raise NoValidEntitlement(
                        "Cannot access CDN content on: %s using any of entitlement cert-key pair: %s"
                        % (normalized_host(self.host), cert_key_pairs)
                    )
        return result, response

    def _request(
        self,
        request_type: str,
        method: str,
        params: Any = None,
        headers: dict = None,
        cert_key_pairs: Optional[List[Tuple[str, str]]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to candlepin server
        :param request_type: string representing request type
        :param method: path of the request
        :param params: data (usually dictionary) of request if any
        :param headers: dictionary with HTTP headers
        :param cert_key_pairs: list of tuples. Tuple contain cert and key
        :param description: description of request
        :return: Dictionary (content, status and headers) of response.
        """
        handler = self.apihandler + method

        # We try to import it here to get fresh value, because rhsm.service can receive
        # several D-BUS API calls with different locale argument (every request have to have
        # different locale)
        self._set_accept_language_in_header()

        # Load certificates from cert dir if specified
        if cert_key_pairs is None or len(cert_key_pairs) == 0:
            cert_key_pairs = self._get_cert_key_list()

        if (
            headers is not None
            and "Content-type" in headers
            and headers["Content-type"] == "application/x-www-form-urlencoded"
        ):
            body = urlencode(params).encode("utf-8")
        elif params is not None:
            body = json.dumps(params, default=json.encode)
        else:
            body = None

        if self.__conn is not None:
            self.headers["Connection"] = "keep-alive"

        log.debug("Making request: %s %s" % (request_type, handler))

        if self.user_agent:
            self.headers["User-Agent"] = self.user_agent

        final_headers = self.headers.copy()
        if body is None:
            final_headers["Content-Length"] = "0"
        if headers:
            final_headers.update(headers)

        # Try to do request, when it wasn't possible, because server closed connection,
        # then close existing connection and try it once again
        try:
            result, response = self._make_request(
                request_type, handler, final_headers, body, cert_key_pairs, description
            )
        except httplib.RemoteDisconnected:
            log.debug("Connection closed by server")
            self.close_connection()
            log.debug("Trying request once again")
            result, response = self._make_request(
                request_type, handler, final_headers, body, cert_key_pairs, description
            )

        self._print_debug_info_about_response(result)

        response_log = "Response: status=" + str(result["status"])
        if response.getheader("x-candlepin-request-uuid"):
            response_log = "%s, requestUuid=%s" % (
                response_log,
                response.getheader("x-candlepin-request-uuid"),
            )
        response_log = '%s, request="%s %s"' % (response_log, request_type, handler)
        log.debug(response_log)

        connection_http_header = response.getheader("Connection", default="").lower()
        if connection_http_header == "keep-alive":
            log.debug("Server wants to keep connection")
        elif connection_http_header == "close":
            log.debug("Server wants to close connection. Closing HTTP connection")
            self.close_connection()
        elif connection_http_header == "":
            log.debug("HTTP header 'Connection' not included in response")
        else:
            log.debug(f"Unsupported value of HTTP header 'Connection': {connection_http_header}")

        keep_alive_http_header = response.getheader("Keep-Alive")
        # When connection is shared between HTTP requests, then try to parse HTTP header
        # and store the latest value in object representing connection
        if self.__conn is not None and keep_alive_http_header is not None:
            keep_alive_timeout, max_requests_num = self.parse_keep_alive_header(keep_alive_http_header)
            if keep_alive_timeout is not None:
                self.__conn.keep_alive_timeout = keep_alive_timeout
                log.debug(f"Connection timeout: {keep_alive_timeout} is used from 'Keep-Alive' HTTP header")
            if max_requests_num is not None:
                self.__conn.max_request_num = max_requests_num
                log.debug(f"Max number of requests: {max_requests_num} is used from 'Keep-Alive' HTTP header")

        # Look for a time drift and log if the system is significantly different from server clock
        response_sent_at: Optional[str] = response.getheader("date")
        if response_sent_at is not None:
            try:
                drift: datetime.timedelta = get_time_drift(response_sent_at)
                message: str = (
                    f"Local system clock seems to be off by {drift}, please check your system time."
                )
                if drift > datetime.timedelta(hours=1):
                    log.warning(message)
                elif drift > datetime.timedelta(minutes=15):
                    log.debug(message)
            except Exception:
                log.exception(
                    f"Could not check if local clock is off from server's time '{response_sent_at}'"
                )

        # FIXME: we should probably do this in a wrapper method
        # so we can use the request method for normal http

        self.validateResult(result, request_type, handler)

        return result

    def _update_smoothed_response_time(self, response_time: float):
        """
        Method for computing smoothed time of response. It is based on computing SRTT (See RFC 793).
        :param response_time: response time of the latest http request
        :return: None
        """
        if self.smoothed_rt is None:
            self.smoothed_rt = response_time
        else:
            self.smoothed_rt = (self.ALPHA * self.smoothed_rt) + ((1 - self.ALPHA) * response_time)
        log.debug(
            f"Response time statistics: {response_time:.4f}s (latest), {self.smoothed_rt:.4f}s (smoothed)"
        )

    def validateResult(self, result: dict, request_type: str = None, handler: str = None) -> None:
        """
        Try to validate result of HTTP request. Raise exception, when validation of
        result failed
        :param result: Dictionary holding result
        :param request_type: String representation of original request
        :param handler: String containing handler of request
        """

        # FIXME: what are we supposed to do with a 204?
        if str(result["status"]) not in ["200", "202", "204", "304"]:
            parsed = {}
            if not result.get("content"):
                parsed = {}
            else:
                # try vaguely to see if it had a json parseable body
                try:
                    parsed = json.loads(result["content"])
                except ValueError as e:
                    log.error("Response: %s" % result["status"])
                    log.error("JSON parsing error: %s" % e)
                except Exception as e:
                    log.error("Response: %s" % result["status"])
                    log.exception(e)

            if parsed:
                # Find and raise a GoneException on '410' with 'deletedId' in the
                # content, implying that the resource has been deleted.

                # NOTE: a 410 with an unparseable content will raise
                # RemoteServerException and will not cause the client
                # to delete the consumer cert.
                if str(result["status"]) == "410":
                    raise GoneException(result["status"], parsed["displayMessage"], parsed["deletedId"])

                elif str(result["status"]) == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port)

                # I guess this is where we would have an exception mapper if we
                # had more meaningful exceptions. We've gotten a response from
                # the server that means something.

                error_msg = self._parse_msg_from_error_response_body(parsed)
                if str(result["status"]) in ["429"]:
                    raise RateLimitExceededException(
                        result["status"], error_msg, headers=result.get("headers")
                    )

                if str(result["status"]) in ["401"]:
                    # If the proxy is not configured correctly
                    # it connects to the server without the identity cert
                    # even if the cert is valid
                    if self.proxy_hostname:
                        if self.cert_file:
                            id_cert = certificate.create_from_file(self.cert_file)
                            if id_cert.is_valid():
                                raise RestlibException(
                                    result["status"],
                                    (
                                        "Unable to make a connection using SSL client certificate. "
                                        "Please review proxy configuration and connectivity."
                                    ),
                                    result.get("headers"),
                                )

                # FIXME: we can get here with a valid json response that
                # could be anything, we don't verify it anymore
                raise RestlibException(result["status"], error_msg, result.get("headers"))
            else:
                # This really needs an exception mapper too...
                if str(result["status"]) in ["404", "410", "500", "502", "503", "504"]:
                    raise RemoteServerException(result["status"], request_type=request_type, handler=handler)
                elif str(result["status"]) in ["401"]:
                    raise UnauthorizedException(result["status"], request_type=request_type, handler=handler)
                elif str(result["status"]) in ["403"]:
                    raise ForbiddenException(result["status"], request_type=request_type, handler=handler)
                elif str(result["status"]) in ["429"]:
                    raise RateLimitExceededException(result["status"], headers=result.get("headers"))

                elif str(result["status"]) == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port)

                else:
                    # unexpected with no valid content
                    raise UnknownContentException(
                        result["status"],
                        result.get("headers", {}).get("Content-Type"),
                        result.get("content"),
                    )

    @staticmethod
    def _parse_msg_from_error_response_body(body: dict) -> str:
        # Old style with a single displayMessage:
        if "displayMessage" in body:
            return body["displayMessage"]

        # New style list of error messages:
        if "errors" in body:
            return " ".join("%s" % errmsg for errmsg in body["errors"])

        # keycloak error messages
        if "error_description" in body:
            return body["error_description"]

    @staticmethod
    def _extract_content_from_response(request_result: Dict[str, Any]) -> Any:
        """
        Extracts the data within the 'content' field of the result from a successful http response.
        :param request_result: Response result from an http request.
        :return: Data from the 'content' field of the result or None if the response had a 204 status.
        """

        # Handle 204s
        if not len(request_result["content"]):
            return None
        try:
            return json.loads(request_result["content"])
        except json.JSONDecodeError:
            # This is primarily intended for getting releases from CDN, because
            # the file containing releases is plaintext and not json.
            return request_result["content"]

    def request_get(
        self,
        method: str,
        headers: dict = None,
        cert_key_pairs: List[Tuple[str, str]] = None,
        description: Optional[str] = None,
    ) -> Any:
        result: Dict[str, Any] = self._request(
            "GET", method, headers=headers, cert_key_pairs=cert_key_pairs, description=description
        )
        return self._extract_content_from_response(result)

    def request_post(
        self, method: str, params: Any = None, headers: dict = None, description: Optional[str] = None
    ) -> Any:
        result: Dict[str, Any] = self._request(
            "POST", method, params, headers=headers, description=description
        )
        return self._extract_content_from_response(result)

    def request_head(self, method: str, headers: dict = None, description: Optional[str] = None) -> Any:
        result: Dict[str, Any] = self._request("HEAD", method, headers=headers, description=description)
        return self._extract_content_from_response(result)

    def request_put(
        self, method: str, params: Any = None, headers: dict = None, description: Optional[str] = None
    ) -> Any:
        result: Dict[str, Any] = self._request(
            "PUT", method, params, headers=headers, description=description
        )
        return self._extract_content_from_response(result)

    def request_delete(
        self, method: str, params: Any = None, headers: dict = None, description: Optional[str] = None
    ) -> Any:
        result: Dict[str, Any] = self._request(
            "DELETE", method, params, headers=headers, description=description
        )
        return self._extract_content_from_response(result)

    @staticmethod
    def _format_http_date(dt: datetime.datetime) -> str:
        """
        Format a datetime to HTTP-date as described by RFC 7231.
        """
        return format_datetime(dt, usegmt=True)


class UEPConnection(BaseConnection):
    """
    Class for communicating with the REST interface of a Red Hat Unified
    Entitlement Platform.
    """

    def __init__(self, **kwargs) -> None:
        """
        Multiple ways to authenticate:
            - username/password for HTTP basic authentication. (owner admin role)
            - uuid/key_file/cert_file for identity cert authentication.
              (consumer role)
            - token (when supported by the server)

        Must specify only one method of authentication.
        """
        user_agent = "RHSM/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)
        if "client_version" in kwargs:
            user_agent += kwargs["client_version"]
        if "dbus_sender" in kwargs:
            user_agent += kwargs["dbus_sender"]
        super(UEPConnection, self).__init__(user_agent=user_agent, **kwargs)

    def _load_supported_resources(self) -> None:
        """
        Load the list of supported resources by doing a GET on the root
        of the web application we're configured to use.

        Need to handle exceptions here because sometimes UEPConnections are
        created in a state where they can't actually be used. (they get
        replaced later) If something goes wrong making this request, just
        leave the list of supported resources empty.
        """
        self.resources: dict = {}
        resources_list = self.conn.request_get("/", description=_("Fetching supported resources"))
        for r in resources_list:
            self.resources[r["rel"]] = r["href"]
        log.debug("Server supports the following resources: %s", self.resources)

    def get_supported_resources(self) -> dict:
        """
        Get list of supported resources.
        :return: list of supported resources
        """
        if self.resources is None:
            self._load_supported_resources()

        return self.resources

    def supports_resource(self, resource_name: Optional[str]) -> bool:
        """Check if the server supports a particular resource.

        :param resource_name:
            Resource to be requested.
            When `None`, API call 'GET /' is made to cache all supported resources.
        """
        if self.resources is None:
            self._load_supported_resources()

        return resource_name in self.resources

    def _load_manager_capabilities(self) -> list:
        """
        Loads manager capabilities by doing a GET on the status
        resource located at '/status'
        """
        status = self.getStatus()
        capabilities = status.get("managerCapabilities")
        if capabilities is None:
            log.debug(
                "The status retrieved did not \
                      include key 'managerCapabilities'.\nStatus:'%s'"
                % status
            )
            capabilities = []
        elif isinstance(capabilities, list) and not capabilities:
            log.debug(
                "The managerCapabilities list \
                      was empty\nStatus:'%s'"
                % status
            )
        else:
            log.debug("Server has the following capabilities: %s", capabilities)
        return capabilities

    def has_capability(self, capability: str) -> bool:
        """
        Check if the server we're connected to has a particular capability.
        """
        if self.capabilities is None:
            self.capabilities = self._load_manager_capabilities()
        return capability in self.capabilities

    def ping(self, *args, **kwargs) -> Any:
        return self.conn.request_get("/status/", description=_("Checking connection status"))

    def getCloudJWT(self, cloud_id: str, metadata: str, signature: str) -> Dict[str, Any]:
        """Obtain cloud JWT.

        This method is part of the Cloud registration v2: standard or anonymous flow.

        :param cloud_id: Cloud provider, e.g. 'aws', 'azure' or 'gcp'.
        :param metadata: Base64 encoded public cloud metadata.
        :param signature: Base64 encoded public cloud signature.
        """
        data = {
            "type": cloud_id,
            "metadata": metadata,
            "signature": signature,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
        }

        return self.conn.request_post(
            method="/cloud/authorize",
            params=data,
            headers=headers,
            description=_("Fetching cloud token"),
        )

    def registerConsumer(
        self,
        name: str = "unknown",
        consumer_type: str = "system",
        facts: Optional[dict] = None,
        owner: str = None,
        environments: str = None,
        keys: str = None,
        installed_products: list = None,
        uuid: str = None,
        hypervisor_id: str = None,
        content_tags: set = None,
        role: str = None,
        addons: Union[str, List[str]] = None,
        service_level: str = None,
        usage: str = None,
        jwt_token: str = None,
    ) -> dict:
        """
        Creates a consumer on candlepin server
        """
        if facts is None:
            facts = {}
        params = {
            "type": consumer_type,
            "name": name,
            "facts": facts,
        }
        if installed_products:
            params["installedProducts"] = installed_products

        if uuid:
            params["uuid"] = uuid

        if hypervisor_id is not None:
            params["hypervisorId"] = {"hypervisorId": hypervisor_id}

        if content_tags is not None:
            params["contentTags"] = content_tags
        if role is not None:
            params["role"] = role
        if addons is not None:
            params["addOns"] = addons
        if usage is not None:
            params["usage"] = usage
        if service_level is not None:
            params["serviceLevel"] = service_level
        if environments is not None and self.has_capability(MULTI_ENV):
            env_list = []
            for environment in environments.split(","):
                env_list.append({"id": environment})
            params["environments"] = env_list

        headers = {}
        if jwt_token:
            headers["Authorization"] = "Bearer {jwt_token}".format(jwt_token=jwt_token)

        url = "/consumers"
        if environments and not self.has_capability(MULTI_ENV):
            url = "/environments/%s/consumers" % self.sanitize(environments)
        elif owner:
            query_param = urlencode({"owner": owner})
            url = "%s?%s" % (url, query_param)
            prepend = ""
            if keys:
                url = url + "&activation_keys="
                for key in keys:
                    url = url + prepend + self.sanitize(key)
                    prepend = ","

        return self.conn.request_post(url, params, headers=headers, description=_("Registering system"))

    # FIXME: the options argument is some object with some attributes. It is not defined anywhere
    # virt-who uses some dummy object and add some attributes to this object
    def hypervisorCheckIn(self, owner: str, env: str, host_guest_mapping: dict, options: Any = None) -> dict:
        """
        Sends a mapping of hostIds to list of guestIds to candlepin
        to be registered/updated.
        This method can raise the following exceptions:
            - RestLibException with http code 400: this means no mapping
            (or a bad one) was provided.
            - RestLibException with other http codes: Please see the
            definition of RestLibException above for info about this.
            - RateLimitExceededException: This means that too many requests
            have been made in the given time period.

        """
        if self.has_capability("hypervisors_async"):
            priorContentType = self.conn.headers["Content-type"]
            self.conn.headers["Content-type"] = "text/plain"

            params = {"env": env, "cloaked": False}
            if options and options.reporter_id and len(options.reporter_id) > 0:
                params["reporter_id"] = options.reporter_id

            query_params = urlencode(params)
            url = "/hypervisors/%s?%s" % (owner, query_params)
            res = self.conn.request_post(
                url,
                host_guest_mapping,
                description=_("Updating detected virtual machines running on given host"),
            )
            self.conn.headers["Content-type"] = priorContentType
        else:
            # fall back to original report api
            # this results in the same json as in the result_data field
            # of the new api method
            query_params = urlencode({"owner": owner, "env": env})
            url = "/hypervisors?%s" % (query_params)
            res = self.conn.request_post(
                url,
                host_guest_mapping,
                description=_("Updating detected virtual machines running on given host"),
            )
        return res

    def hypervisorHeartbeat(self, owner: str, options: Any = None) -> Union[dict, None]:
        """
        Sends the reporter id to candlepin
        to update the hypervisors it has previously reported.
        This method can raise the following exception:
            - RateLimitExceededException: This means that too many requests
            have been made in the given time period.
        """
        # Return None early if the connected UEP does not support
        # hypervisors_heartbeat or if there is no reporter_id provided.
        if not self.has_capability("hypervisors_heartbeat") or not (
            options and options.reporter_id and len(options.reporter_id) > 0
        ):
            return

        params = {}
        params["reporter_id"] = options.reporter_id
        query_params = urlencode(params)
        url = "/hypervisors/%s/heartbeat?%s" % (owner, query_params)
        return self.conn.request_put(url, description=_("Updating hypervisor information"))

    def updateConsumerFacts(self, consumer_uuid: str, facts: dict = None) -> dict:
        """
        Update a consumers facts on candlepin server
        """
        return self.updateConsumer(consumer_uuid, facts=facts)

    def updateConsumer(
        self,
        uuid: str,
        facts: dict = None,
        installed_products: list = None,
        guest_uuids: Union[List[str], List[dict]] = None,
        service_level: str = None,
        release: str = None,
        autoheal: bool = None,
        hypervisor_id: str = None,
        content_tags: set = None,
        role: str = None,
        addons: Union[str, List[str]] = None,
        usage: str = None,
        environments: str = None,
    ) -> dict:
        """
        Update a consumer on the server.

        Rather than requiring a full representation of the consumer, only some
        information is passed depending on what we wish to update.

        Note that installed_products and guest_uuids expects a certain format,
        example parsing is in subscription-manager's format_for_server() method.

        This can raise the following exceptions:
            - RestlibException - This will include an http error code and a
            translated message that provides some detail as to what happend.
            - GoneException - This indicates that the consumer has been deleted
        """
        params = {}
        if installed_products is not None:
            params["installedProducts"] = installed_products
        if guest_uuids is not None:
            params["guestIds"] = self.sanitizeGuestIds(guest_uuids)
        if facts is not None:
            params["facts"] = facts
        if release is not None:
            params["releaseVer"] = release
        if autoheal is not None:
            params["autoheal"] = autoheal
        if hypervisor_id is not None:
            params["hypervisorId"] = {"hypervisorId": hypervisor_id}
        if content_tags is not None:
            params["contentTags"] = content_tags
        if role is not None:
            params["role"] = role
        if addons is not None:
            if isinstance(addons, list):
                params["addOns"] = addons
            elif isinstance(addons, str):
                params["addOns"] = [addons]
        if usage is not None:
            params["usage"] = usage
        if environments is not None:
            env_list = []
            for environment in environments.split(","):
                env_list.append({"id": environment})
            params["environments"] = env_list

        # The server will reject a service level that is not available
        # in the consumer's organization, so no need to check if it's safe
        # here:
        if service_level is not None:
            params["serviceLevel"] = service_level

        method = "/consumers/%s" % self.sanitize(uuid)
        ret = self.conn.request_put(method, params, description=_("Updating consumer information"))
        return ret

    def getGuestIds(self, uuid: str) -> dict:
        method = "/consumers/%s/guestids" % self.sanitize(uuid)
        return self.conn.request_get(method, description=_("Fetching guest information"))

    def getGuestId(self, uuid: str, guest_uuid: str) -> dict:
        method = "/consumers/%s/guestids/%s" % (self.sanitize(uuid), self.sanitize(guest_uuid))
        return self.conn.request_get(method, description=_("Fetching guest information"))

    def removeGuestId(self, uuid: str, guest_uuid: str) -> dict:
        method = "/consumers/%s/guestids/%s" % (self.sanitize(uuid), self.sanitize(guest_uuid))
        return self.conn.request_delete(method, description=_("Removing guests"))

    def sanitizeGuestIds(self, guestIds: Union[List[str], List[dict]]) -> Union[List[str], List[dict]]:
        return [self.sanitizeGuestId(guestId) for guestId in guestIds or []]

    def sanitizeGuestId(self, guestId: Union[str, dict]) -> Union[str, dict]:
        """
        Sanitizes one or more provided guest Ids.
        :param guestId: One or more guest Ids.
        """
        if isinstance(guestId, str):
            return guestId
        elif isinstance(guestId, dict):
            if "guestId" in list(guestId.keys()):
                if self.supports_resource("guestids"):
                    # Upload full json
                    return guestId
                # Does not support the full guestId json, use the id string
                return guestId["guestId"]
            raise KeyError("Error: A 'guestId' key was not found in the provided guest Id dictionary.")
        raise TypeError("Error: Only a string or dictionary data type can be sanitized.")

    def updatePackageProfile(self, consumer_uuid: str, pkg_dicts: dict) -> dict:
        """
        Updates the consumer's package profile on the server.

        pkg_dicts expected to be a list of dicts, each containing the
        package headers we're interested in. See profile.py.
        """
        method = "/consumers/%s/packages" % self.sanitize(consumer_uuid)
        return self.conn.request_put(method, pkg_dicts, description=_("Updating profile information"))

    def updateCombinedProfile(self, consumer_uuid: str, profile: List[Dict]) -> dict:
        """
        Updates the costumers' combined profile containing package profile,
        enabled repositories and dnf modules.
        :param consumer_uuid: UUID of consumer
        :param profile: Combined profile
        :return: Dict containing response from HTTP server
        """
        method = "/consumers/%s/profiles" % self.sanitize(consumer_uuid)
        return self.conn.request_put(method, profile, description=_("Updating profile information"))

    def getConsumer(self, uuid: str) -> dict:
        """
        Returns a consumer object with pem/key for existing consumers
        :param uuid: UUID of consumer (part of installed consumer cert, when system is registered)
        """
        method = "/consumers/%s" % self.sanitize(uuid)
        return self.conn.request_get(method, description=_("Fetching consumer keys"))

    def getCompliance(self, uuid: str, on_date: datetime.datetime = None) -> dict:
        """
        Returns a compliance object with compliance status information
        """
        method = "/consumers/%s/compliance" % self.sanitize(uuid)
        if on_date:
            method = "%s?on_date=%s" % (method, self.sanitize(on_date.isoformat(), plus=True))
        return self.conn.request_get(method, description=_("Checking compliance status"))

    def getSyspurposeCompliance(self, uuid: str, on_date: datetime.datetime = None) -> dict:
        """
        Returns a system purpose compliance object with compliance status information
        """
        method = "/consumers/%s/purpose_compliance" % self.sanitize(uuid)
        if on_date:
            method = "%s?on_date=%s" % (method, self.sanitize(on_date.isoformat(), plus=True))
        return self.conn.request_get(method, description=_("Checking system purpose compliance status"))

    def getOwnerSyspurposeValidFields(self, owner_key: str) -> dict:
        """
        Retrieves the system purpose settings available to an owner
        """
        method = "/owners/%s/system_purpose" % self.sanitize(owner_key)
        return self.conn.request_get(method, description=_("Fetching available system purpose settings"))

    def getOwner(self, uuid: str) -> dict:
        """
        Returns an owner object with pem/key for existing consumers
        """
        method = "/consumers/%s/owner" % self.sanitize(uuid)
        return self.conn.request_get(method, description=_("Fetching organizations"))

    def getOwnerList(self, username: str) -> List[dict]:
        """
        Returns a list of owners for given user. This method requires admin connection and authenticated
        using username/password
        """
        method = "/users/%s/owners" % self.sanitize(username)
        owners = self.conn.request_get(method, description=_("Fetching organizations"))
        # BZ 1749395 When a user has no orgs, the return value
        #  is an array with a single None element.
        # Ensures the value is the same for a simple None value
        owners = [x for x in (owners or []) if x is not None]
        return owners

    def unregisterConsumer(self, consumerId: str) -> bool:
        """
        Deletes a consumer from candlepin server
        :param consumerId: consumer UUID (it could be found in consumer cert, when system is registered)
        """
        method = "/consumers/%s" % self.sanitize(consumerId)
        return self.conn.request_delete(method, description=_("Unregistering system")) is None

    def getCertificates(
        self,
        consumer_uuid: str,
        serials: Optional[list] = None,
        jwt: Optional[str] = None,
    ) -> List[dict]:
        """
        Fetch all entitlement certificates for this consumer. Specify a list of serial numbers to
        filter if desired

        :param consumer_uuid: consumer UUID
        :param serials: list of entitlement serial numbers
        :param jwt: JWT identifying an anonymous system
        """
        method = "/consumers/%s/certificates" % (self.sanitize(consumer_uuid))
        if serials:
            serials_str = ",".join(serials)
            method = "%s?serials=%s" % (method, serials_str)
        headers: Dict[str, str] = {}
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        return self.conn.request_get(method, headers=headers, description=_("Fetching certificates"))

    def getCertificateSerials(self, consumerId: str) -> List[dict]:
        """
        Get serial numbers for certs for a given consumer. Returned list is list of dictionaries, because
        it contains additional information about entitlement certificates
        :param consumerId: consumer UUID
        """
        method = "/consumers/%s/certificates/serials" % self.sanitize(consumerId)
        return self.conn.request_get(method, description=_("Fetching certificate serial numbers"))

    def getAccessibleContent(self, consumerId: str, if_modified_since: datetime.datetime = None) -> dict:
        """
        Get the content of the accessible content cert for a given consumer. This method works only in the
        case, when simple content access is used by current owner (organization)
        :param consumerId: consumer UUID
        :param if_modified_since: If present, only return the content if it was altered since the given date
        :return: Dictionary with the last modified date and the content
        """
        method = "/consumers/%s/accessible_content" % consumerId
        headers = {}
        if if_modified_since:
            timestamp = BaseRestLib._format_http_date(if_modified_since)
            headers["If-Modified-Since"] = timestamp
        return self.conn.request_get(
            method, headers=headers, description=_("Fetching content for a certificate")
        )

    def bindByEntitlementPool(self, consumerId: str, poolId: str, quantity: int = None) -> List[dict]:
        """
        Subscribe consumer to a subscription by pool ID
        :param consumerId: consumer UUID
        :param poolId: pool ID
        :param quantity: the desired quantity of subscription to be consumed
        """
        method = "/consumers/%s/entitlements?pool=%s" % (self.sanitize(consumerId), self.sanitize(poolId))
        if quantity:
            method = "%s&quantity=%s" % (method, quantity)
        return self.conn.request_post(method, description=_("Updating subscriptions"))

    def bind(self, consumerId: str, entitle_date: datetime.datetime = None) -> List[dict]:
        """
        Same as bindByProduct, but assume the server has a list of the
        system's products. This is useful for autosubscribe. Note that this is
        done on a best-effort basis, and there are cases when the server will
        not be able to fulfill the client's product certs with entitlements
        :param consumerId: consumer UUID
        :param entitle_date: The date, when subscription will be valid
        """
        method = "/consumers/%s/entitlements" % (self.sanitize(consumerId))

        # add the optional date to the url
        if entitle_date:
            method = "%s?entitle_date=%s" % (method, self.sanitize(entitle_date.isoformat(), plus=True))

        return self.conn.request_post(method, description=_("Updating subscriptions"))

    def unbindBySerial(self, consumerId: str, serial: str) -> bool:
        """
        Try to remove consumed pool by serial number
        :param consumerId: consumer UUID
        :param serial: serial number of consumed pool
        """
        method = "/consumers/%s/certificates/%s" % (self.sanitize(consumerId), self.sanitize(str(serial)))
        return self.conn.request_delete(method, description=_("Unsubscribing")) is None

    def unbindByPoolId(self, consumer_uuid: str, pool_id: str) -> bool:
        """
        Try to remove consumed pool by pool ID
        :param consumer_uuid: consumer UUID
        :param pool_id: pool ID
        :return: None
        """
        method = "/consumers/%s/entitlements/pool/%s" % (self.sanitize(consumer_uuid), self.sanitize(pool_id))
        return self.conn.request_delete(method, description=_("Unsubscribing")) is None

    def unbindAll(self, consumerId: str) -> dict:
        """
        Try to remove all consumed pools
        :param consumerId: consumer UUID
        :return: Dictionary containing statistics about removed pools
        """
        method = "/consumers/%s/entitlements" % self.sanitize(consumerId)
        return self.conn.request_delete(method, description=_("Unsubscribing"))

    def getPoolsList(
        self,
        consumer: str = None,
        listAll: bool = False,
        active_on: datetime.datetime = None,
        owner: str = None,
        filter_string: str = None,
        future: str = None,
        after_date: datetime.datetime = None,
        page: int = 0,
        items_per_page: int = 0,
    ) -> List[dict]:
        """
        List pools for a given consumer or owner.

        Ideally, try to always pass the owner key argument. The old method is deprecated
        and may eventually be removed.
        """

        if owner:
            # Use the new preferred URL structure if possible:
            method = "/owners/%s/pools?" % self.sanitize(owner)
            if consumer:
                method = "%sconsumer=%s" % (method, consumer)

        elif consumer:
            # Just consumer specified, this URL is deprecated and may go away someday:
            method = "/pools?consumer=%s" % consumer

        else:
            raise Exception("Must specify an owner or a consumer to list pools.")

        if listAll:
            method = "%s&listall=true" % method
        if future in ("add", "only"):
            method = "%s&%s_future=true" % (method, future)
        if after_date:
            method = "%s&after=%s" % (method, self.sanitize(after_date.isoformat(), plus=True))
        if active_on and not after_date:
            method = "%s&activeon=%s" % (method, self.sanitize(active_on.isoformat(), plus=True))
        if filter_string:
            method = "%s&matches=%s" % (method, self.sanitize(filter_string, plus=True))
        if page != 0:
            method = "%s&page=%s" % (method, self.sanitize(page))
        if items_per_page != 0:
            method = "%s&per_page=%s" % (method, self.sanitize(items_per_page))

        results = self.conn.request_get(method, description=_("Fetching pools"))
        return results

    def getRelease(self, consumerId: str) -> dict:
        """
        Try to get current release for given consumer
        :param consumerId: consumer UUID
        :return: Dictionary with current release. It returns dictionary even no release is set.
            Like {'releaseVer': None}
        """
        method = "/consumers/%s/release" % self.sanitize(consumerId)
        results = self.conn.request_get(method, description=_("Fetching release information"))
        return results

    def getAvailableReleases(self, consumerId: str) -> List[dict]:
        """
        Gets the available content releases for a consumer.

        NOTE: Used for getting the available release versions
              from katello. In hosted candlepin scenario, the
              release versions will come from the CDN directly
              (API not implemented in candlepin).
        :param consumerId: consumer UUID
        """
        method = "/consumers/%s/available_releases" % self.sanitize(consumerId)
        return self.conn.request_get(method, description=_("Fetching available releases"))

    def getEntitlementList(self, consumerId: str, request_certs: bool = False) -> List[dict]:
        """
        Try to get list of consumed entitlement certificates
        :param consumerId: consumer UUID
        :param request_certs: If this argument is true, then response will include entitlement certs too
        :return: List of dictionaries containing information about entitlements
        """
        method = "/consumers/%s/entitlements" % self.sanitize(consumerId)
        if not request_certs:
            # It is unnecessary to download the certificate and key here
            filters = "?exclude=certificates.key&exclude=certificates.cert"
        else:
            filters = ""
        results = self.conn.request_get(method + filters, description=_("Fetching entitlements"))
        return results

    def getServiceLevelList(self, owner_key: str) -> List[str]:
        """
        List the service levels available for an owner
        :param owner_key: owner ID (organization ID)
        """
        method = "/owners/%s/servicelevels" % self.sanitize(owner_key)
        results = self.conn.request_get(method, description=_("Fetching service levels"))
        return results

    def getEnvironmentList(self, owner_key: str) -> List[dict]:
        """
        List the environments for a particular owner.

        Some servers may not support this and will error out. The caller
        can always check with supports_resource("environments").
        """
        method = "/owners/%s/environments" % self.sanitize(owner_key)
        results = self.conn.request_get(method, description=_("Fetching environments"))
        return results

    def regenIdCertificate(self, consumerId: str) -> dict:
        """
        Try to regenerate consumer certificate
        :param consumerId: consumer UUID
        :return: Dictionary containing information about consumer and new consumer certificate
        """
        method = "/consumers/%s" % self.sanitize(consumerId)
        return self.conn.request_post(method, description=_("Updating certificate"))

    def regenEntitlementCertificates(self, consumer_id: str, lazy_regen: bool = True) -> bool:
        """
        Regenerates all entitlements for the given consumer
        :param consumer_id: consumer UUID
        :param lazy_regen: When True then only mark certificates dirty and allow it to be regenerated
        on-demand on candlepin server. When False, then certificates are regenerated immediately
        :return True when regenerating of certificates was successful. Otherwise, return False
        """

        method = "/consumers/%s/certificates" % self.sanitize(consumer_id)

        if lazy_regen:
            method += "?lazy_regen=true"

        result = False

        try:
            self.conn.request_put(method, description=_("Updating certificates"))
            result = True
        except (RemoteServerException, httplib.BadStatusLine, RestlibException) as e:
            # 404s indicate that the service is unsupported (Candlepin too old, or SAM)
            if isinstance(e, httplib.BadStatusLine) or str(e.code) == "404":
                log.debug("Unable to refresh entitlement certificates: Service currently unsupported.")
                log.debug(e)
            else:
                # Something else happened that we should probably raise
                raise e

        return result

    def getStatus(self) -> dict:
        """
        Try to get information about status of server and supported capabilities
        :return: Dictionary with information about server
        """
        method = "/status"
        return self.conn.request_get(method, description=_("Checking server status"))

    def getContentOverrides(self, consumerId: str) -> List[dict]:
        """
        Get all the overrides for the specified consumer
        :param consumerId: consumer UUID
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        return self.conn.request_get(method, description=_("Fetching content overrides"))

    def setContentOverrides(self, consumerId: str, overrides: List[dict]) -> List[dict]:
        """
        Set an override on a content object
        :param consumerId: consumer UUID
        :param overrides: list of dictionaries. The dictionary have to have the following structure:
            {"contentLabel": "repo_id", "name": "label_name", "value": "label_value"}
        :return List of dictionaries containing all overrides for given repository
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        return self.conn.request_put(method, overrides, description=_("Updating content overrides"))

    def deleteContentOverrides(self, consumerId: str, params: List[dict] = None) -> List[dict]:
        """
        Delete an override on a content object
        :param consumerId: consumer UUID
        :param params: List of dictionaries containing overrides to be deleted. The dictionary have to
            have the following structure: {"contentLabel": "repo_id", "name": "label_name"}
        :return List of dictionaries containing all overrides for given repository
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        if not params:
            params = []
        return self.conn.request_delete(method, params, description=_("Removing content overrides"))

    def activateMachine(self, consumerId: str, email: str, lang: str = None) -> Union[dict, None]:
        """
        Activate a subscription by machine, information is located in the consumer facts
        :param consumerId: consumer UUID
        :param email: The email for sending notification. The notification will be sent by candlepin server
        :param lang: The locale specifies the language of notification email
        :return When activation was successful, then dictionary is returned. Otherwise, None is returned.
        """
        method = "/subscriptions?consumer_uuid=%s" % consumerId
        method += "&email=%s" % self.sanitize(email)
        if (not lang) and (locale.getdefaultlocale()[0] is not None):
            lang = locale.getdefaultlocale()[0].lower().replace("_", "-")
        if lang:
            method += "&email_locale=%s" % self.sanitize(lang)
        return self.conn.request_post(method, description=_("Activating"))

    # used by virt-who
    def getJob(self, job_id: str) -> str:
        """
        Returns the status of a candlepin job.
        """
        query_params = urlencode({"result_data": True})
        method = "/jobs/%s?%s" % (job_id, query_params)
        results = self.conn.request_get(method, description=_("Fetching job"))
        return results

    def sanitize(self, url_param: str, plus: bool = False) -> str:
        """
        This is a wrapper around urllib.quote to avoid issues like the one
        discussed in http://bugs.python.org/issue9301
        :param url_param: String with URL parameter
        :param plus: If True, then replace ' ' with '+'
        :return: Sanitized string
        """
        if plus:
            sane_string = quote_plus(str(url_param))
        else:
            sane_string = quote(str(url_param))
        return sane_string
