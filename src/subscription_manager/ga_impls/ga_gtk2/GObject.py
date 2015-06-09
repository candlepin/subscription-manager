
import gtk
#import gobject
#from gobject import
from gobject import *

threads_init = gtk.gdk.threads_init


class SignalFlags(object):
    RUN_LAST = SIGNAL_RUN_LAST


constants = [TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE]
methods = [idle_add, markup_escape_text, source_remove, threads_init,
           timeout_add]
__all__ = [GObject, SignalFlags, source_remove, threads_init] + methods + constants
