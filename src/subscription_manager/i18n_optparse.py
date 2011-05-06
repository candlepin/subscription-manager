#
# Make optparse friendlier to i18n/l10n
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Make optparse friendlier to i18n/l10n

Just use this instead of optparse, the interface should be the same.

For some backgorund, see:
http://bugs.python.org/issue4319
"""

import sys
import gettext
_ = gettext.gettext

from optparse import OptionParser as _OptionParser


class OptionParser(_OptionParser):

    # These are a bunch of strings that are marked for translation in optparse,
    # but not actually translated anywhere. Mark them for translation here,
    # so we get it picked up. for local translation, and then optparse will
    # use them.

    #translators: this should have the same translation as "Usage: %s\n"
    _("usage: %s\n")   # For older versions of optparse
    _("Usage: %s\n")
    _("Usage")
    _("%prog [options]")
    _("Options")

    # stuff for option value sanity checking
    _("no such option: %s")
    _("ambiguous option: %s (%s?)")
    _("%s option requires an argument")
    _("%s option requires %d arguments")
    _("%s option does not take a value")
    _("integer")
    _("long integer")
    _("floating-point")
    _("complex")
    _("option %s: invalid %s value: %r")
    _("option %s: invalid choice: %r (choose from %s)")

    # default options
    _("show this help message and exit")
    _("show program's version number and exit")

    def print_help(self):
        sys.stdout.write(self.format_help())

    def error(self, msg):
        """
        Override default error handler to localize

        prints command usage, then the error string, and exits.
        """
        self.print_usage(sys.stderr)
        #translators: arg 1 is the program name, arg 2 is the error message
        self.exit(2, _("%s: error: %s\n") % (self.get_prog_name(), msg))
