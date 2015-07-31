

# objects
from gobject import GObject
from gobject import MainLoop

# methods
from gobject import add_emission_hook, idle_add, property
from gobject import source_remove, timeout_add
from gobject import markup_escape_text

# enums
from gobject import SIGNAL_RUN_FIRST, SIGNAL_RUN_LAST
from gobject import TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE


class SignalFlags(object):
    RUN_FIRST = SIGNAL_RUN_FIRST
    RUN_LAST = SIGNAL_RUN_LAST

constants = [TYPE_BOOLEAN, TYPE_PYOBJECT, PARAM_READWRITE]
methods = [add_emission_hook, idle_add, markup_escape_text,
           property, source_remove, timeout_add]
enums = [SignalFlags]
objects = [GObject, MainLoop]
__all__ = objects + methods + constants + enums
