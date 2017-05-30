from __future__ import print_function, division, absolute_import

import os

# ../../gui/data/glade/
ourfile = __file__
GTK_BUILDER_FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                      "../../gui/data/glade/"))
GTK_BUILDER_FILES_SUFFIX = "glade"

GTK_COMPAT_VERSION = "2"

__all__ = [GTK_BUILDER_FILES_DIR,
           GTK_BUILDER_FILES_SUFFIX]
