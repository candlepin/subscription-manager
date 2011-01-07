#
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

import re
from socket import error as socket_error
from M2Crypto import SSL

import gettext
_ = gettext.gettext

import rhsm.connection as connection
import messageWindow
from logutil import getLogger
log = getLogger(__name__)

def handle_gui_exception(e, msg, logMsg=None):
    """
    Handles an exception for the gui by logging the stack trace and
    displaying a user-friendly internationalized message.

    msg = User friendly message to display in GUI.
    logMsg = Optional message to be logged in addition to stack trace.
    """

    if logMsg:
        log.error(logMsg)
    log.exception(e)

    # If exception is of these types we ignore the given display msg:
    if isinstance(e, socket_error):
        errorWindow(_('Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.'))
    elif isinstance(e, SSL.SSLError):
        errorWindow(_('Unable to verify server\'s identity: %s' % str(e)))
    elif isinstance(e, connection.NetworkException):
        # NOTE: yes this looks a lot like the socket error, but I think these
        # were actually intended to display slightly different messages:
        errorWindow(_("Network error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information."))
    elif isinstance(e, connection.RestlibException):
        errorWindow(msg % linkify(e.msg))
    elif isinstance(e, connection.BadCertificateException):
        errorWindow(_("Bad CA certificate: %s" % e.cert_path))
    else:
        errorWindow(msg)

def errorWindow(message):
    messageWindow.ErrorDialog(messageWindow.wrap_text(message))

def linkify(msg):
    """
    Parse a string for any urls and wrap them in a hrefs, for use in a
    gtklabel.
    """
    # lazy regex; should be good enough.
    url_regex = re.compile("https?://\S*")

    def add_markup(mo):
        url = mo.group(0)
        return '<a href="%s">%s</a>' % (url, url)

    return url_regex.sub(add_markup, msg)
