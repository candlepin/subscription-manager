from __future__ import print_function, division, absolute_import

import os

from gtk import TreeRowReference
from gtk.gdk import threads_init


# Gtk2's TreeRowReference is a class, while Gtk3's TreeRowReference is
# non-callable class that has to be constructed with it's .new() method.
# Provide a helper method that provides a compatible interface. snake_case
# naming used to distinquish it from the "real" TreeRowReference.
def tree_row_reference(model, path):
    return TreeRowReference(model, path)


# These are not exact replacements, but for our purposes they
# are used in the same places in the same way. A purely GObject
# app with no gui may want to distinquish.
threads_init = threads_init

# ../../gui/data/glade/
ourfile = __file__
GTK_BUILDER_FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                      "../../gui/data/glade/"))
GTK_BUILDER_FILES_SUFFIX = "glade"

GTK_COMPAT_VERSION = "2"

__all__ = [GTK_BUILDER_FILES_DIR,
           GTK_BUILDER_FILES_SUFFIX]
