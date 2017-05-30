from __future__ import print_function, division, absolute_import

import os
from gi.repository import Gtk
from gi.repository import GObject

# ../../gui/data/glade/
ourfile = __file__
GTK_BUILDER_FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                      "../gui/data/ui/"))
GTK_BUILDER_FILES_SUFFIX = "ui"

GTK_COMPAT_VERSION = "3"


# gtk3 requires constructing with .new(), where
# gtk2 does not have a .new()
def tree_row_reference(model, path):
    return Gtk.TreeRowReference.new(model, path)


threads_init = GObject.threads_init
