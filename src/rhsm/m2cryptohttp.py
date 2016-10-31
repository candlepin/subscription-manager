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

from httplib import *
from M2Crypto.httpslib import *
from M2Crypto import httpslib, SSL
import socket


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
            try:
                sock = SSL.Connection(self.ssl_ctx, family=family)
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
        self.ssl_port = ssl_port
        context = kwargs.pop('context', None)
        kwargs['ssl_context'] = context.m2context
        self._connection = _RhsmHTTPSConnection(host, *args, **kwargs)
        self.args = args
        self.kwargs = kwargs

    def request(self, method, handler, *args, **kwargs):
        handler = "https://%s:%s%s" % (self.host, self.ssl_port, handler)
        return self._connection.request(method, handler, *args, **kwargs)

    def getresponse(self, *args, **kwargs):
        return self._connection.getresponse(*args, **kwargs)

    def set_debuglevel(self, *args, **kwargs):
        return self._connection.set_debuglevel(*args, **kwargs)

    def set_tunnel(self, host, port=None, headers=None):
        # switch to proxy connection
        proxy_host = self.host
        proxy_port = self.ssl_port
        self.host = host
        self.ssl_port = port
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
