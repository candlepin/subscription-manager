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
import logging
from socket import error as socket_error
from M2Crypto import SSL
import gobject
import datetime
import dbus
import gtk
import gtk.glade

import gettext
_ = lambda x: gettext.ldgettext("rhsm", x)

import rhsm.connection as connection
from subscription_manager.gui import messageWindow
from subscription_manager import managerlib

log = logging.getLogger('rhsm-app.' + __name__)

# we need gtk 2.18+ to do the right markup in likify
MIN_GTK_MAJOR = 2
MIN_GTK_MINOR = 18
MIN_GTK_MICRO = 0

EVEN_ROW_COLOR = '#eeeeee'


def handle_gui_exception(e, msg, parent, formatMsg=True, logMsg=None):
    """
    Handles an exception for the gui by logging the stack trace and
    displaying a user-friendly internationalized message.

    msg = User friendly message to display in GUI.
    parent = Parent window where the error originates.
    logMsg = Optional message to be logged in addition to stack trace.
    formatMsg = if true, string sub the exception error in the msg
    """

    if logMsg:
        log.error(logMsg)
    log.exception(e)

    # If exception is of these types we ignore the given display msg:
    if isinstance(e, socket_error):
        errorWindow(_('Network error, unable to connect to server. Please see /var/log/rhsm/rhsm.log for more information.'),
                parent=parent)
    elif isinstance(e, SSL.SSLError):
        errorWindow(_('Unable to verify server\'s identity: %s') % str(e),
                parent=parent)
    elif isinstance(e, connection.NetworkException):
        # NOTE: yes this looks a lot like the socket error, but I think these
        # were actually intended to display slightly different messages:
        errorWindow(_("Network error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information."), parent=parent)
    elif isinstance(e, connection.RemoteServerException):
        # This is what happens when there's an issue with the server on the other side of the wire
        errorWindow(_("Remote server error. Please check the connection details, or see /var/log/rhsm/rhsm.log for more information."), parent=parent)
    elif isinstance(e, connection.RestlibException):
        # If this exception's code is in the 200 range (such as 202 ACCEPTED)
        # we're going to ignore the message we were given and just display
        # the message from the server as an info dialog. (not an error)
        if 200 < int(e.code) < 300:
            message = linkify(e.msg)
            messageWindow.InfoDialog(messageWindow.wrap_text(message))

        else:
            try:
                if formatMsg:
                    message = msg % linkify(e.msg)
                else:
                    message = linkify(e.msg)
            except:
                message = msg

            errorWindow(message, parent=parent)

    elif isinstance(e, connection.BadCertificateException):
        errorWindow(_("Bad CA certificate: %s") % e.cert_path, parent=parent)
    else:
        #catch-all, try to interpolate and if it doesn't work out, just display the message
        try:
            interpolatedStr = msg % e
            errorWindow(interpolatedStr, parent=parent)
        except:
            errorWindow(msg, parent=parent)


def errorWindow(message, parent=None):
    messageWindow.ErrorDialog(messageWindow.wrap_text(message),
            parent)


def linkify(msg):
    """
    Parse a string for any urls and wrap them in a hrefs, for use in a
    gtklabel.
    """
    # http (non whitespace or . or
    #  ? or () or - or / or ;
    url_regex = re.compile("""https?://[\w\.\?\(\)\-\/]*""")

    if gtk.check_version(MIN_GTK_MAJOR, MIN_GTK_MINOR, MIN_GTK_MICRO):
        return msg

    def add_markup(mo):
        url = mo.group(0)
        return '<a href="%s">%s</a>' % (url, url)

    return url_regex.sub(add_markup, msg)


def apply_highlight(text, highlight):
    """
    Apply pango markup to highlight a search term in a string
    """
    if not highlight:
        return gobject.markup_escape_text(text)

    regex = re.compile("(" + highlight + ")", re.I)
    parts = regex.split(text)

    escaped = []
    # re.split makes every second result be our split term
    on_search_term = False
    for part in parts:
        if on_search_term:
            escaped += "<b>%s</b>" % gobject.markup_escape_text(part)
        else:
            escaped += gobject.markup_escape_text(part)
        on_search_term = not on_search_term

    return "".join(escaped)


def find_text(haystack, needle):
    """
    Find all occurances of needle in haystack, case insensitvely.
    Return a list of the offsets of all the occurances
    """
    if not needle:
        return []

    needle = needle.lower()
    haystack = haystack.lower()

    finds = []
    offset = 0

    while True:
        index = haystack.find(needle, offset)
        if (index == -1):
            break
        finds.append(index)
        offset = index + 1
        if (index + 1 == len(haystack)):
            break

    return finds


def make_today_now(today):
    """
    Given a datetime, return either that datetime, or, if the value is today's
    date, return the datetime representing 'right now'.

    Useful for asking for subscriptions that are valid now.
    """
    if today.date() == datetime.date.today():
        now = datetime.datetime.today()
        today = today.replace(hour=now.hour, minute=now.minute,
                second=now.second, tzinfo=managerlib.LocalTz())
    return today


def get_dbus_iface():
    """
    Set up the dbus proxy for calling remote methods
    """
    bus = dbus.SystemBus()
    validity_obj = bus.get_object('com.redhat.SubscriptionManager',
                      '/EntitlementStatus')
    validity_iface = dbus.Interface(validity_obj,
                        dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus')
    return validity_iface


def get_cell_background_color(item_idx):
    """
    Determines the BG color for a cell based on entry index of the model.
    """
    # NOTE: Even indexes are actually displayed as an odd row.
    if item_idx % 2 != 0:
        return EVEN_ROW_COLOR


def set_background_model_index(tree_view, model_idx):
    """
    Sets the model index containing the background color for all cells.
    This should be called after all columns and renderes have been added
    to the treeview.

    @param tree_view: the tree view to set the background model index on.
    @param model_idx: the model index containing the background color.
    """
    for col in tree_view.get_columns():
        for renderer in col.get_cell_renderers():
            col.add_attribute(renderer, 'cell-background', model_idx)


class GladeWrapper(gtk.glade.XML):
    def __init__(self, filename):
        gtk.glade.XML.__init__(self, filename)

    def get_widget(self, widget_name):
        widget = gtk.glade.XML.get_widget(self, widget_name)
        if widget is None:
            print "Error: widget %s was not found" % widget_name
            raise Exception("Widget %s not found" % widget_name)
        return widget
