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
from M2Crypto.SSL import SSLError
import gettext
_ = gettext.gettext

from rhsm import connection, utils

from subscription_manager.entcertlib import Disconnected

SOCKET_MESSAGE = _('Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.')
NETWORK_MESSAGE = _('Network error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information.')
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


class ExceptionMapper(object):
    def __init__(self):

        self.message_map = {
            socket_error: (SOCKET_MESSAGE, self.format_default),
            Disconnected: (SOCKET_MESSAGE, self.format_default),
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
            SSLError: (SSL_MESSAGE, self.format_ssl_error),
            # The message template will always be none since the RestlibException's
            # message is already translated server-side.
            connection.RestlibException: (None, self.format_restlib_exception),
        }

    def format_default(self, e, message):
        return message

    def format_bad_ca_cert_exception(self, bad_ca_cert_error, message_template):
        return message_template % bad_ca_cert_error.cert_path

    def format_ssl_error(self, ssl_error, message_template):
        return message_template % str(ssl_error)

    def format_restlib_exception(self, restlib_exception, message_template):
        return restlib_exception.msg

    def get_message(self, ex):
        # Lookup by __class__ instead of type to support old style classes
        classes = inspect.getmro(ex.__class__)
        for next_class in classes:
            if next_class in self.message_map:
                message_template, formatter = self.message_map[next_class]
                return formatter(ex, message_template)
        return None
