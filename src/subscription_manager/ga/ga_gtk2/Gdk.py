#from gtk.gdk import color_parse
#from gtk.gdk import WINDOW_TYPE_HINT_DIALOG

from gtk.gdk import *


class WindowTypeHint(object):
    DIALOG = WINDOW_TYPE_HINT_DIALOG


class CursorType(object):
    WATCH = WATCH


__all__ = [color_parse, Cursor, WindowTypeHint]
