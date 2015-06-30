
import os
# so ga.gtk_compat.tree_row_reference finds it
from Gtk import tree_row_reference

# ../../gui/data/glade/
ourfile = __file__
GTK_BUILDER_FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                      "../../gui/data/glade/"))
GTK_BUILDER_FILES_SUFFIX = "glade"

__all__ = [GTK_BUILDER_FILES_DIR,
           GTK_BUILDER_FILES_SUFFIX,
           tree_row_reference]
