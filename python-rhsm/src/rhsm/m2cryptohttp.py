# A compatibility wrapper that adapts m2crypto to the subset of standard lib httplib used in python-rhsm.
#
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

import httplib
from M2Crypto import httpslib, SSL
import socket
import inspect

# constants from actual httplib
HTTP_PORT = httplib.HTTP_PORT
HTTPS_PORT = httplib.HTTPS_PORT

CONTINUE = httplib.CONTINUE
SWITCHING_PROTOCOLS = httplib.SWITCHING_PROTOCOLS
PROCESSING = httplib.PROCESSING
OK = httplib.OK
CREATED = httplib.CREATED
ACCEPTED = httplib.ACCEPTED
NON_AUTHORITATIVE_INFORMATION = httplib.NON_AUTHORITATIVE_INFORMATION
NO_CONTENT = httplib.NO_CONTENT
RESET_CONTENT = httplib.RESET_CONTENT
PARTIAL_CONTENT = httplib.PARTIAL_CONTENT
MULTI_STATUS = httplib.MULTI_STATUS
IM_USED = httplib.IM_USED
MULTIPLE_CHOICES = httplib.MULTIPLE_CHOICES
MOVED_PERMANENTLY = httplib.MOVED_PERMANENTLY
FOUND = httplib.FOUND
SEE_OTHER = httplib.SEE_OTHER
NOT_MODIFIED = httplib.NOT_MODIFIED
USE_PROXY = httplib.USE_PROXY
TEMPORARY_REDIRECT = httplib.TEMPORARY_REDIRECT
BAD_REQUEST = httplib.BAD_REQUEST
UNAUTHORIZED = httplib.UNAUTHORIZED
PAYMENT_REQUIRED = httplib.PAYMENT_REQUIRED
FORBIDDEN = httplib.FORBIDDEN
NOT_FOUND = httplib.NOT_FOUND
METHOD_NOT_ALLOWED = httplib.METHOD_NOT_ALLOWED
NOT_ACCEPTABLE = httplib.NOT_ACCEPTABLE
PROXY_AUTHENTICATION_REQUIRED = httplib.PROXY_AUTHENTICATION_REQUIRED
REQUEST_TIMEOUT = httplib.REQUEST_TIMEOUT
CONFLICT = httplib.CONFLICT
GONE = httplib.GONE
LENGTH_REQUIRED = httplib.LENGTH_REQUIRED
PRECONDITION_FAILED = httplib.PRECONDITION_FAILED
REQUEST_ENTITY_TOO_LARGE = httplib.REQUEST_ENTITY_TOO_LARGE
REQUEST_URI_TOO_LONG = httplib.REQUEST_URI_TOO_LONG
UNSUPPORTED_MEDIA_TYPE = httplib.UNSUPPORTED_MEDIA_TYPE
REQUESTED_RANGE_NOT_SATISFIABLE = httplib.REQUESTED_RANGE_NOT_SATISFIABLE
EXPECTATION_FAILED = httplib.EXPECTATION_FAILED
UNPROCESSABLE_ENTITY = httplib.UNPROCESSABLE_ENTITY
LOCKED = httplib.LOCKED
FAILED_DEPENDENCY = httplib.FAILED_DEPENDENCY
UPGRADE_REQUIRED = httplib.UPGRADE_REQUIRED
INTERNAL_SERVER_ERROR = httplib.INTERNAL_SERVER_ERROR
NOT_IMPLEMENTED = httplib.NOT_IMPLEMENTED
BAD_GATEWAY = httplib.BAD_GATEWAY
SERVICE_UNAVAILABLE = httplib.SERVICE_UNAVAILABLE
GATEWAY_TIMEOUT = httplib.GATEWAY_TIMEOUT
HTTP_VERSION_NOT_SUPPORTED = httplib.HTTP_VERSION_NOT_SUPPORTED
INSUFFICIENT_STORAGE = httplib.INSUFFICIENT_STORAGE
NOT_EXTENDED = httplib.NOT_EXTENDED

responses = httplib.responses

HTTPConnection = httplib.HTTPConnection
HTTPResponse = httplib.HTTPResponse
HTTPMessage = httplib.HTTPMessage
HTTPException = httplib.HTTPException
NotConnected = httplib.NotConnected
InvalidURL = httplib.InvalidURL
UnknownProtocol = httplib.UnknownProtocol
UnknownTransferEncoding = httplib.UnknownTransferEncoding
UnimplementedFileMode = httplib.UnimplementedFileMode
IncompleteRead = httplib.IncompleteRead
ImproperConnectionState = httplib.ImproperConnectionState
CannotSendRequest = httplib.CannotSendRequest
CannotSendHeader = httplib.CannotSendHeader
ResponseNotReady = httplib.ResponseNotReady
BadStatusLine = httplib.BadStatusLine


class _RhsmProxyHTTPSConnection(httpslib.ProxyHTTPSConnection):
    def __init__(self, host, *args, **kwargs):
        self.rhsm_timeout = float(kwargs.pop('timeout', -1.0))
        self.proxy_headers = kwargs.pop('proxy_headers', None)
        httpslib.ProxyHTTPSConnection.__init__(self, host, *args, **kwargs)

    def _start_ssl(self):
        self.sock = SSL.Connection(self.ssl_ctx, self.sock)
        self.sock.settimeout(self.rhsm_timeout)
        self.sock.setup_ssl()
        self.sock.set_connect_state()
        self.sock.connect_ssl()

    # 2.7 httplib expects to be able to pass a body argument to
    # endheaders, which the m2crypto.httpslib.ProxyHTTPSConnect does
    # not support
    def endheaders(self, body=None):
        if body:
            httpslib.HTTPSConnection.endheaders(self, body)
        else:
            httpslib.HTTPSConnection.endheaders(self)

    def _get_connect_msg(self):
        """ Return an HTTP CONNECT request to send to the proxy. """
        try:
            port = int(self._real_port)
        except Exception:
            port = None
        msg = "CONNECT %s:%d HTTP/1.1\r\n" % (self._real_host, port)
        msg += "Host: %s:%d\r\n" % (self._real_host, port)
        if self.proxy_headers:
            for key, value in self.proxy_headers.items():
                msg += "%s: %s\r\n" % (key, value)
        msg += "\r\n"
        return msg


class _RhsmHTTPSConnection(httpslib.HTTPSConnection):
    def __init__(self, host, *args, **kwargs):
        self.rhsm_timeout = float(kwargs.pop('timeout', -1.0))
        httpslib.HTTPSConnection.__init__(self, host, *args, **kwargs)

    def connect(self):
        """Copied verbatim except for adding the timeout"""
        error = None
        # We ignore the returned sockaddr because SSL.Connection.connect needs
        # a host name.
        for (family, _, _, _, _) in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            sock = None

            # 1435475: Older versions of M2Crypto do not support specifying the connection family, but if
            # we are on a version that does, we can to send it in to support IPv6.
            m2_args, _vargs, _kwords, _defaults = inspect.getargspec(SSL.Connection.__init__)
            connection_kwargs = {}
            if m2_args and 'family' in m2_args:
                connection_kwargs['family'] = family

            try:
                sock = SSL.Connection(self.ssl_ctx, **connection_kwargs)
                sock.settimeout(self.rhsm_timeout)
                if self.session is not None:
                    sock.set_session(self.session)
                sock.connect((self.host, self.port))

                self.sock = sock
                sock = None
                return
            except socket.error as e:
                # Other exception are probably SSL-related, in that case we
                # abort and the exception is forwarded to the caller.
                error = e
            finally:
                if sock is not None:
                    sock.close()

        if error is None:
            raise AssertionError("Empty list returned by getaddrinfo")
        raise error


class HTTPSConnection(object):
    def __init__(self, host, ssl_port, *args, **kwargs):
        self.host = host
        self.ssl_port = int(ssl_port) if ssl_port else None
        context = kwargs.pop('context', None)
        if context:
            kwargs['ssl_context'] = context.m2context
        self._connection = _RhsmHTTPSConnection(host, self.ssl_port, *args, **kwargs)
        self.args = args
        self.kwargs = kwargs

    def request(self, method, handler, *args, **kwargs):
        if isinstance(self._connection, _RhsmProxyHTTPSConnection):
            handler = "https://%s:%s%s" % (self.host, self.ssl_port, handler)
        try:
            return self._connection.request(method, handler, *args, **kwargs)
        except IndexError:  # bz#1423443
            raise socket.error("socket error during request")  # unfortunately details are lost by this point

    def getresponse(self, *args, **kwargs):
        return self._connection.getresponse(*args, **kwargs)

    def set_debuglevel(self, *args, **kwargs):
        return self._connection.set_debuglevel(*args, **kwargs)

    def set_tunnel(self, host, port=None, headers=None):
        # switch to proxy connection
        proxy_host = self.host
        proxy_port = self.ssl_port
        self.host = host
        self.ssl_port = int(port) if port else None
        self._connection = _RhsmProxyHTTPSConnection(proxy_host, proxy_port, *self.args, proxy_headers=headers,
                                                    **self.kwargs)

    def close(self, *args, **kwargs):
        return self._connection.close(*args, **kwargs)

    def putrequest(self, *args, **kwargs):
        return self._connection.putrequest(*args, **kwargs)

    def putheader(self, *args, **kwargs):
        return self._connection.putheader(*args, **kwargs)

    def endheaders(self, *args, **kwargs):
        return self._connection.endheaders(*args, **kwargs)

    def send(self, *args, **kwargs):
        return self._connection.send(*args, **kwargs)
