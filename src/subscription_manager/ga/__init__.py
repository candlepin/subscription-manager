import os

GTK_VERSION = "gtk3"
if 'SUBMAN_GTK_VERSION' in os.environ:
    GTK_VERSION = os.environ.get('SUBMAN_GTK_VERSION')

if GTK_VERSION == "gtk2":
    from subscription_manager.ga.ga_gtk2 import Gtk
    from subscription_manager.ga.ga_gtk2 import Gdk
    from subscription_manager.ga.ga_gtk2 import GLib
    from subscription_manager.ga.ga_gtk2 import GObject
    from subscription_manager.ga.ga_gtk2 import GdkPixbuf
    from subscription_manager.ga.ga_gtk2 import Pango
    from subscription_manager.ga.ga_gtk2.Gtk import tree_row_reference

if GTK_VERSION == "gtk3":
    # ga_gtk3 has an __all__ that includes all the symbols we
    # provide abstraction for.
    from subscription_manager.ga.ga_gtk3 import GObject
    from subscription_manager.ga.ga_gtk3 import GLib
    from subscription_manager.ga.ga_gtk3 import Gdk
    from subscription_manager.ga.ga_gtk3 import Gtk
    from subscription_manager.ga.ga_gtk3 import GdkPixbuf
    from subscription_manager.ga.ga_gtk3 import Pango
    from subscription_manager.ga.ga_gtk3 import tree_row_reference

#__all__ = [Gtk]
