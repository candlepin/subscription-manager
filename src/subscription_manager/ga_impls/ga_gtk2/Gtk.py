#
# Question: So, why not just 'from gtk import *' ?
# Answer: Because there are name collisions and semantic changes. So this
#         only imports names used in subscription-manager and are known to work.

# classes widgets
from gtk import AboutDialog, Adjustment, Builder, Button, Calendar, CellRendererPixbuf
from gtk import CellRendererProgress, CellRendererSpin, CellRendererText
from gtk import CellRendererToggle, Entry
from gtk import FileChooserDialog, FileFilter, Frame, HBox, HButtonBox, Image
from gtk import Label, ListStore, MessageDialog, RadioButton, SpinButton
from gtk import TextBuffer, TreeRowReference
from gtk import TreeStore, TreeView, TreeViewColumn, VBox, Viewport

# enums
from gtk import BUTTONBOX_END
from gtk import BUTTONS_OK, BUTTONS_OK_CANCEL, BUTTONS_YES_NO
from gtk import FILE_CHOOSER_ACTION_OPEN
from gtk import MESSAGE_ERROR, MESSAGE_INFO, MESSAGE_QUESTION, MESSAGE_WARNING
from gtk import RESPONSE_CANCEL, RESPONSE_DELETE_EVENT, RESPONSE_OK, RESPONSE_YES
from gtk import STOCK_APPLY, STOCK_CANCEL, STOCK_REMOVE, STOCK_YES
from gtk import TREE_VIEW_COLUMN_AUTOSIZE, TREE_VIEW_GRID_LINES_BOTH
from gtk import ICON_SIZE_MENU
from gtk import SORT_ASCENDING
from gtk import SELECTION_NONE
from gtk import STATE_NORMAL
from gtk import WINDOW_TOPLEVEL
from gtk import WIN_POS_MOUSE, WIN_POS_CENTER_ON_PARENT

# methods
from gtk import image_new_from_icon_name
from gtk import main
from gtk import main_quit
from gtk import check_version

# gtk2 (or more specifically, pygtk2) provided all of it's enums and
# constants in the top level 'gtk' module. Gtk3 (or more specifically, gobject
# introspection of Gtk3) moves them into seperate classes. The enum
# classes here map the Gtk3 class and attr names to gtk2 names.


class ButtonBoxStyle(object):
    END = BUTTONBOX_END


class ButtonsType(object):
    OK = BUTTONS_OK
    OK_CANCEL = BUTTONS_OK_CANCEL
    YES_NO = BUTTONS_YES_NO


class FileChooserAction(object):
    OPEN = FILE_CHOOSER_ACTION_OPEN


class IconSize(object):
    MENU = ICON_SIZE_MENU


class MessageType(object):
    WARNING = MESSAGE_WARNING
    QUESTION = MESSAGE_QUESTION
    INFO = MESSAGE_INFO
    ERROR = MESSAGE_ERROR


class ResponseType(object):
    OK = RESPONSE_OK
    YES = RESPONSE_YES
    DELETE_EVENT = RESPONSE_DELETE_EVENT
    CANCEL = RESPONSE_CANCEL


class SortType(object):
    ASCENDING = SORT_ASCENDING


class StateType(object):
    NORMAL = STATE_NORMAL


class SelectionMode(object):
    NONE = SELECTION_NONE


class TreeViewColumnSizing(object):
    AUTOSIZE = TREE_VIEW_COLUMN_AUTOSIZE


class TreeViewGridLines(object):
    BOTH = TREE_VIEW_GRID_LINES_BOTH


class WindowType(object):
    TOPLEVEL = WINDOW_TOPLEVEL


class WindowPosition(object):
    MOUSE = WIN_POS_MOUSE
    CENTER_ON_PARENT = WIN_POS_CENTER_ON_PARENT


class GaImage(Image):
    """A subclass of Gtk.Image that provides a Gtk3 style constructor."""
    @classmethod
    def new_from_icon_name(cls, icon_name, size):
        return image_new_from_icon_name(icon_name, size)

# NOTE: ga.Gtk.Image will be the GaImage subclass above, and not the gtk2
#       gtk.Image. However, aside from the added constructor, the rest of
#       the Gtk.Image is not provided here.
Image = GaImage


# Gtk2's TreeRowReference is a class, while Gtk3's TreeRowReference is
# non-callable class that has to be constructed with it's .new() method.
# Provide a helper method that provides a compatible interface. snake_case
# naming used to distinquish it from the "real" TreeRowReference.
def tree_row_reference(model, path):
    return TreeRowReference(model, path)

# Attempt to keep the list of faux Gtk 3 names we are
# providing to a min.
constants = [STOCK_APPLY, STOCK_CANCEL, STOCK_REMOVE, STOCK_YES]

enums = [ButtonsType, ButtonBoxStyle, FileChooserAction, IconSize, MessageType,
         ResponseType, SelectionMode, SortType, StateType, TreeViewColumnSizing,
         TreeViewGridLines, WindowPosition]

widgets = [AboutDialog, Adjustment, Builder, Button, Calendar, CellRendererPixbuf,
           CellRendererProgress, CellRendererSpin,
           CellRendererText, CellRendererToggle,
           Entry, FileChooserDialog, FileFilter, Frame, HBox,
           HButtonBox, Image, Label, ListStore, MessageDialog,
           RadioButton, SpinButton, TextBuffer, TreeStore, TreeView, TreeViewColumn,
           VBox, Viewport]

methods = [check_version, main, main_quit]

__all__ = widgets + constants + methods + enums
