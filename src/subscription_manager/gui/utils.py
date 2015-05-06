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

import datetime
import gettext
import logging
import re
import threading

from gi.repository import GObject
from gi.repository import Gtk

from subscription_manager.exceptions import ExceptionMapper
import rhsm.connection as connection
from subscription_manager.gui import messageWindow

log = logging.getLogger('rhsm-app.' + __name__)

# we need gtk 2.18+ to do the right markup in linkify
MIN_GTK_MAJOR = 2
MIN_GTK_MINOR = 18
MIN_GTK_MICRO = 0

EVEN_ROW_COLOR = '#eeeeee'

# set if we are in firstboot, to disable linkify, see bz#814378
FIRSTBOOT = False

_ = lambda x: gettext.ldgettext("rhsm", x)


def running_as_firstboot():
    global FIRSTBOOT
    FIRSTBOOT = True


def get_running_as_firstboot():
    return FIRSTBOOT


def handle_gui_exception(e, msg, parent, format_msg=True, log_msg=None):
    """
    Handles an exception for the gui by logging the stack trace and
    displaying a user-friendly internationalized message.

    e = either an exception or a tuple returned from sys.exc_info()
    msg = User friendly message to display in GUI.
    parent = Parent window where the error originates.
    log_msg = Optional message to be logged in addition to stack trace.
    format_msg = if true, string sub the exception error in the msg
    """
    if isinstance(e, tuple):
        log.error(log_msg, exc_info=e)
        # Get the class instance of the exception
        e = e[1]
    else:
        if log_msg:
            log.error(log_msg)
        log.exception(e)

    exception_mapper = ExceptionMapper()
    mapped_message = exception_mapper.get_message(e)
    if mapped_message:
        if isinstance(e, connection.RestlibException):
            # If this exception's code is in the 200 range (such as 202 ACCEPTED)
            # we're going to ignore the message we were given and just display
            # the message from the server as an info dialog. (not an error)
            if 200 < int(e.code) < 300:
                message = linkify(mapped_message)
                messageWindow.InfoDialog(messageWindow.wrap_text(message))

            else:
                try:
                    if format_msg:
                        message = msg % linkify(mapped_message)
                    else:
                        message = linkify(mapped_message)
                except Exception:
                    message = msg

                show_error_window(message, parent=parent)
        else:
            show_error_window(mapped_message, parent)
    else:
        #catch-all, try to interpolate and if it doesn't work out, just display the message
        try:
            interpolated_str = msg % e
            show_error_window(interpolated_str, parent=parent)
        except Exception:
            show_error_window(msg, parent=parent)


def show_error_window(message, parent=None):
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

    if Gtk.check_version(MIN_GTK_MAJOR, MIN_GTK_MINOR, MIN_GTK_MICRO):
        return msg

    # dont linkify in firstboot
    if FIRSTBOOT:
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
        return GObject.markup_escape_text(text)

    regex = re.compile("(" + re.escape(highlight) + ")", re.I)
    parts = regex.split(text)

    escaped = []
    # re.split makes every second result be our split term
    on_search_term = False
    for part in parts:
        if on_search_term:
            escaped += "<b>%s</b>" % GObject.markup_escape_text(part)
        else:
            escaped += GObject.markup_escape_text(part)
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


def make_today_none(today):
    """
    Given a datetime, return either that datetime, or, if the value is today's
    date, return None, to use the servers current time

    Useful for asking for subscriptions that are valid now.
    """
    if today.date() == datetime.date.today():
        return None
    return today


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


def gather_group(store, iter, group):
    """
    Returns a list of TreeRowReferences for an iter and every child of the iter
    """
    if store.iter_has_child(iter):
        child_iter = store.iter_children(iter)
        while child_iter:
            gather_group(store, child_iter, group)
            child_iter = store.iter_next(child_iter)

    refs = Gtk.TreeRowReference.new(store, store.get_path(iter))
    group.append(refs)

    return group


class WidgetUpdate(object):

    def __init__(self, *widgets_to_disable):
        self.widgets_to_disable = widgets_to_disable
        self.set_sensitive(False)

    def set_sensitive(self, is_sensitive):
        for widget in self.widgets_to_disable:
            widget.set_sensitive(is_sensitive)

    def finished(self):
        self.set_sensitive(True)


class AsyncWidgetUpdater(object):

    def __init__(self, parent):
        self.parent_window = parent

    def worker(self, widget_update, backend_method, args=None, kwargs=None, exception_msg=None, callback=None):
        args = args or []
        kwargs = kwargs or {}
        try:
            result = backend_method(*args, **kwargs)
            if callback:
                GObject.idle_add(callback, result)
        except Exception, e:
            message = exception_msg or str(e)
            GObject.idle_add(handle_gui_exception, e, message, self.parent_window)
        finally:
            GObject.idle_add(widget_update.finished)

    def update(self, widget_update, backend_method, args=None, kwargs=None, exception_msg=None, callback=None):
        threading.Thread(target=self.worker, args=(widget_update,
            backend_method, args, kwargs, exception_msg, callback)).start()
