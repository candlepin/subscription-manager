
from gtk import *
#from gtk import Button, Calendar, CellRendererText, Entry, HBox
#from gtk import Image, Label, ListStore, TreeStore
#from gtk import TextBuffer, TreeViewColumn
#from gtk import STOCK_APPLY, STOCK_REMOVE, STOCK_YES
#from gtk import ICON_SIZE_MENU
#from gtk import SORT_ASCENDING
#from gtk import SELECTION_NONE
#from gtk import STATE_NORMAL
#from gtk import WINDOW_TOPLEVEL
#from gtk import main_quit


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


class WindowType(object):
    TOPLEVEL = WINDOW_TOPLEVEL


class WindowPosition(object):
    MOUSE = WIN_POS_MOUSE
    CENTER_ON_PARENT = WIN_POS_CENTER_ON_PARENT


class GaImage(Image):
    @classmethod
    def new_from_icon_name(cls, icon_name, size):
        return image_new_from_icon_name(icon_name, size)
# NOTE: icky
Image = GaImage


def tree_row_reference(model, path):
    return TreeRowReference(model, path)

# Attempt to keep the list of faux Gtk 3 names we are
# providing to a min.
constants = [STOCK_APPLY, STOCK_REMOVE, STOCK_YES]

enums = [ButtonsType, ButtonBoxStyle, FileChooserAction, IconSize, MessageType,
         ResponseType, SelectionMode, SortType, StateType, TreeViewColumnSizing,
         WindowPosition]

widgets = [AboutDialog, Adjustment, Button, Calendar, CellRendererPixbuf,
           CellRendererProgress, CellRendererSpin,
           CellRendererText, Entry, FileChooserDialog, FileFilter, Frame, HBox,
           HButtonBox, Image, Label, ListStore,
           RadioButton, TextBuffer, TreeStore, TreeView, TreeViewColumn,
           VBox, Viewport]

misc = [main_quit]

__all__ = widgets + constants + misc + enums
