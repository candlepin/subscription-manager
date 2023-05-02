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
from typing import Callable, Dict, Optional, Tuple

from socket import error as socket_error, gaierror as socket_gaierror
from rhsm.https import ssl, httplib

from rhsm import connection, utils
from rhsm.certificate2 import CertificateLoadingError

from subscription_manager.certdirectory import DEFAULT_PRODUCT_CERT_DIR
from subscription_manager.cp_provider import TokenAuthUnsupportedException
from subscription_manager.entcertlib import Disconnected

from subscription_manager.i18n import ungettext, ugettext as _
from subscription_manager.utils import terminal_printable_content

SOCKET_MESSAGE = _(
    "Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information."
)
GAI_MESSAGE = _("Network error: {message} (error code {code})")
CONNECTION_MESSAGE = _("Connection error: {message} (error code {code})")
UNKNOWN_CONTENT_MESSAGE_CONTENT = _("Unknown server reply (HTTP error code {code}: {title}):\n{content}")
UNKNOWN_CONTENT_MESSAGE = _("Unknown server reply (HTTP error code {code}: {title})")
PROXY_ADDRESS_REASON_OSERROR_MESSAGE = _(
    "Proxy error: unable to connect to {hostname}: {message} (error code {code})"
)
PROXY_ADDRESS_REASON_MESSAGE = _("Proxy error: unable to connect to {hostname}: {message}")
PROXY_ADDRESS_MESSAGE = _("Proxy error: unable to connect to {hostname}")
UNAUTHORIZED_MESSAGE = _("Unauthorized: Invalid credentials for request.")
TOKEN_AUTH_UNSUPPORTED_MESSAGE = _("Token authentication not supported by the entitlement server")
FORBIDDEN_MESSAGE = _("Forbidden: Invalid credentials for request.")
REMOTE_SERVER_MESSAGE = _(
    "Remote server error. Please check the connection details, "
    "or see /var/log/rhsm/rhsm.log for more information."
)
BAD_CA_CERT_MESSAGE = _("Bad CA certificate: {file}: {reason}")
EXPIRED_ID_CERT_MESSAGE = _("Your identity certificate has expired")
SSL_MESSAGE = _("Unable to verify server's identity: %s")
PERROR_EMPTY_MESSAGE = _("Server URL can not be empty")
PERROR_JUST_SCHEME_MESSAGE = _("Server URL is just a schema. Should include hostname, and/or port and path")
PERROR_NONE_MESSAGE = _("Server URL can not be None")
PERROR_PORT_MESSAGE = _("Server URL port should be numeric")
PERROR_SCHEME_MESSAGE = _("Server URL has an invalid scheme. http:// and https:// are supported")
RATE_LIMIT_MESSAGE = _("The server rate limit has been exceeded, please try again later.")
PRODUCT_CERTIFICATE_LOADING_PATH_ERROR = _("Bad product certificate: {file}: [{library}] {message}")
CERTIFICATE_LOADING_PATH_ERROR = _("Bad certificate: {file}: [{library}] {message}")
CERTIFICATE_LOADING_PEM_ERROR = _("Bad certificate: [{library}] {message}\n{data}")
CERTIFICATE_LOADING_ERROR = _("Bad certificate: [{library}] {message}")
CONNECTION_UNREACHABLE_MESSAGE = _("Unable to reach the server at {host}: {message}")

# TRANSLATORS: example: "You don't have permission to perform this action (HTTP error code 403: Forbidden)"
# (the part before the opening bracket originates on the server)
RESTLIB_MESSAGE = _("{message} (HTTP error code {code}: {title})")


class ExceptionMapper:
    def __init__(self):
        self.message_map: Dict[str, Callable] = {
            socket_error: (SOCKET_MESSAGE, self.format_using_template),
            socket_gaierror: (GAI_MESSAGE, self.format_generic_oserror),
            ConnectionError: (CONNECTION_MESSAGE, self.format_generic_oserror),
            Disconnected: (SOCKET_MESSAGE, self.format_using_template),
            connection.ProxyException: (None, self.format_proxy_exception),
            connection.UnknownContentException: (None, self.format_unknown_content),
            connection.UnauthorizedException: (UNAUTHORIZED_MESSAGE, self.format_using_template),
            connection.ForbiddenException: (FORBIDDEN_MESSAGE, self.format_using_template),
            connection.RemoteServerException: (REMOTE_SERVER_MESSAGE, self.format_using_template),
            connection.BadCertificateException: (BAD_CA_CERT_MESSAGE, self.format_bad_ca_cert_exception),
            connection.ExpiredIdentityCertException: (EXPIRED_ID_CERT_MESSAGE, self.format_using_template),
            utils.ServerUrlParseErrorEmpty: (PERROR_EMPTY_MESSAGE, self.format_using_template),
            utils.ServerUrlParseErrorJustScheme: (PERROR_JUST_SCHEME_MESSAGE, self.format_using_template),
            utils.ServerUrlParseErrorNone: (PERROR_NONE_MESSAGE, self.format_using_template),
            utils.ServerUrlParseErrorPort: (PERROR_PORT_MESSAGE, self.format_using_template),
            utils.ServerUrlParseErrorScheme: (PERROR_SCHEME_MESSAGE, self.format_using_template),
            ssl.SSLError: (SSL_MESSAGE, self.format_ssl_error),
            # The message template will always be none since the RestlibException's
            # message is already translated server-side.
            connection.RestlibException: (RESTLIB_MESSAGE, self.format_restlib_exception),
            connection.RateLimitExceededException: (None, self.format_rate_limit_exception),
            httplib.BadStatusLine: (REMOTE_SERVER_MESSAGE, self.format_using_template),
            TokenAuthUnsupportedException: (TOKEN_AUTH_UNSUPPORTED_MESSAGE, self.format_using_template),
            CertificateLoadingError: (None, self.format_cert_loading_error),
            connection.ConnectionOSErrorException: (
                CONNECTION_UNREACHABLE_MESSAGE,
                self.format_connection_unreachable,
            ),
        }

    def format_using_template(self, _: Exception, message: str) -> str:
        """Return unaltered message template."""
        return message

    def format_using_error(self, exc: Exception, _: Optional[str]) -> str:
        """Return string representation of the error."""
        return str(exc)

    def format_generic_oserror(self, exc: Exception, message_template: str):
        return message_template.format(message=exc.strerror, code=exc.errno)

    def format_proxy_exception(self, exc: connection.ProxyException, _: str) -> str:
        proxy_address = exc.address
        # catches gaierror and socket.error;
        # the check for errno is done as some socket errors (typically related
        # to proxies) are not the results of failed system calls
        if isinstance(exc.exc, OSError) and exc.exc.errno is not None:
            return PROXY_ADDRESS_REASON_OSERROR_MESSAGE.format(
                hostname=proxy_address,
                message=exc.exc.strerror,
                code=exc.exc.errno,
            )
        if exc.exc is not None:
            return PROXY_ADDRESS_REASON_MESSAGE.format(
                hostname=proxy_address,
                message=exc.exc,
            )
        return PROXY_ADDRESS_MESSAGE.format(hostname=proxy_address)

    def format_unknown_content(self, exc: connection.UnknownContentException, _: str) -> str:
        content = exc.content
        if content is not None:
            return UNKNOWN_CONTENT_MESSAGE_CONTENT.format(
                code=exc.code, title=exc.title, content=terminal_printable_content(content)
            )
        return UNKNOWN_CONTENT_MESSAGE.format(code=exc.code, title=exc.title)

    def format_bad_ca_cert_exception(
        self, bad_ca_cert_error: connection.BadCertificateException, message_template: str
    ):
        return message_template.format(
            file=bad_ca_cert_error.cert_path, reason=str(bad_ca_cert_error.ssl_exc)
        )

    def format_ssl_error(self, ssl_error: ssl.SSLError, message_template: str):
        return message_template % ssl_error

    def format_restlib_exception(
        self,
        restlib_exception: connection.RestlibException,
        message_template: str,
    ):
        return message_template.format(
            message=restlib_exception.msg,
            code=restlib_exception.code,
            title=restlib_exception.title,
        )

    def format_rate_limit_exception(
        self,
        rate_limit_exception: connection.RateLimitExceededException,
        _: str,
    ):
        if rate_limit_exception.retry_after is not None:
            return ungettext(
                "The server rate limit has been exceeded, please try again later. "
                "(Expires in {time} second)",
                "The server rate limit has been exceeded, please try again later. "
                "(Expires in {time} seconds)",
                rate_limit_exception.retry_after,
            ).format(time=rate_limit_exception.retry_after)
        else:
            return RATE_LIMIT_MESSAGE

    def format_cert_loading_error(self, exc: CertificateLoadingError, _: str):
        fmtargs = {
            "library": exc.liberr,
            "message": exc.reasonerr,
        }
        if exc.path is not None:
            fmtargs["file"] = exc.path
        if exc.pem is not None:
            fmtargs["data"] = terminal_printable_content(exc.pem)
        if exc.path is not None:
            if exc.path.startswith(DEFAULT_PRODUCT_CERT_DIR):
                return PRODUCT_CERTIFICATE_LOADING_PATH_ERROR.format(**fmtargs)
            return CERTIFICATE_LOADING_PATH_ERROR.format(**fmtargs)
        if exc.pem is not None:
            return CERTIFICATE_LOADING_PEM_ERROR.format(**fmtargs)
        return CERTIFICATE_LOADING_ERROR.format(**fmtargs)

    def format_connection_unreachable(
        self, exc: connection.ConnectionOSErrorException, message_template: str
    ):
        host = f"{exc.host}:{exc.port}{exc.handler}"
        return message_template.format(host=host, message=str(exc.exc))

    def get_message(self, exception) -> str:
        """Get string representation of an exception.

        The exception may have special handler (to allow us to fill in
        variables into the message), or it may only use custom string template
        (so we can display translated version).

        If the message does not have any handler defined its string
        representation is returned.
        """
        # Lookup by __class__ instead of type to support old style classes
        exception_classes: Tuple[type(Exception), ...] = inspect.getmro(exception.__class__)
        exception_class: type(Exception)
        for exception_class in exception_classes:
            if exception_class in self.message_map:
                message_template: str
                formatter: Callable
                message_template, formatter = self.message_map[exception_class]
                return formatter(exception, message_template)
        return self.format_using_error(exception, None)
