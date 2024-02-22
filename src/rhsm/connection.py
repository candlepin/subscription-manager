from __future__ import print_function, division, absolute_import

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
import six
import socket
import sys
import time
import traceback
from typing import Optional
from pathlib import Path

from email.utils import format_datetime

from rhsm.https import httplib, ssl

from six.moves.urllib.request import proxy_bypass
from six.moves.urllib.parse import urlencode, quote, quote_plus

from rhsm.config import get_config_parser
from rhsm import ourjson as json
from rhsm import utils

try:
    import subscription_manager.version
    subman_version = subscription_manager.version.rpm_version
except ImportError:
    subman_version = "unknown"

config = get_config_parser()
MULTI_ENV = "multi_environment"


def safe_int(value, safe_value=None):
    try:
        return int(value)
    except Exception:
        return safe_value


def normalized_host(host):
    """
    When you want to use IPv6 address and port in e.g. HTTP header, then you cannot use following
    notation common for IPv4 (147.230.16.1:53). You have to use following notation for IPv6
    [2001:718:1c01:16::aa]:53.
    :param host: hostname or IPv4 or IPv6 address
    :return: When host is IPv6 address, then it encapsulated in [] brackets
    """
    if ':' in host:
        return '[%s]' % host
    else:
        return host


def drift_check(utc_time_string, hours=1):
    """
    Takes in a RFC 1123 date and returns True if the current time
    is greater then the supplied number of hours
    """
    drift = False
    if utc_time_string:
        try:
            # This may have a timezone (utc)
            utc_datetime = dateutil.parser.parse(utc_time_string)
            # This should not have a timezone, but we know it will be utc.
            # We need our timezones to match in order to compare
            local_datetime = datetime.datetime.utcnow().replace(tzinfo=utc_datetime.tzinfo)
            delta = datetime.timedelta(hours=hours)
            drift = abs((utc_datetime - local_datetime)) > delta
        except Exception as e:
            log.error(e)

    return drift


class NullHandler(logging.Handler):
    def emit(self, record):
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
    """ Thrown when an error parsing a certificate is encountered. """

    def __init__(self, cert_path, ssl_exc):
        """ Pass the full path to the bad certificate. """
        self.cert_path = cert_path
        self.ssl_exc = ssl_exc

    def __str__(self):
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


class BaseConnection(object):
    def __init__(
            self,
            restlib_class=None,
            host=None,
            ssl_port=None,
            handler=None,
            ca_dir=None,
            insecure=None,
            proxy_hostname=None,
            proxy_port=None,
            proxy_user=None,
            proxy_password=None,
            no_proxy=None,
            username=None,
            password=None,
            cert_file=None,
            key_file=None,
            cert_dir=None,
            token=None,
            user_agent=None,
            correlation_id=None,
            timeout=None,
            **kwargs
    ):

        restlib_class = restlib_class or Restlib
        self.host = host or config.get('server', 'hostname')
        self.handler = handler or config.get('server', 'prefix')
        self.ssl_port = ssl_port or safe_int(config.get('server', 'port'))
        self.timeout = timeout or safe_int(config.get('server', 'server_timeout'))

        # allow specifying no_proxy via api or config
        no_proxy_override = no_proxy or config.get('server', 'no_proxy')
        if no_proxy_override:
            os.environ['no_proxy'] = no_proxy_override

        utils.fix_no_proxy()
        log.debug('Environment variable NO_PROXY=%s will be used' % no_proxy_override)

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
                self.proxy_hostname = config.get('server', 'proxy_hostname') or info['proxy_hostname']
            if proxy_port is not None:
                self.proxy_port = proxy_port
            else:
                self.proxy_port = config.get('server', 'proxy_port') or info['proxy_port']
            if proxy_user is not None:
                self.proxy_user = proxy_user
            else:
                self.proxy_user = config.get('server', 'proxy_user') or info['proxy_username']
            if proxy_password is not None:
                self.proxy_password = proxy_password
            else:
                self.proxy_password = config.get('server', 'proxy_password') or info['proxy_password']

        self.cert_file = cert_file
        self.key_file = key_file
        self.username = username
        self.password = password
        self.token = token

        self.ca_dir = ca_dir or config.get('rhsm', 'ca_cert_dir')
        self.ssl_verify_depth = safe_int(config.get('server', 'ssl_verify_depth'))

        self.insecure = insecure
        if insecure is None:
            self.insecure = False
            config_insecure = safe_int(config.get('server', 'insecure'))
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

        if len([value for value in (
            using_basic_auth,
            using_id_cert_auth,
            using_keycloak_auth,
            using_ent_cert_auth
        ) if value]) > 1:
            raise Exception("Cannot specify multiple auth types")

        proxy_description = None
        if self.proxy_hostname and self.proxy_port:
            proxy_description = "http_proxy=%s:%s " % \
                                (normalized_host(self.proxy_hostname),
                                 safe_int(self.proxy_port))
        # initialize connection
        self.conn = restlib_class(self.host, self.ssl_port, self.handler,
                                  username=self.username, password=self.password,
                                  token=self.token, cert_file=self.cert_file, key_file=self.key_file,
                                  proxy_hostname=self.proxy_hostname, proxy_port=self.proxy_port,
                                  proxy_user=self.proxy_user, proxy_password=self.proxy_password,
                                  ca_dir=self.ca_dir, insecure=self.insecure, cert_dir=cert_dir,
                                  ssl_verify_depth=self.ssl_verify_depth, timeout=self.timeout,
                                  correlation_id=correlation_id, user_agent=user_agent)

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

    def __init__(self, realm, auth_url, resource, **kwargs):
        host = six.moves.urllib.parse.urlparse(auth_url).hostname or ''
        handler = six.moves.urllib.parse.urlparse(auth_url).path
        ssl_port = six.moves.urllib.parse.urlparse(auth_url).port or 443
        super(KeycloakConnection, self).__init__(host=host, ssl_port=ssl_port, handler=handler, **kwargs)
        self.realm = realm
        self.resource = resource

    def get_access_token_through_refresh(self, refreshtoken):
        # Get access token in exchange for refresh token
        method = "/realms/" + self.realm + "/protocol/openid-connect/token"
        params = {"client_id": self.resource, "grant_type": "refresh_token", "refresh_token": refreshtoken}
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        try:
            data = self.conn.request_post(method, params, headers)
            return data['access_token']
        except RestlibException as e:
            if e.code == 400:
                raise TokenAuthException(e.msg)
            raise


class RestlibException(ConnectionException):
    """
    Raised when a response with a valid json body is received along with a status code
    that is not in [200, 202, 204, 410, 429]
    See RestLib.validateResponse to see when this and other exceptions are raised.
    """

    def __init__(self, code, msg=None, headers=None):
        self.code = code
        self.msg = msg or ""
        self.headers = headers or {}

    @property
    def title(self):
        return httplib.responses.get(self.code, "Unknown")

    def __str__(self):
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
    def __init__(self, code, msg, deleted_id):
        # Exception doesn't inherit from object on el5 python version
        RestlibException.__init__(self, code, msg)
        self.deleted_id = deleted_id


class UnknownContentException(ConnectionException):
    """
    Thrown when the response of a request has no valid json content
    and the http status code is anything other than the following:
    [200, 202, 204, 401, 403, 410, 429, 500, 502, 503, 504]
    """

    def __init__(self, code: int, content_type: Optional[str] = None, content: Optional[str] = None):
        self.code = code
        self.content_type = content_type
        self.content = content

    @property
    def title(self) -> str:
        return httplib.responses.get(self.code, "Unknown")

    def __str__(self):
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
    def __init__(self, code,
                 request_type=None,
                 handler=None):
        self.code = code
        self.request_type = request_type
        self.handler = handler

    def __str__(self):
        if self.request_type and self.handler:
            return "Server error attempting a %s to %s returned status %s" % (self.request_type,
                                                                              self.handler,
                                                                              self.code)
        return "Server returned %s" % self.code


class AuthenticationException(RemoteServerException):
    prefix = "Authentication error"

    def __str__(self):
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
    def __init__(self, code, msg=None, headers=None):
        super(RateLimitExceededException, self).__init__(code, msg)
        self.headers = headers or {}
        self.retry_after = safe_int(self.headers.get('retry-after'))
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
    encoded = base64.b64encode(':'.join((username, password)).encode('utf-8')).decode('utf-8')
    return 'Basic %s' % encoded


# FIXME: this is terrible, we need to refactor
# Restlib to be Restlib based on a https client class
class ContentConnection(BaseConnection):
    def __init__(self, cert_dir=None, **kwargs):
        log.debug("ContentConnection")
        user_agent = "RHSM-content/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)
        if 'client_version' in kwargs:
            user_agent += kwargs['client_version']
        cert_dir = cert_dir or '/etc/pki/entitlement'
        super(ContentConnection, self).__init__(handler='/', cert_dir=cert_dir, user_agent=user_agent,
                                                **kwargs)

    def get_versions(self, path, cert_key_pairs=None):
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

    def _get_versions_for_product(self, product_id):
        pass


def _get_locale():
    l = None
    try:
        l = locale.getlocale()
    except (locale.Error, ValueError):
        try:
            l = locale.getdefaultlocale()
        except locale.Error:
            pass
        except ValueError:
            pass

    if l and l != (None, None):
        return l[0]

    return None


class BaseRestLib(object):
    """
    A low-level wrapper around httplib
    to make rest calls easy and expose the details of
    responses
    """

    ALPHA = 0.9

    def __init__(self, host, ssl_port, apihandler,
                 username=None, password=None,
                 proxy_hostname=None, proxy_port=None,
                 proxy_user=None, proxy_password=None,
                 cert_file=None, key_file=None, cert_dir=None,
                 ca_dir=None, insecure=False, ssl_verify_depth=1, timeout=None,
                 correlation_id=None, token=None, user_agent=None):
        self.host = host
        self.ssl_port = ssl_port
        self.apihandler = apihandler

        # Default, updated by UepConnection
        self.user_agent = user_agent or "python-rhsm-user-agent"

        self.headers = {"Content-type": "application/json",
                        "Accept": "application/json",
                        "x-subscription-manager-version": subman_version}

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
        self.ssl_verify_depth = ssl_verify_depth
        self.proxy_hostname = proxy_hostname
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password
        self.smoothed_rt = None
        self.token = token
        # We set this to None, because we don't know the truth unless we get
        # first response from the server using cert/key connection
        self.is_consumer_cert_key_valid = None

        # Setup basic authentication if specified:
        if username and password:
            self.headers['Authorization'] = _encode_auth(username, password)
        elif token:
            self.headers['Authorization'] = 'Bearer ' + token

    def _get_cert_key_list(self):
        """
        Create list of cert-key pairs to be used with the connection
        """

        cert_key_pairs = []

        if self.cert_dir is None:
            return [(self.cert_file, self.key_file)]

        for cert_file in os.listdir(self.cert_dir):
            if cert_file.endswith(".pem") and not cert_file.endswith("-key.pem"):
                cert_path = os.path.join(self.cert_dir, cert_file)
                key_path = os.path.join(self.cert_dir, "%s-key.pem" % cert_file.split('.', 1)[0])
                cert_key_pairs.append((cert_path, key_path))

        return cert_key_pairs

    def _load_ca_certificates(self, context):
        """
        Tries to load CA certificates to SSL context
        :param context: SSL context
        :return: None
        """
        if not os.path.isdir(self.ca_dir):
            log.warning('Directory "%s" with CA certificates is missing' % self.ca_dir)
            return None

        loaded_ca_certs = []
        cert_path = ''
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
            log.debug("Loaded CA certificates from %s: %s" % (self.ca_dir, ', '.join(loaded_ca_certs)))
        else:
            log.warning("Unable to load any CA certificate from: %s" % self.ca_dir)

    def _create_connection(self, cert_file=None, key_file=None):
        # See M2Crypto/SSL/Context.py in m2crypto source and
        # https://www.openssl.org/docs/ssl/SSL_CTX_new.html
        # This ends up invoking SSLv23_method, which is the catch all
        # "be compatible" protocol, even though it explicitly is not
        # using sslv2. This will by default potentially include sslv3
        # if not used with post-poodle openssl. If however, the server
        # intends to not offer sslv3, it's workable.
        #
        # So this supports tls1.2, 1.1, 1.0, and/or sslv3 if supported.
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

        # Disable SSLv2 and SSLv3 support to avoid poodles.
        context.options = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3

        if self.insecure:  # allow clients to work insecure mode if required..
            context.verify_mode = ssl.CERT_NONE
        else:
            context.verify_mode = ssl.CERT_REQUIRED
            if self.ca_dir is not None:
                self._load_ca_certificates(context)
        if cert_file and os.path.exists(cert_file):
            context.load_cert_chain(cert_file, keyfile=key_file)

        if self.proxy_hostname and self.proxy_port:
            log.debug("Using proxy: %s:%s" % (normalized_host(self.proxy_hostname), safe_int(self.proxy_port)))
            proxy_headers = {
                'User-Agent': self.user_agent,
                'Host': '%s:%s' % (normalized_host(self.host), safe_int(self.ssl_port))
            }
            if self.proxy_user and self.proxy_password:
                proxy_headers['Proxy-Authorization'] = _encode_auth(self.proxy_user, self.proxy_password)
            conn = httplib.HTTPSConnection(self.proxy_hostname, self.proxy_port, context=context, timeout=self.timeout)
            conn.set_tunnel(self.host, safe_int(self.ssl_port), proxy_headers)
            self.headers['Host'] = '%s:%s' % (normalized_host(self.host), safe_int(self.ssl_port))
        else:
            conn = httplib.HTTPSConnection(self.host, self.ssl_port, context=context, timeout=self.timeout)

        return conn

    def _print_debug_info_about_request(self, request_type, handler, final_headers, body):
        """
        This method can print debug information about sent http request. We do not use
        httplib.HTTPConnection.debuglevel = 1, because it doesn't provide control about displayed information.
        The debug print is printed to stdout, when environment variable SUBMAN_DEBUG_PRINT_REQUEST is set.
        Output can be modified with following environment variables:
         * SUBMAN_DEBUG_PRINT_REQUEST_HEADER
         * SUBMAN_DEBUG_PRINT_REQUEST_BODY
        :param request_type: (GET, POST, PUT, ...)
        :param handler: e.g. /candlepin/status
        :param final_headers: HTTP header used by request
        :param body: request can contain body
        :return: None
        """

        if 'SUBMAN_DEBUG_PRINT_REQUEST' in os.environ:
            yellow_col = '\033[93m'
            magenta_col = "\033[95m"
            blue_col = '\033[94m'
            green_col = '\033[92m'
            red_col = '\033[91m'
            end_col = '\033[0m'
            if self.insecure is True:
                msg = blue_col + "Making insecure request:" + end_col
            else:
                msg = blue_col + "Making request:" + end_col
            msg += (
                    red_col +
                    " https://" +
                    f"{normalized_host(self.host)}:{safe_int(self.ssl_port)}{handler} {request_type}" +
                    end_col
            )
            if self.proxy_hostname and self.proxy_port:
                # Note: using only https:// is not a mistake. We use only https for proxy connection.
                msg += blue_col + " Using proxy: " + magenta_col + "https://"
                # Print username and eventually password
                if self.proxy_user:
                    if self.proxy_user and self.proxy_password:
                        msg += f"{self.proxy_user}:{self.proxy_password}@"
                    elif self.proxy_user and not self.proxy_password:
                        msg += f"{self.proxy_user}@"
                # Print hostname and port
                msg += f"{normalized_host(self.proxy_hostname)}:{safe_int(self.proxy_port)}"
                msg += end_col
            if 'SUBMAN_DEBUG_PRINT_REQUEST_HEADER' in os.environ:
                msg += blue_col + " %s" % final_headers + end_col
            if 'SUBMAN_DEBUG_PRINT_REQUEST_BODY' in os.environ and body is not None:
                msg += yellow_col + " %s" % body + end_col
            print()
            print(msg)
            print()
            if 'SUBMAN_DEBUG_SAVE_TRACEBACKS' in os.environ:
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

                print(green_col + f'Traceback saved to {str(debug_log)}.' + end_col)
                print()

    @staticmethod
    def _print_debug_info_about_response(result):
        """
        This method can print result of HTTP request to stdout, when environment variable SUBMAN_DEBUG_PRINT_RESPONSE
        is set.
        :param result: response from candlepin server
        :return: None
        """

        if 'SUBMAN_DEBUG_PRINT_RESPONSE' in os.environ:
            print('%s %s' % (result['status'], result['headers']))
            print(result['content'])
            print()

    def _set_accept_language_in_header(self):
        """
        Set accept language in http header according current settings or environment variable
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
            self.headers["Accept-Language"] = lc.lower().replace('_', '-').split('.', 1)[0]

    # FIXME: can method be empty?
    def _request(self, request_type, method, info=None, headers=None, cert_key_pairs=None):
        handler = self.apihandler + method

        # We try to import it here to get fresh value, because rhsm.service can receive
        # several D-BUS API calls with different locale argument (every request have to have
        # different locale)
        self._set_accept_language_in_header()

        # Load certificates from cert dir if specified
        if cert_key_pairs is None or len(cert_key_pairs) == 0:
            cert_key_pairs = self._get_cert_key_list()

        if headers is not None and \
                'Content-type' in headers and \
                headers['Content-type'] == 'application/x-www-form-urlencoded':
            body = six.moves.urllib.parse.urlencode(info).encode('utf-8')
        elif info is not None:
            body = json.dumps(info, default=json.encode)
        else:
            body = None

        log.debug("Making request: %s %s" % (request_type, handler))

        if self.user_agent:
            self.headers['User-Agent'] = self.user_agent

        final_headers = self.headers.copy()
        if body is None:
            final_headers["Content-Length"] = "0"
        if headers:
            final_headers.update(headers)

        self._print_debug_info_about_request(request_type, handler, final_headers, body)

        response = None
        result = None
        for cert_file, key_file in cert_key_pairs:
            try:
                conn = self._create_connection(cert_file=cert_file, key_file=key_file)
                ts_start = time.time()
                conn.request(request_type, handler, body=body, headers=final_headers)
                ts_end = time.time()
                response = conn.getresponse()
                self._update_smoothed_response_time(ts_end - ts_start)

                result = {
                     "content": response.read().decode('utf-8'),
                     "status": response.status,
                     "headers": dict(response.getheaders())
                }
                if response.status == 200:
                    self.is_consumer_cert_key_valid = True
                    break  # this client cert worked, no need to try more
                elif self.cert_dir:
                    log.debug("Unable to get valid response: %s from CDN: %s" %
                              (result, normalized_host(self.host)))

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
                if isinstance(err, ConnectionError) \
                    and self.proxy_hostname and self.proxy_port:
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port, exc=err)
                if six.PY2:
                    code = httplib.PROXY_AUTHENTICATION_REQUIRED
                else:
                    code = httplib.PROXY_AUTHENTICATION_REQUIRED.value
                if str(code) in str(err):
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port, exc=err)
                # in case this OSError does not have an errno set, it means it was
                # not a syscall failure; mostly (if at all) this is raisen on proxy
                # connection failures
                if err.errno is None:
                    # wrap this to carry also the details on the destination host
                    raise ConnectionOSErrorException(self.host, self.ssl_port, self.apihandler, err)
                raise

        else:
            if self.cert_dir:
                raise NoValidEntitlement(
                    "Cannot access CDN content on: %s using any of entitlement cert-key pair: %s" %
                    (normalized_host(self.host), cert_key_pairs)
                )

        self._print_debug_info_about_response(result)

        response_log = 'Response: status=' + str(result['status'])
        if response.getheader('x-candlepin-request-uuid'):
            response_log = "%s, requestUuid=%s" % (response_log, response.getheader('x-candlepin-request-uuid'))
        response_log = "%s, request=\"%s %s\"" % (response_log, request_type, handler)
        log.debug(response_log)

        # Look for server drift, and log a warning
        if drift_check(response.getheader('date')):
            log.warning("Clock skew detected, please check your system time")

        # FIXME: we should probably do this in a wrapper method
        # so we can use the request method for normal http

        self.validateResponse(result, request_type, handler)

        return result

    def _update_smoothed_response_time(self, response_time):
        """
        Method for computing smoothed time of response. It is based on computing SRTT (See RFC 793).
        :param response_time: response time of the latest http request
        :return: None
        """
        if self.smoothed_rt is None:
            self.smoothed_rt = response_time
        else:
            self.smoothed_rt = (self.ALPHA * self.smoothed_rt) + ((1 - self.ALPHA) * response_time)
        log.debug("Response time: %s, Smoothed response time: %s" % (response_time, self.smoothed_rt))

    def validateResponse(self, response, request_type=None, handler=None):

        # FIXME: what are we supposed to do with a 204?
        if str(response['status']) not in ["200", "202", "204", "304"]:
            parsed = {}
            if not response.get('content'):
                parsed = {}
            else:
                # try vaguely to see if it had a json parseable body
                try:
                    parsed = json.loads(response['content'])
                except ValueError as e:
                    log.error("Response: %s" % response['status'])
                    log.error("JSON parsing error: %s" % e)
                except Exception as e:
                    log.error("Response: %s" % response['status'])
                    log.exception(e)

            if parsed:
                # Find and raise a GoneException on '410' with 'deletedId' in the
                # content, implying that the resource has been deleted.

                # NOTE: a 410 with a unparseable content will raise
                # RemoteServerException and will not cause the client
                # to delete the consumer cert.
                if str(response['status']) == "410":
                    raise GoneException(response['status'],
                                        parsed['displayMessage'],
                                        parsed['deletedId'])

                elif str(response['status']) == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port)

                # I guess this is where we would have an exception mapper if we
                # had more meaningful exceptions. We've gotten a response from
                # the server that means something.

                error_msg = self._parse_msg_from_error_response_body(parsed)
                if str(response['status']) in ['429']:
                    raise RateLimitExceededException(response['status'],
                                                     error_msg,
                                                     headers=response.get('headers'))

                if str(response['status']) in ["401"]:
                    # If the proxy is not configured correctly
                    # it connects to the server without the identity cert
                    # even if the cert is valid
                    if self.proxy_hostname:
                        if self.cert_file:
                            id_cert = certificate.create_from_file(self.cert_file)
                            if id_cert.is_valid():
                                raise RestlibException(response['status'],
                                                       ("Unable to make a connection using SSL client certificate. "
                                                        "Please review proxy configuration and connectivity."),
                                                       response.get('headers'))

                # FIXME: we can get here with a valid json response that
                # could be anything, we don't verify it anymore
                raise RestlibException(response['status'], error_msg, response.get('headers'))
            else:
                # This really needs an exception mapper too...
                if str(response['status']) in ["404", "410", "500", "502", "503", "504"]:
                    raise RemoteServerException(response['status'],
                                                request_type=request_type,
                                                handler=handler)
                elif str(response['status']) in ["401"]:
                    raise UnauthorizedException(response['status'],
                                                request_type=request_type,
                                                handler=handler)
                elif str(response['status']) in ["403"]:
                    raise ForbiddenException(response['status'],
                                             request_type=request_type,
                                             handler=handler)
                elif str(response['status']) in ['429']:
                    raise RateLimitExceededException(response['status'],
                                                     headers=response.get('headers'))

                elif str(response['status']) == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                    raise ProxyException(hostname=self.proxy_hostname, port=self.proxy_port)

                else:
                    # unexpected with no valid content
                    raise UnknownContentException(
                        response['status'],
                        response.get("headers", {}).get("Content-Type"),
                        response.get("content"),
                    )

    def _parse_msg_from_error_response_body(self, body):

        # Old style with a single displayMessage:
        if 'displayMessage' in body:
            return body['displayMessage']

        # New style list of error messages:
        if 'errors' in body:
            return " ".join("%s" % errmsg for errmsg in body['errors'])

        # keycloak error messages
        if 'error_description' in body:
            return body['error_description']

    def request_get(self, method, headers=None, cert_key_pairs=None):
        return self._request("GET", method, headers=headers, cert_key_pairs=cert_key_pairs)

    def request_post(self, method, params=None, headers=None):
        return self._request("POST", method, params, headers=headers)

    def request_head(self, method, headers=None):
        return self._request("HEAD", method, headers=headers)

    def request_put(self, method, params=None, headers=None):
        return self._request("PUT", method, params, headers=headers)

    def request_delete(self, method, params=None, headers=None):
        return self._request("DELETE", method, params, headers=headers)

    @staticmethod
    def _format_http_date(dt):
        """
        Format a datetime to HTTP-date as described by RFC 7231.
        """
        return format_datetime(dt, usegmt=True)


# FIXME: it would be nice if the ssl server connection stuff
# was decomposed from the api handling parts
class Restlib(BaseRestLib):
    """
     A wrapper around httplib to make rest calls easier
     See validateResponse() to learn when exceptions are raised as a result
     of communication with the server.
    """

    def _request(self, request_type, method, info=None, headers=None, cert_key_pairs=None):
        result = super(Restlib, self)._request(request_type, method,
                                               info=info, headers=headers, cert_key_pairs=cert_key_pairs)

        # Handle 204s
        if not len(result['content']):
            return None

        try:
            return json.loads(result['content'])
        except json.JSONDecodeError:
            # This is primarily intended for getting releases from CDN, because
            # the file containing releases is plaintext and not json.
            return result['content']


class UEPConnection(BaseConnection):
    """
    Class for communicating with the REST interface of a Red Hat Unified
    Entitlement Platform.
    """

    def __init__(self, **kwargs):
        """
        Multiple ways to authenticate:
            - username/password for HTTP basic authentication. (owner admin role)
            - uuid/key_file/cert_file for identity cert authentication.
              (consumer role)
            - token (when supported by the server)

        Must specify only one method of authentication.
        """
        user_agent = "RHSM/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)
        if 'client_version' in kwargs:
            user_agent += kwargs['client_version']
        if 'dbus_sender' in kwargs:
            user_agent += kwargs['dbus_sender']
        super(UEPConnection, self).__init__(user_agent=user_agent, **kwargs)

    def _load_supported_resources(self):
        """
        Load the list of supported resources by doing a GET on the root
        of the web application we're configured to use.

        Need to handle exceptions here because sometimes UEPConnections are
        created in a state where they can't actually be used. (they get
        replaced later) If something goes wrong making this request, just
        leave the list of supported resources empty.
        """
        self.resources = {}
        resources_list = self.conn.request_get("/")
        for r in resources_list:
            self.resources[r['rel']] = r['href']
        log.debug("Server supports the following resources: %s",
                  self.resources)

    def get_supported_resources(self):
        """
        Get list of supported resources.
        :return: list of supported resources
        """
        if self.resources is None:
            self._load_supported_resources()

        return self.resources

    def supports_resource(self, resource_name: Optional[str]):
        """Check if the server supports a particular resource.

        :param resource_name:
            Resource to be requested.
            When `None`, API call `GET /` is made to cache all supported resources.
        """
        if self.resources is None:
            self._load_supported_resources()

        return resource_name in self.resources

    def _load_manager_capabilities(self):
        """
        Loads manager capabilities by doing a GET on the status
        resource located at '/status'
        """
        status = self.getStatus()
        capabilities = status.get('managerCapabilities')
        if capabilities is None:
            log.debug("The status retrieved did not \
                      include key 'managerCapabilities'.\nStatus:'%s'" % status)
            capabilities = []
        elif isinstance(capabilities, list) and not capabilities:
            log.debug("The managerCapabilities list \
                      was empty\nStatus:'%s'" % status)
        else:
            log.debug("Server has the following capabilities: %s", capabilities)
        return capabilities

    def has_capability(self, capability):
        """
        Check if the server we're connected to has a particular capability.
        """
        if self.capabilities is None:
            self.capabilities = self._load_manager_capabilities()
        return capability in self.capabilities

    def shutDown(self):
        self.conn.close()
        log.debug("remote connection closed")

    def ping(self, username=None, password=None):
        return self.conn.request_get("/status/")

    def getJWToken(self, cloud_id, metadata, signature):
        """
        When automatic registration is enabled in rhsm.conf and it was possible
        to gather cloud metadata, then it is possible to try to get JSON Web Token
        for automatic registration. When candlepin does not provide automatic
        registration, then raise exception.
        :param cloud_id: ID of cloud provider, e.g. "aws", "azure", "gcp"
        :param metadata: string with base64 encoded metadata
        :param signature: string with base64 encoded signature
        :return: string with JWT
        """
        params = {
            "type": cloud_id,
            "metadata": metadata,
            "signature": signature
        }
        # "Accept" http header has to be text/plain, because candlepin return
        # token as simple text and it is not wrapped in json document
        headers = {
            "Content-type": "application/json",
            "Accept": "text/plain"
        }
        return self.conn.request_post(
            method="/cloud/authorize",
            params=params,
            headers=headers
        )

    def registerConsumer(self, name="unknown", type="system", facts={},
            owner=None, environments=None, keys=None,
            installed_products=None, uuid=None, hypervisor_id=None,
            content_tags=None, role=None, addons=None, service_level=None, usage=None,
            jwt_token=None):
        """
        Creates a consumer on candlepin server
        """
        params = {"type": type,
                  "name": name,
                  "facts": facts}
        if installed_products:
            params['installedProducts'] = installed_products

        if uuid:
            params['uuid'] = uuid

        if hypervisor_id is not None:
            params['hypervisorId'] = {'hypervisorId': hypervisor_id}

        if content_tags is not None:
            params['contentTags'] = content_tags
        if role is not None:
            params['role'] = role
        if addons is not None:
            params['addOns'] = addons
        if usage is not None:
            params['usage'] = usage
        if service_level is not None:
            params['serviceLevel'] = service_level
        if environments is not None and self.has_capability(MULTI_ENV):
            env_list = []
            for environment in environments.split(','):
                env_list.append({"id": environment})
            params['environments'] = env_list

        headers = {}
        if jwt_token:
            headers['Authorization'] = 'Bearer {jwt_token}'.format(jwt_token=jwt_token)

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

        return self.conn.request_post(url, params, headers=headers)

    def hypervisorCheckIn(self, owner, env, host_guest_mapping, options=None):
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
        if (self.has_capability("hypervisors_async")):
            priorContentType = self.conn.headers['Content-type']
            self.conn.headers['Content-type'] = 'text/plain'

            params = {"env": env, "cloaked": False}
            if options and options.reporter_id and len(options.reporter_id) > 0:
                params['reporter_id'] = options.reporter_id

            query_params = urlencode(params)
            url = "/hypervisors/%s?%s" % (owner, query_params)
            res = self.conn.request_post(url, host_guest_mapping)
            self.conn.headers['Content-type'] = priorContentType
        else:
            # fall back to original report api
            # this results in the same json as in the result_data field
            # of the new api method
            query_params = urlencode({"owner": owner, "env": env})
            url = "/hypervisors?%s" % (query_params)
            res = self.conn.request_post(url, host_guest_mapping)
        return res

    def hypervisorHeartbeat(self, owner, options=None):
        """
        Sends the reporter id to candlepin
        to update the hypervisors it has previously reported.
        This method can raise the following exception:
            - RateLimitExceededException: This means that too many requests
            have been made in the given time period.
        """
        # Return None early if the connected UEP does not support hypervisors_heartbeat or if there is no reporter_id provided.
        if not self.has_capability("hypervisors_heartbeat") or not (options and options.reporter_id and len(options.reporter_id) > 0):
            return

        params = {}
        params['reporter_id'] = options.reporter_id
        query_params = urlencode(params)
        url = "/hypervisors/%s/heartbeat?%s" % (owner, query_params)
        return self.conn.request_put(url)

    def updateConsumerFacts(self, consumer_uuid, facts={}):
        """
        Update a consumers facts on candlepin server
        """
        return self.updateConsumer(consumer_uuid, facts=facts)

    def updateConsumer(self, uuid, facts=None, installed_products=None,
            guest_uuids=None, service_level=None, release=None,
            autoheal=None, hypervisor_id=None, content_tags=None, role=None, addons=None,
            usage=None, environments=None):
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
            params['installedProducts'] = installed_products
        if guest_uuids is not None:
            params['guestIds'] = self.sanitizeGuestIds(guest_uuids)
        if facts is not None:
            params['facts'] = facts
        if release is not None:
            params['releaseVer'] = release
        if autoheal is not None:
            params['autoheal'] = autoheal
        if hypervisor_id is not None:
            params['hypervisorId'] = {'hypervisorId': hypervisor_id}
        if content_tags is not None:
            params['contentTags'] = content_tags
        if role is not None:
            params['role'] = role
        if addons is not None:
            if isinstance(addons, list):
                params['addOns'] = addons
            elif isinstance(addons, six.text_type):
                params['addOns'] = [addons]
        if usage is not None:
            params['usage'] = usage
        if environments is not None:
            env_list = []
            for environment in environments.split(','):
                env_list.append({"id": environment})
            params['environments'] = env_list

        # The server will reject a service level that is not available
        # in the consumer's organization, so no need to check if it's safe
        # here:
        if service_level is not None:
            params['serviceLevel'] = service_level

        method = "/consumers/%s" % self.sanitize(uuid)
        ret = self.conn.request_put(method, params)
        return ret

    def addOrUpdateGuestId(self, uuid, guestId):
        if isinstance(guestId, six.string_types):
            guest_uuid = guestId
            guestId = {}
        else:
            guest_uuid = guestId['guestId']
        method = "/consumers/%s/guestids/%s" % (self.sanitize(uuid), self.sanitize(guest_uuid))
        return self.conn.request_put(method, guestId)

    def getGuestIds(self, uuid):
        method = "/consumers/%s/guestids" % self.sanitize(uuid)
        return self.conn.request_get(method)

    def getGuestId(self, uuid, guest_uuid):
        method = "/consumers/%s/guestids/%s" % (self.sanitize(uuid), self.sanitize(guest_uuid))
        return self.conn.request_get(method)

    def removeGuestId(self, uuid, guest_uuid):
        method = "/consumers/%s/guestids/%s" % (self.sanitize(uuid), self.sanitize(guest_uuid))
        return self.conn.request_delete(method)

    def sanitizeGuestIds(self, guestIds):
        return [self.sanitizeGuestId(guestId) for guestId in guestIds or []]

    def sanitizeGuestId(self, guestId):
        if isinstance(guestId, six.string_types):
            return guestId
        elif isinstance(guestId, dict) and "guestId" in list(guestId.keys()):
            if self.supports_resource('guestids'):
                # Upload full json
                return guestId
            # Does not support the full guestId json, use the id string
            return guestId["guestId"]

    def updatePackageProfile(self, consumer_uuid, pkg_dicts):
        """
        Updates the consumer's package profile on the server.

        pkg_dicts expected to be a list of dicts, each containing the
        package headers we're interested in. See profile.py.
        """
        method = "/consumers/%s/packages" % self.sanitize(consumer_uuid)
        return self.conn.request_put(method, pkg_dicts)

    def updateCombinedProfile(self, consumer_uuid, profile):
        """
        Updates the costumers' combined profile containing package profile,
        enabled repositories and dnf/yum modules.
        :param consumer_uuid: UUID of consumer
        :param profile: Combined profile
        :return: Dict containing response from HTTP server
        """
        method = "/consumers/%s/profiles" % self.sanitize(consumer_uuid)
        return self.conn.request_put(method, profile)

    # FIXME: username and password not used here
    def getConsumer(self, uuid, username=None, password=None):
        """
        Returns a consumer object with pem/key for existing consumers
        """
        method = '/consumers/%s' % self.sanitize(uuid)
        return self.conn.request_get(method)

    def getConsumers(self, owner=None):
        """
        Returns a list of consumers
        """
        method = '/consumers/'
        if owner:
            method = "%s?owner=%s" % (method, owner)

        return self.conn.request_get(method)

    def getCompliance(self, uuid, on_date=None):
        """
        Returns a compliance object with compliance status information
        """
        method = '/consumers/%s/compliance' % self.sanitize(uuid)
        if on_date:
            method = "%s?on_date=%s" % (method,
                    self.sanitize(on_date.isoformat(), plus=True))
        return self.conn.request_get(method)

    def getSyspurposeCompliance(self, uuid, on_date=None):
        """
        Returns a system purpose compliance object with compliance status information
        """
        method = '/consumers/%s/purpose_compliance' % self.sanitize(uuid)
        if on_date:
            method = "%s?on_date=%s" % (method,
                                        self.sanitize(on_date.isoformat(), plus=True))
        return self.conn.request_get(method)

    def getOwnerSyspurposeValidFields(self, owner_key):
        """
        Retrieves the system purpose settings available to an owner
        """
        method = '/owners/%s/system_purpose' % self.sanitize(owner_key)
        return self.conn.request_get(method)

    def createOwner(self, ownerKey, ownerDisplayName=None):
        params = {"key": ownerKey}
        if ownerDisplayName:
            params['displayName'] = ownerDisplayName
        method = '/owners/'
        return self.conn.request_post(method, params)

    def getOwner(self, uuid):
        """
        Returns an owner object with pem/key for existing consumers
        """
        method = '/consumers/%s/owner' % self.sanitize(uuid)
        return self.conn.request_get(method)

    def deleteOwner(self, key):
        """
        deletes an owner
        """
        method = '/owners/%s' % self.sanitize(key)
        return self.conn.request_delete(method)

    def getOwners(self):
        """
        Returns a list of all owners
        """
        method = '/owners'
        return self.conn.request_get(method)

    def getOwnerInfo(self, owner):
        """
        Returns an owner info
        """
        method = '/owners/%s/info' % self.sanitize(owner)
        return self.conn.request_get(method)

    def getOwnerList(self, username):
        """
        Returns an owner objects with pem/key for existing consumers
        """
        method = '/users/%s/owners' % self.sanitize(username)
        owners = self.conn.request_get(method)
        # BZ 1749395 When a user has no orgs, the return value
        #  is an array with a single None element.
        # Ensures the value is the same for a simple None value
        owners = [x for x in (owners or []) if x is not None]
        return owners

    def getOwnerHypervisors(self, owner_key, hypervisor_ids=None):
        """
        If hypervisor_ids is populated, only hypervisors with those ids will be returned
        """
        method = '/owners/%s/hypervisors?' % owner_key
        for hypervisor_id in hypervisor_ids or []:
            method += '&hypervisor_id=%s' % self.sanitize(hypervisor_id)
        return self.conn.request_get(method)

    def unregisterConsumer(self, consumerId):
        """
         Deletes a consumer from candlepin server
        """
        method = '/consumers/%s' % self.sanitize(consumerId)
        return self.conn.request_delete(method)

    def getCertificates(self, consumer_uuid, serials=[]):
        """
        Fetch all entitlement certificates for this consumer.
        Specify a list of serial numbers to filter if desired.
        """
        method = '/consumers/%s/certificates' % (self.sanitize(consumer_uuid))
        if len(serials) > 0:
            serials_str = ','.join(serials)
            method = "%s?serials=%s" % (method, serials_str)
        return self.conn.request_get(method)

    def getCertificateSerials(self, consumerId):
        """
        Get serial numbers for certs for a given consumer
        """
        method = '/consumers/%s/certificates/serials' % self.sanitize(consumerId)
        return self.conn.request_get(method)

    def getAccessibleContent(self, consumerId, if_modified_since=None):
        """
        Get the content of the accessible content cert for a given consumer.

        :param consumerId: consumer id
        :param if_modified_since: if present, only return the content if it was altered since the given date
        :return: json with the last modified date and the content
        """
        method = "/consumers/%s/accessible_content" % consumerId
        headers = {}
        if if_modified_since:
            timestamp = BaseRestLib._format_http_date(if_modified_since)
            headers["If-Modified-Since"] = timestamp
        return self.conn.request_get(method, headers=headers)

    def bindByEntitlementPool(self, consumerId, poolId, quantity=None):
        """
         Subscribe consumer to a subscription by pool ID.
        """
        method = "/consumers/%s/entitlements?pool=%s" % (self.sanitize(consumerId), self.sanitize(poolId))
        if quantity:
            method = "%s&quantity=%s" % (method, quantity)
        return self.conn.request_post(method)

    def bindByProduct(self, consumerId, products):
        """
        Subscribe consumer directly to one or more products by their ID.
        This will cause the UEP to look for one or more pools which provide
        access to the given product.
        """
        args = "&".join(["product=" + product.replace(" ", "%20") for product in products])
        method = "/consumers/%s/entitlements?%s" % (str(consumerId), args)
        return self.conn.request_post(method)

    def bind(self, consumerId, entitle_date=None):
        """
        Same as bindByProduct, but assume the server has a list of the
        system's products. This is useful for autosubscribe. Note that this is
        done on a best-effort basis, and there are cases when the server will
        not be able to fulfill the client's product certs with entitlements.
        """
        method = "/consumers/%s/entitlements" % (self.sanitize(consumerId))

        # add the optional date to the url
        if entitle_date:
            method = "%s?entitle_date=%s" % (method,
                    self.sanitize(entitle_date.isoformat(), plus=True))

        return self.conn.request_post(method)

    def dryRunBind(self, consumer_uuid, service_level):
        """
        Performs a dry-run autobind on the server and returns the results of
        what we would get. Callers can use this information to determine if
        they wish to perform the autobind, and to explicitly grab entitlements
        from each pool returned.

        Return will be a dict containing a "quantity" and a "pool".
        """
        if service_level is None:
            method = "/consumers/%s/entitlements/dry-run" % self.sanitize(consumer_uuid)
        else:
            method = "/consumers/%s/entitlements/dry-run?service_level=%s" % \
                    (self.sanitize(consumer_uuid), self.sanitize(service_level))
        return self.conn.request_get(method)

    def unbindBySerial(self, consumerId, serial):
        method = "/consumers/%s/certificates/%s" % (self.sanitize(consumerId), self.sanitize(str(serial)))
        return self.conn.request_delete(method)

    def unbindByPoolId(self, consumer_uuid, pool_id):
        method = "/consumers/%s/entitlements/pool/%s" % (self.sanitize(consumer_uuid), self.sanitize(pool_id))
        return self.conn.request_delete(method)

    def unbindAll(self, consumerId):
        method = "/consumers/%s/entitlements" % self.sanitize(consumerId)
        return self.conn.request_delete(method)

    def checkin(self, consumerId, checkin_date=None):
        method = "/consumers/%s/checkin" % self.sanitize(consumerId)
        # add the optional date to the url
        if checkin_date:
            method = "%s?checkin_date=%s" % (method,
                    self.sanitize(checkin_date.isoformat(), plus=True))

        return self.conn.request_put(method)

    def getPoolsList(self, consumer=None, listAll=False, active_on=None, owner=None, filter_string=None, future=None,
                     after_date=None, page=0, items_per_page=0):
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
        if future in ('add', 'only'):
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

        results = self.conn.request_get(method)
        return results

    def getPool(self, poolId, consumerId=None):
        method = "/pools/%s" % self.sanitize(poolId)
        if consumerId:
            method = "%s?consumer=%s" % (method, self.sanitize(consumerId))
        return self.conn.request_get(method)

    def getProduct(self, product_uuid):
        method = "/products/%s" % self.sanitize(product_uuid)
        return self.conn.request_get(method)

    def getRelease(self, consumerId):
        method = "/consumers/%s/release" % self.sanitize(consumerId)
        results = self.conn.request_get(method)
        return results

    def getAvailableReleases(self, consumerId):
        """
        Gets the available content releases for a consumer.

        NOTE: Used for getting the available release versions
              from katello. In hosted candlepin scenario, the
              release versions will come from the CDN directly
              (API not implemented in candlepin).
        """
        method = "/consumers/%s/available_releases" % self.sanitize(consumerId)
        return self.conn.request_get(method)

    def getEntitlementList(self, consumerId, request_certs=False):
        method = "/consumers/%s/entitlements" % self.sanitize(consumerId)
        if not request_certs:
            # It is unnecessary to download the certificate and key here
            filters = "?exclude=certificates.key&exclude=certificates.cert"
        else:
            filters = ""
        results = self.conn.request_get(method + filters)
        return results

    def getServiceLevelList(self, owner_key):
        """
        List the service levels available for an owner.
        """
        method = "/owners/%s/servicelevels" % self.sanitize(owner_key)
        results = self.conn.request_get(method)
        return results

    def getEnvironmentList(self, owner_key):
        """
        List the environments for a particular owner.

        Some servers may not support this and will error out. The caller
        can always check with supports_resource("environments").
        """
        method = "/owners/%s/environments" % self.sanitize(owner_key)
        results = self.conn.request_get(method)
        return results

    def getEnvironment(self, owner_key=None, name=None):
        """
        Fetch an environment for an owner.

        If querying by name, owner is required as environment names are only
        unique within the context of an owner.

        TODO: Add support for querying by ID, this will likely hit an entirely
        different URL.
        """
        if name and not owner_key:
            raise Exception("Must specify owner key to query environment "
                    "by name")

        query_param = urlencode({"name": name})
        url = "/owners/%s/environments?%s" % (self.sanitize(owner_key), query_param)
        results = self.conn.request_get(url)
        if len(results) == 0:
            return None
        return results[0]

    def getEntitlement(self, entId):
        method = "/entitlements/%s" % self.sanitize(entId)
        return self.conn.request_get(method)

    def regenIdCertificate(self, consumerId):
        method = "/consumers/%s" % self.sanitize(consumerId)
        return self.conn.request_post(method)

    def regenEntitlementCertificates(self, consumer_id, lazy_regen=True):
        """
        Regenerates all entitlements for the given consumer
        """

        method = "/consumers/%s/certificates" % self.sanitize(consumer_id)

        if lazy_regen:
            method += "?lazy_regen=true"

        result = False

        try:
            self.conn.request_put(method)
            result = True
        except (RemoteServerException, httplib.BadStatusLine, RestlibException) as e:
            # 404s indicate that the service is unsupported (Candlepin too old, or SAM)
            if isinstance(e, httplib.BadStatusLine) or str(e.code) == "404":
                log.debug("Unable to refresh entitlement certificates: Service currently unsupported.")
                log.debug(e)
            else:
                # Something else happened that we should probabaly raise
                raise e

        return result

    def regenEntitlementCertificate(self, consumer_id, entitlement_id, lazy_regen=True):
        """
        Regenerates the specified entitlement for the given consumer
        """

        method = "/consumers/%s/certificates?entitlement=%s" % (self.sanitize(consumer_id), self.sanitize(entitlement_id))

        if lazy_regen:
            method += "&lazy_regen=true"

        result = False

        try:
            self.conn.request_put(method)
            result = True
        except (RemoteServerException, httplib.BadStatusLine, RestlibException) as e:
            # 404s indicate that the service is unsupported (Candlepin too old, or SAM)
            if isinstance(e, httplib.BadStatusLine) or str(e.code) == "404":
                log.debug("Unable to refresh entitlement certificates: Service currently unsupported.")
                log.debug(e)
            else:
                # Something else happened that we should probabaly raise
                raise e

        return result

    def getStatus(self):
        method = "/status"
        return self.conn.request_get(method)

    def getContentOverrides(self, consumerId):
        """
        Get all the overrides for the specified consumer.
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        return self.conn.request_get(method)

    def setContentOverrides(self, consumerId, overrides):
        """
        Set an override on a content object.
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        return self.conn.request_put(method, overrides)

    def deleteContentOverrides(self, consumerId, params=None):
        """
        Delete an override on a content object.
        """
        method = "/consumers/%s/content_overrides" % self.sanitize(consumerId)
        if not params:
            params = []
        return self.conn.request_delete(method, params)

    def activateMachine(self, consumerId, email=None, lang=None):
        """
        Activate a subscription by machine, information is located in the
        consumer facts
        """
        method = "/subscriptions?consumer_uuid=%s" % consumerId
        if email:
            method += "&email=%s" % email
            if (not lang) and (locale.getdefaultlocale()[0] is not None):
                lang = locale.getdefaultlocale()[0].lower().replace('_', '-')

            if lang:
                method += "&email_locale=%s" % lang
        return self.conn.request_post(method)

    def getSubscriptionList(self, owner_key):
        """
        List the subscriptions for a particular owner.
        """
        method = "/owners/%s/subscriptions" % self.sanitize(owner_key)
        results = self.conn.request_get(method)
        return results

    def updateSubscriptionList(self, owner_key, auto_create_owner=None, lazy_regen=None):
        """
        Update subscriptions for a particular owner.
        """
        method = "/owners/%s/subscriptions?" % self.sanitize(owner_key)

        if auto_create_owner is not None:
            method += "&auto_create_owner=%s" % bool(auto_create_owner).lower()
        if lazy_regen is not None:
            method += "&lazy_regen=%s" % bool(lazy_regen).lower()

        results = self.conn.request_put(method)
        return results

    def getJob(self, job_id):
        """
        Returns the status of a candlepin job.
        """
        query_params = urlencode({"result_data": True})
        method = "/jobs/%s?%s" % (job_id, query_params)
        results = self.conn.request_get(method)
        return results

    def updateJobStatus(self, job_status):
        """
        Given a dict representing a candlepin JobStatus, check it's status.
        """
        # let key error bubble up
        method = job_status['statusPath']
        results = self.conn.request_get(method)
        return results

    def cancelJob(self, job_id):
        """
        Given a job id representing a candlepin JobStatus, cancel it.
        """
        method = "/jobs/%s" % (job_id)
        results = self.conn.request_delete(method)
        return results

    def sanitize(self, url_param, plus=False):
        # This is a wrapper around urllib.quote to avoid issues like the one
        # discussed in http://bugs.python.org/issue9301
        if plus:
            sane_string = quote_plus(str(url_param))
        else:
            sane_string = quote(str(url_param))
        return sane_string
