
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GdkPixbuf


# gtk3 requires constructing with .new(), where
# gtk2 does not have a .new()
def tree_row_reference(model, path):
    return Gtk.TreeRowReference.new(model, path)


methods = [tree_row_reference]
__all__ = [GLib, GObject, Gdk, Gtk, Pango, GdkPixbuf] + methods
