from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
#
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
import inspect
from socket import error as socket_error
from rhsm.https import ssl, httplib

from rhsm import connection, utils

from subscription_manager.entcertlib import Disconnected

from subscription_manager.i18n import ugettext as _
from subscription_manager.printing_utils import to_unicode_or_bust

SOCKET_MESSAGE = _('Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.')
NETWORK_MESSAGE = _('Network error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information.')
PROXY_MESSAGE = _("Proxy error, unable to connect to proxy server.")
UNAUTHORIZED_MESSAGE = _("Unauthorized: Invalid credentials for request.")
FORBIDDEN_MESSAGE = _("Forbidden: Invalid credentials for request.")
REMOTE_SERVER_MESSAGE = _("Remote server error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information.")
BAD_CA_CERT_MESSAGE = _("Bad CA certificate: %s")
EXPIRED_ID_CERT_MESSAGE = _("Your identity certificate has expired")
SSL_MESSAGE = _('Unable to verify server\'s identity: %s')
PERROR_EMPTY_MESSAGE = _("Server URL can not be empty")
PERROR_JUST_SCHEME_MESSAGE = _("Server URL is just a schema. Should include hostname, and/or port and path")
PERROR_NONE_MESSAGE = _("Server URL can not be None")
PERROR_PORT_MESSAGE = _("Server URL port should be numeric")
PERROR_SCHEME_MESSAGE = _("Server URL has an invalid scheme. http:// and https:// are supported")
RATE_LIMIT_MESSAGE = _("The server rate limit has been exceeded, please try again later.")
RATE_LIMIT_EXPIRATION = _("The server rate limit has been exceeded, please try again later. (Expires in %s seconds)")

# TRANSLATORS: example: "HTTP error code 500: Error on the server" (the portion after the colon will
# originate on the server)
RESTLIB_MESSAGE = _(u"HTTP error code %s: %s")


class ExceptionMapper(object):
    def __init__(self):

        self.message_map = {
            socket_error: (SOCKET_MESSAGE, self.format_default),
            Disconnected: (SOCKET_MESSAGE, self.format_default),
            connection.ProxyException: (PROXY_MESSAGE, self.format_default),
            connection.NetworkException: (NETWORK_MESSAGE, self.format_default),
            connection.UnauthorizedException: (UNAUTHORIZED_MESSAGE, self.format_default),
            connection.ForbiddenException: (FORBIDDEN_MESSAGE, self.format_default),
            connection.RemoteServerException: (REMOTE_SERVER_MESSAGE, self.format_default),
            connection.BadCertificateException: (BAD_CA_CERT_MESSAGE, self.format_bad_ca_cert_exception),
            connection.ExpiredIdentityCertException: (EXPIRED_ID_CERT_MESSAGE, self.format_default),
            utils.ServerUrlParseErrorEmpty: (PERROR_EMPTY_MESSAGE, self.format_default),
            utils.ServerUrlParseErrorJustScheme: (PERROR_JUST_SCHEME_MESSAGE, self.format_default),
            utils.ServerUrlParseErrorNone: (PERROR_NONE_MESSAGE, self.format_default),
            utils.ServerUrlParseErrorPort: (PERROR_PORT_MESSAGE, self.format_default),
            utils.ServerUrlParseErrorScheme: (PERROR_SCHEME_MESSAGE, self.format_default),
            ssl.SSLError: (SSL_MESSAGE, self.format_ssl_error),
            # The message template will always be none since the RestlibException's
            # message is already translated server-side.
            connection.RestlibException: (RESTLIB_MESSAGE, self.format_restlib_exception),
            connection.RateLimitExceededException: (None, self.format_rate_limit_exception),
            httplib.BadStatusLine: (REMOTE_SERVER_MESSAGE, self.format_default),
        }

    def format_default(self, e, message):
        return message

    def format_bad_ca_cert_exception(self, bad_ca_cert_error, message_template):
        return message_template % bad_ca_cert_error.cert_path

    def format_ssl_error(self, ssl_error, message_template):
        return message_template % ssl_error

    def format_restlib_exception(self, restlib_exception, message_template):
        return message_template % (restlib_exception.code, to_unicode_or_bust(restlib_exception.msg))

    def format_rate_limit_exception(self, rate_limit_exception, _):
        if rate_limit_exception.retry_after is not None:
            return RATE_LIMIT_EXPIRATION % str(rate_limit_exception.retry_after)
        else:
            return RATE_LIMIT_MESSAGE

    def get_message(self, ex):
        # Lookup by __class__ instead of type to support old style classes
        classes = inspect.getmro(ex.__class__)
        for next_class in classes:
            if next_class in self.message_map:
                message_template, formatter = self.message_map[next_class]
                return formatter(ex, message_template)
        return None
