#from gtk.gdk import color_parse
#from gtk.gdk import WINDOW_TYPE_HINT_DIALOG

from gtk.gdk import *


class WindowTypeHint(object):
    DIALOG = WINDOW_TYPE_HINT_DIALOG


class CursorType(object):
    WATCH = WATCH


class EventType(object):
    BUTTON_PRESS = BUTTON_PRESS


enums = [CursorType, EventType, WindowTypeHint]
classes = [Cursor]
methods = [color_parse]
__all__ = classes + methods + enums
