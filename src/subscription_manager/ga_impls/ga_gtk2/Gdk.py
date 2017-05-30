from __future__ import print_function, division, absolute_import

from gtk.gdk import color_parse
from gtk.gdk import Cursor, Event
from gtk.gdk import BUTTON_PRESS, WATCH, WINDOW_TYPE_HINT_DIALOG


class WindowTypeHint(object):
    DIALOG = WINDOW_TYPE_HINT_DIALOG


class CursorType(object):
    WATCH = WATCH


class EventType(object):
    BUTTON_PRESS = BUTTON_PRESS


enums = [CursorType, EventType, WindowTypeHint]
classes = [Cursor, Event]
methods = [color_parse]
__all__ = classes + methods + enums
