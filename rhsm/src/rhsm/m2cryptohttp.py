from __future__ import print_function, division, absolute_import

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

"""
This is wrapper providing https connection on RHEL6. It is not used on higher versions
of RHEL. It also is not used on Fedora (since version 23).
NOTE: using environment variable RHSM_USE_M2CRYPTO does not work with Python3.
"""

import six.moves.http_client
from M2Crypto import httpslib, SSL
from M2Crypto.SSL import timeout
import socket
import inspect

# constants from actual httplib
HTTP_PORT = six.moves.http_client.HTTP_PORT
HTTPS_PORT = six.moves.http_client.HTTPS_PORT

CONTINUE = six.moves.http_client.CONTINUE
SWITCHING_PROTOCOLS = six.moves.http_client.SWITCHING_PROTOCOLS
PROCESSING = six.moves.http_client.PROCESSING
OK = six.moves.http_client.OK
CREATED = six.moves.http_client.CREATED
ACCEPTED = six.moves.http_client.ACCEPTED
NON_AUTHORITATIVE_INFORMATION = six.moves.http_client.NON_AUTHORITATIVE_INFORMATION
NO_CONTENT = six.moves.http_client.NO_CONTENT
RESET_CONTENT = six.moves.http_client.RESET_CONTENT
PARTIAL_CONTENT = six.moves.http_client.PARTIAL_CONTENT
MULTI_STATUS = six.moves.http_client.MULTI_STATUS
IM_USED = six.moves.http_client.IM_USED
MULTIPLE_CHOICES = six.moves.http_client.MULTIPLE_CHOICES
MOVED_PERMANENTLY = six.moves.http_client.MOVED_PERMANENTLY
FOUND = six.moves.http_client.FOUND
SEE_OTHER = six.moves.http_client.SEE_OTHER
NOT_MODIFIED = six.moves.http_client.NOT_MODIFIED
USE_PROXY = six.moves.http_client.USE_PROXY
TEMPORARY_REDIRECT = six.moves.http_client.TEMPORARY_REDIRECT
BAD_REQUEST = six.moves.http_client.BAD_REQUEST
UNAUTHORIZED = six.moves.http_client.UNAUTHORIZED
PAYMENT_REQUIRED = six.moves.http_client.PAYMENT_REQUIRED
FORBIDDEN = six.moves.http_client.FORBIDDEN
NOT_FOUND = six.moves.http_client.NOT_FOUND
METHOD_NOT_ALLOWED = six.moves.http_client.METHOD_NOT_ALLOWED
NOT_ACCEPTABLE = six.moves.http_client.NOT_ACCEPTABLE
PROXY_AUTHENTICATION_REQUIRED = six.moves.http_client.PROXY_AUTHENTICATION_REQUIRED
REQUEST_TIMEOUT = six.moves.http_client.REQUEST_TIMEOUT
CONFLICT = six.moves.http_client.CONFLICT
GONE = six.moves.http_client.GONE
LENGTH_REQUIRED = six.moves.http_client.LENGTH_REQUIRED
PRECONDITION_FAILED = six.moves.http_client.PRECONDITION_FAILED
REQUEST_ENTITY_TOO_LARGE = six.moves.http_client.REQUEST_ENTITY_TOO_LARGE
REQUEST_URI_TOO_LONG = six.moves.http_client.REQUEST_URI_TOO_LONG
UNSUPPORTED_MEDIA_TYPE = six.moves.http_client.UNSUPPORTED_MEDIA_TYPE
REQUESTED_RANGE_NOT_SATISFIABLE = six.moves.http_client.REQUESTED_RANGE_NOT_SATISFIABLE
EXPECTATION_FAILED = six.moves.http_client.EXPECTATION_FAILED
UNPROCESSABLE_ENTITY = six.moves.http_client.UNPROCESSABLE_ENTITY
LOCKED = six.moves.http_client.LOCKED
FAILED_DEPENDENCY = six.moves.http_client.FAILED_DEPENDENCY
UPGRADE_REQUIRED = six.moves.http_client.UPGRADE_REQUIRED
INTERNAL_SERVER_ERROR = six.moves.http_client.INTERNAL_SERVER_ERROR
NOT_IMPLEMENTED = six.moves.http_client.NOT_IMPLEMENTED
BAD_GATEWAY = six.moves.http_client.BAD_GATEWAY
SERVICE_UNAVAILABLE = six.moves.http_client.SERVICE_UNAVAILABLE
GATEWAY_TIMEOUT = six.moves.http_client.GATEWAY_TIMEOUT
HTTP_VERSION_NOT_SUPPORTED = six.moves.http_client.HTTP_VERSION_NOT_SUPPORTED
INSUFFICIENT_STORAGE = six.moves.http_client.INSUFFICIENT_STORAGE
NOT_EXTENDED = six.moves.http_client.NOT_EXTENDED

responses = six.moves.http_client.responses

HTTPConnection = six.moves.http_client.HTTPConnection
HTTPResponse = six.moves.http_client.HTTPResponse
HTTPMessage = six.moves.http_client.HTTPMessage
HTTPException = six.moves.http_client.HTTPException
NotConnected = six.moves.http_client.NotConnected
InvalidURL = six.moves.http_client.InvalidURL
UnknownProtocol = six.moves.http_client.UnknownProtocol
UnknownTransferEncoding = six.moves.http_client.UnknownTransferEncoding
UnimplementedFileMode = six.moves.http_client.UnimplementedFileMode
IncompleteRead = six.moves.http_client.IncompleteRead
ImproperConnectionState = six.moves.http_client.ImproperConnectionState
CannotSendRequest = six.moves.http_client.CannotSendRequest
CannotSendHeader = six.moves.http_client.CannotSendHeader
ResponseNotReady = six.moves.http_client.ResponseNotReady
BadStatusLine = six.moves.http_client.BadStatusLine


class _RhsmProxyHTTPSConnection(httpslib.ProxyHTTPSConnection):
    def __init__(self, host, *args, **kwargs):
        self.rhsm_timeout = float(kwargs.pop('timeout', -1.0))
        self.proxy_headers = kwargs.pop('proxy_headers', None)
        httpslib.ProxyHTTPSConnection.__init__(self, host, *args, **kwargs)

    def _start_ssl(self):
        self.sock = SSL.Connection(self.ssl_ctx, self.sock)
        try:
            self.sock.settimeout(self.rhsm_timeout)
        except AttributeError:
            self.sock.set_socket_write_timeout(timeout(self.rhsm_timeout))
            self.sock.set_socket_read_timeout(timeout(self.rhsm_timeout))
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
        if self.proxy_headers:
            for key, value in list(self.proxy_headers.items()):
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
                try:
                    sock.settimeout(self.rhsm_timeout)
                except AttributeError:
                    sock.set_socket_write_timeout(timeout(self.rhsm_timeout))
                    sock.set_socket_read_timeout(timeout(self.rhsm_timeout))
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
