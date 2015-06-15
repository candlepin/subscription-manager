
import gtk
from gobject import GObject
from gobject import SIGNAL_RUN_LAST
from gobject import TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE
from gobject import idle_add, markup_escape_text, source_remove, timeout_add

threads_init = gtk.gdk.threads_init


class SignalFlags(object):
    RUN_LAST = SIGNAL_RUN_LAST


constants = [TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE]
methods = [idle_add, markup_escape_text, source_remove, threads_init,
           timeout_add]
__all__ = [GObject, SignalFlags, source_remove, threads_init] + methods + constants
