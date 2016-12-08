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
import certificate
import datetime
import dateutil.parser
import locale
import logging
import os
import socket
import sys
import urllib

from rhsm.https import httplib, ssl

from urllib import urlencode

from config import initConfig

import version
python_rhsm_version = version.rpm_version

try:
    import subscription_manager.version
    subman_version = subscription_manager.version.rpm_version
except ImportError:
    subman_version = "unknown"

from rhsm import ourjson as json
from rhsm import utils

config = initConfig()


def safe_int(value, safe_value=None):
    try:
        return int(value)
    except Exception:
        return safe_value


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


class ConnectionException(Exception):
    pass


class ProxyException(Exception):
    pass


class ConnectionSetupException(ConnectionException):
    pass


class BadCertificateException(ConnectionException):
    """ Thrown when an error parsing a certificate is encountered. """

    def __init__(self, cert_path):
        """ Pass the full path to the bad certificate. """
        self.cert_path = cert_path

    def __str__(self):
        return "Bad certificate at %s" % self.cert_path


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

    def __str__(self):
        return self.msg


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


class NetworkException(ConnectionException):
    """
    Thrown when the response of a request has no valid json content
    and the http status code is anything other than the following:
    [200, 202, 204, 401, 403, 410, 429, 500, 502, 503, 504]
    """

    def __init__(self, code):
        self.code = code

    def __str__(self):
        return "Network error code: %s" % self.code


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
    def __init__(self, code,
                 msg=None,
                 headers=None):
        super(RateLimitExceededException, self).__init__(code,
                                                         msg)
        self.headers = headers or {}
        self.msg = msg or ""
        self.retry_after = safe_int(self.headers.get('retry-after'))


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
    encoded = base64.b64encode(':'.join((username, password)))
    return 'Basic %s' % encoded


# FIXME: this is terrible, we need to refactor
# Restlib to be Restlib based on a https client class
class ContentConnection(object):
    def __init__(self, host, ssl_port=None,
                 username=None, password=None,
                 proxy_hostname=None, proxy_port=None,
                 proxy_user=None, proxy_password=None,
                 ca_dir=None, insecure=False,
                 ssl_verify_depth=1, timeout=None):

        log.debug("ContentConnection")
        # FIXME
        self.ent_dir = "/etc/pki/entitlement"
        self.handler = "/"
        self.ssl_verify_depth = ssl_verify_depth

        self.host = host or config.get('server', 'hostname')
        self.ssl_port = ssl_port or safe_int(config.get('server', 'port'))
        self.timeout = timeout or safe_int(config.get('server', 'server_timeout'))
        self.ca_dir = ca_dir
        self.insecure = insecure
        self.username = username
        self.password = password
        self.ssl_verify_depth = ssl_verify_depth

        # honor no_proxy environment variable
        if urllib.proxy_bypass_environment(self.host):
            self.proxy_hostname = None
            self.proxy_port = None
            self.proxy_user = None
            self.proxy_password = None
        else:
            info = utils.get_env_proxy_info()

            self.proxy_hostname = proxy_hostname or config.get('server', 'proxy_hostname') or info['proxy_hostname']
            self.proxy_port = proxy_port or config.get('server', 'proxy_port') or info['proxy_port']
            self.proxy_user = proxy_user or config.get('server', 'proxy_user') or info['proxy_username']
            self.proxy_password = proxy_password or config.get('server', 'proxy_password') or info['proxy_password']

    @property
    def user_agent(self):
        return "RHSM-content/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)

    def _request(self, request_type, handler, body=None):
        # See note in Restlib._request
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

        # Disable SSLv2 and SSLv3 support to avoid poodles.
        context.options = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3

        self._load_ca_certificates(context)

        if self.proxy_hostname and self.proxy_port:
            log.debug("Using proxy: %s:%s" % (self.proxy_hostname, self.proxy_port))
            proxy_headers = {'User-Agent': self.user_agent}
            if self.proxy_user and self.proxy_password:
                proxy_headers['Proxy-Authorization'] = _encode_auth(self.proxy_user, self.proxy_password)
            conn = httplib.HTTPSConnection(self.proxy_hostname, self.proxy_port, context=context, timeout=self.timeout)
            conn.set_tunnel(self.host, safe_int(self.ssl_port), proxy_headers)
        else:
            conn = httplib.HTTPSConnection(self.host, self.ssl_port, context=context, timeout=self.timeout)

        conn.request("GET", handler,
                     body="",
                     headers={"Host": "%s:%s" % (self.host, self.ssl_port),
                              "Content-Length": "0",
                              "User-Agent": self.user_agent})
        response = conn.getresponse()
        result = {
            "content": response.read(),
            "status": response.status,
            "headers": dict(response.getheaders())}

        return result

    def _load_ca_certificates(self, context):
        try:
            for cert_file in os.listdir(self.ent_dir):
                if cert_file.endswith(".pem") and not cert_file.endswith("-key.pem"):
                    cert_path = os.path.join(self.ent_dir, cert_file)
                    key_path = os.path.join(self.ent_dir, "%s-key.pem" % cert_file.split('.', 1)[0])
                    log.debug("Loading CA certificate: '%s'" % cert_path)

                    # FIXME: reenable res =
                    context.load_verify_locations(cert_path)
                    context.load_cert_chain(cert_path, key_path)
                    # if res == 0:
                    #     raise BadCertificateException(cert_path)
        except OSError as e:
            raise ConnectionSetupException(e.strerror)

    def test(self):
        pass

    def request_get(self, method):
        return self._request("GET", method)

    def get_versions(self, path):
        handler = "%s/%s" % (self.handler, path)
        results = self._request("GET", handler, body="")

        if results['status'] == 200:
            return results['content']
        return ''

    def _get_versions_for_product(self, product_id):
        pass


def _get_locale():
    l = None
    try:
        l = locale.getlocale()
    except locale.Error:
        pass

    try:
        l = locale.getdefaultlocale()
    except locale.Error:
        pass
    except ValueError:
        pass

    if l and l != (None, None):
        return l[0]

    return None


# FIXME: it would be nice if the ssl server connection stuff
# was decomposed from the api handling parts
class Restlib(object):
    """
     A wrapper around httplib to make rest calls easier
     See validateResponse() to learn when exceptions are raised as a result
     of communication with the server.
    """
    def __init__(self, host, ssl_port, apihandler,
            username=None, password=None,
            proxy_hostname=None, proxy_port=None,
            proxy_user=None, proxy_password=None,
            cert_file=None, key_file=None,
            ca_dir=None, insecure=False, ssl_verify_depth=1, timeout=None):
        self.host = host
        self.ssl_port = ssl_port
        self.apihandler = apihandler
        lc = _get_locale()

        # Default, updated by UepConnection
        self.user_agent = "python-rhsm-user-agent"

        self.headers = {"Content-type": "application/json",
                        "Accept": "application/json",
                        "x-python-rhsm-version": python_rhsm_version,
                        "x-subscription-manager-version": subman_version}

        if lc:
            self.headers["Accept-Language"] = lc.lower().replace('_', '-')

        self.cert_file = cert_file
        self.key_file = key_file
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

        # Setup basic authentication if specified:
        if username and password:
            self.headers['Authorization'] = _encode_auth(username, password)

    def _decode_list(self, data):
        rv = []
        for item in data:
            if isinstance(item, unicode):
                item = item.encode('utf-8')
            elif isinstance(item, list):
                item = self._decode_list(item)
            elif isinstance(item, dict):
                item = self._decode_dict(item)
            rv.append(item)
        return rv

    def _decode_dict(self, data):
        rv = {}
        for key, value in data.iteritems():
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            elif isinstance(value, list):
                value = self._decode_list(value)
            elif isinstance(value, dict):
                value = self._decode_dict(value)
            rv[key] = value
        return rv

    def _load_ca_certificates(self, context):
        loaded_ca_certs = []
        try:
            for cert_file in os.listdir(self.ca_dir):
                if cert_file.endswith(".pem"):
                    cert_path = os.path.join(self.ca_dir, cert_file)
                    res = context.load_verify_locations(cert_path)
                    loaded_ca_certs.append(cert_file)
                    if res == 0:
                        raise BadCertificateException(cert_path)
        except OSError, e:
            raise ConnectionSetupException(e.strerror)

        if loaded_ca_certs:
            log.debug("Loaded CA certificates from %s: %s" % (self.ca_dir, ', '.join(loaded_ca_certs)))

    # FIXME: can method be empty?
    def _request(self, request_type, method, info=None):
        handler = self.apihandler + method

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
            context.check_hostname = False
        else:
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True
            if self.ca_dir is not None:
                self._load_ca_certificates(context)
        if self.cert_file and os.path.exists(self.cert_file):
            context.load_cert_chain(self.cert_file, keyfile=self.key_file)

        if self.proxy_hostname and self.proxy_port:
            log.debug("Using proxy: %s:%s" % (self.proxy_hostname, self.proxy_port))
            proxy_headers = {'User-Agent': self.user_agent}
            if self.proxy_user and self.proxy_password:
                proxy_headers['Proxy-Authorization'] = _encode_auth(self.proxy_user, self.proxy_password)
            conn = httplib.HTTPSConnection(self.proxy_hostname, self.proxy_port, context=context, timeout=self.timeout)
            conn.set_tunnel(self.host, safe_int(self.ssl_port), proxy_headers)
        else:
            conn = httplib.HTTPSConnection(self.host, self.ssl_port, context=context, timeout=self.timeout)

        if info is not None:
            body = json.dumps(info, default=json.encode)
        else:
            body = None

        log.debug("Making request: %s %s" % (request_type, handler))

        if self.user_agent:
            self.headers['User-Agent'] = self.user_agent

        headers = self.headers
        if body is None:
            headers = dict(self.headers.items() +
                           {"Content-Length": "0"}.items())

        try:
            conn.request(request_type, handler, body=body, headers=headers)
        except ssl.SSLError:
            if self.cert_file:
                id_cert = certificate.create_from_file(self.cert_file)
                if not id_cert.is_valid():
                    raise ExpiredIdentityCertException()
            raise
        except socket.error, e:
            if str(e)[-3:] == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                raise ProxyException(e)
            raise
        response = conn.getresponse()
        result = {
            "content": response.read(),
            "status": response.status,
            "headers": dict(response.getheaders())
        }

        response_log = 'Response: status=' + str(result['status'])
        if response.getheader('x-candlepin-request-uuid'):
            response_log = "%s, requestUuid=%s" % (response_log,
                    response.getheader('x-candlepin-request-uuid'))
        response_log = "%s, request=\"%s %s\"" % (response_log,
            request_type, handler)
        log.info(response_log)

        # Look for server drift, and log a warning
        if drift_check(response.getheader('date')):
            log.warn("Clock skew detected, please check your system time")

        # FIXME: we should probably do this in a wrapper method
        # so we can use the request method for normal http

        self.validateResponse(result, request_type, handler)

        # handle empty, but succesful responses, ala 204
        if not len(result['content']):
            return None

        return json.loads(result['content'], object_hook=self._decode_dict)

    def validateResponse(self, response, request_type=None, handler=None):

        # FIXME: what are we supposed to do with a 204?
        if str(response['status']) not in ["200", "202", "204"]:
            parsed = {}
            if not response.get('content'):
                parsed = {}
            else:
                # try vaguely to see if it had a json parseable body
                try:
                    parsed = json.loads(response['content'], object_hook=self._decode_dict)
                except ValueError, e:
                    log.error("Response: %s" % response['status'])
                    log.error("JSON parsing error: %s" % e)
                except Exception, e:
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
                    raise ProxyException

                # I guess this is where we would have an exception mapper if we
                # had more meaningful exceptions. We've gotten a response from
                # the server that means something.

                error_msg = self._parse_msg_from_error_response_body(parsed)
                if str(response['status']) in ['429']:
                    raise RateLimitExceededException(response['status'],
                                                     error_msg,
                                                     headers=response.get('headers'))

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
                    raise RateLimitExceededException(response['status'])

                elif str(response['status']) == str(httplib.PROXY_AUTHENTICATION_REQUIRED):
                    raise ProxyException

                else:
                    # unexpected with no valid content
                    raise NetworkException(response['status'])

    def _parse_msg_from_error_response_body(self, body):

        # Old style with a single displayMessage:
        if 'displayMessage' in body:
            return body['displayMessage']

        # New style list of error messages:
        if 'errors' in body:
            return " ".join("%s" % errmsg for errmsg in body['errors'])

    def request_get(self, method):
        return self._request("GET", method)

    def request_post(self, method, params=None):
        return self._request("POST", method, params)

    def request_head(self, method):
        return self._request("HEAD", method)

    def request_put(self, method, params=None):
        return self._request("PUT", method, params)

    def request_delete(self, method, params=None):
        return self._request("DELETE", method, params)


# FIXME: there should probably be a class here for just
# the connection bits, then a sub class for the api
# stuff
class UEPConnection:
    """
    Class for communicating with the REST interface of a Red Hat Unified
    Entitlement Platform.
    """

    def __init__(self,
            host=None,
            ssl_port=None,
            handler=None,
            proxy_hostname=None,
            proxy_port=None,
            proxy_user=None,
            proxy_password=None,
            username=None, password=None,
            cert_file=None, key_file=None,
            insecure=None,
            timeout=None):
        """
        Two ways to authenticate:
            - username/password for HTTP basic authentication. (owner admin role)
            - uuid/key_file/cert_file for identity cert authentication.
              (consumer role)

        Must specify one method of authentication or the other, not both.
        """
        self.host = host or config.get('server', 'hostname')
        self.ssl_port = ssl_port or safe_int(config.get('server', 'port'))
        self.handler = handler or config.get('server', 'prefix')
        self.timeout = timeout or safe_int(config.get('server', 'server_timeout'))

        # remove trailing "/" from the prefix if it is there
        # BZ848836
        self.handler = self.handler.rstrip("/")

        # honor no_proxy environment variable
        if urllib.proxy_bypass_environment(self.host):
            self.proxy_hostname = None
            self.proxy_port = None
            self.proxy_user = None
            self.proxy_password = None
        else:
            info = utils.get_env_proxy_info()

            self.proxy_hostname = proxy_hostname or config.get('server', 'proxy_hostname') or info['proxy_hostname']
            self.proxy_port = proxy_port or config.get('server', 'proxy_port') or info['proxy_port']
            self.proxy_user = proxy_user or config.get('server', 'proxy_user') or info['proxy_username']
            self.proxy_password = proxy_password or config.get('server', 'proxy_password') or info['proxy_password']

        self.cert_file = cert_file
        self.key_file = key_file
        self.username = username
        self.password = password

        self.ca_cert_dir = config.get('rhsm', 'ca_cert_dir')
        self.ssl_verify_depth = safe_int(config.get('server', 'ssl_verify_depth'))

        self.insecure = insecure
        if insecure is None:
            self.insecure = False
            config_insecure = safe_int(config.get('server', 'insecure'))
            if config_insecure:
                self.insecure = True

        using_basic_auth = False
        using_id_cert_auth = False

        if username and password:
            using_basic_auth = True
        elif cert_file and key_file:
            using_id_cert_auth = True

        if using_basic_auth and using_id_cert_auth:
            raise Exception("Cannot specify both username/password and "
                    "cert_file/key_file")
        # if not (using_basic_auth or using_id_cert_auth):
        #     raise Exception("Must specify either username/password or "
        #         "cert_file/key_file")

        proxy_description = None
        if self.proxy_hostname and self.proxy_port:
            proxy_description = "http_proxy=%s:%s " % (self.proxy_hostname, self.proxy_port)
        auth_description = None
        # initialize connection
        if using_basic_auth:
            self.conn = Restlib(self.host, self.ssl_port, self.handler,
                    username=self.username, password=self.password,
                    proxy_hostname=self.proxy_hostname, proxy_port=self.proxy_port,
                    proxy_user=self.proxy_user, proxy_password=self.proxy_password,
                    ca_dir=self.ca_cert_dir, insecure=self.insecure,
                    ssl_verify_depth=self.ssl_verify_depth, timeout=self.timeout)
            auth_description = "auth=basic username=%s" % username
        elif using_id_cert_auth:
            self.conn = Restlib(self.host, self.ssl_port, self.handler,
                                cert_file=self.cert_file, key_file=self.key_file,
                                proxy_hostname=self.proxy_hostname, proxy_port=self.proxy_port,
                                proxy_user=self.proxy_user, proxy_password=self.proxy_password,
                                ca_dir=self.ca_cert_dir, insecure=self.insecure,
                                ssl_verify_depth=self.ssl_verify_depth, timeout=self.timeout)
            auth_description = "auth=identity_cert ca_dir=%s insecure=%s" % (self.ca_cert_dir, self.insecure)
        else:
            self.conn = Restlib(self.host, self.ssl_port, self.handler,
                    proxy_hostname=self.proxy_hostname, proxy_port=self.proxy_port,
                    proxy_user=self.proxy_user, proxy_password=self.proxy_password,
                    ca_dir=self.ca_cert_dir, insecure=self.insecure,
                    ssl_verify_depth=self.ssl_verify_depth, timeout=self.timeout)
            auth_description = "auth=none"

        self.conn.user_agent = "RHSM/1.0 (cmd=%s)" % utils.cmd_name(sys.argv)

        self.resources = None
        self.capabilities = None
        connection_description = ""
        if proxy_description:
            connection_description += proxy_description
        connection_description += "host=%s port=%s handler=%s %s" % (self.host, self.ssl_port,
                                                                    self.handler, auth_description)
        log.info("Connection built: %s", connection_description)

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

    def supports_resource(self, resource_name):
        """
        Check if the server we're connecting too supports a particular
        resource. For our use cases this is generally the plural form
        of the resource.
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
        log.info("remote connection closed")

    def ping(self, username=None, password=None):
        return self.conn.request_get("/status/")

    def registerConsumer(self, name="unknown", type="system", facts={},
            owner=None, environment=None, keys=None,
            installed_products=None, uuid=None, hypervisor_id=None,
            content_tags=None):
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

        url = "/consumers"
        if environment:
            url = "/environments/%s/consumers" % self.sanitize(environment)
        elif owner:
            query_param = urlencode({"owner": owner})
            url = "%s?%s" % (url, query_param)
            prepend = ""
            if keys:
                url = url + "&activation_keys="
                for key in keys:
                    url = url + prepend + self.sanitize(key)
                    prepend = ","

        return self.conn.request_post(url, params)

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

    def updateConsumerFacts(self, consumer_uuid, facts={}):
        """
        Update a consumers facts on candlepin server
        """
        return self.updateConsumer(consumer_uuid, facts=facts)

    def updateConsumer(self, uuid, facts=None, installed_products=None,
            guest_uuids=None, service_level=None, release=None,
            autoheal=None, hypervisor_id=None, content_tags=None):
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

        # The server will reject a service level that is not available
        # in the consumer's organization, so no need to check if it's safe
        # here:
        if service_level is not None:
            params['serviceLevel'] = service_level

        method = "/consumers/%s" % self.sanitize(uuid)
        ret = self.conn.request_put(method, params)
        return ret

    def addOrUpdateGuestId(self, uuid, guestId):
        if isinstance(guestId, basestring):
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
        if isinstance(guestId, basestring):
            return guestId
        elif isinstance(guestId, dict) and "guestId" in guestId.keys():
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
        ret = self.conn.request_put(method, pkg_dicts)
        return ret

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
        return self.conn.request_get(method)

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

    def getPoolsList(self, consumer=None, listAll=False, active_on=None, owner=None, filter_string=None):
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
        if active_on:
            method = "%s&activeon=%s" % (method,
                    self.sanitize(active_on.isoformat(), plus=True))
        if filter_string:
            method = "%s&matches=%s" % (method, self.sanitize(filter_string, plus=True))
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

    def sanitize(self, url_param, plus=False):
        # This is a wrapper around urllib.quote to avoid issues like the one
        # discussed in http://bugs.python.org/issue9301
        if plus:
            sane_string = urllib.quote_plus(str(url_param))
        else:
            sane_string = urllib.quote(str(url_param))
        return sane_string
