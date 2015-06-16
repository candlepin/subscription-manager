
import gtk

# objects
from gobject import GObject
from gobject import MainLoop

# methods
from gobject import idle_add, markup_escape_text, source_remove, timeout_add

# enums
from gobject import SIGNAL_RUN_LAST
from gobject import TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE

threads_init = gtk.gdk.threads_init


class SignalFlags(object):
    RUN_LAST = SIGNAL_RUN_LAST


constants = [TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE]
methods = [idle_add, markup_escape_text, source_remove, threads_init,
           timeout_add]
enums = [SignalFlags]
objects = [GObject, MainLoop]
__all__ = objects + methods + constants + enums
