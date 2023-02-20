# Make argparse friendlier to i18n/l10n
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
Make argparse friendlier to i18n/l10n

Just use this instead of argparse, the interface should be the same.

For some background, see:
http://bugs.python.org/issue4319
"""
import argparse
from argparse import ArgumentParser as _ArgumentParser
import sys

from subscription_manager.i18n import ugettext as _


argparse._ = _

# note default is lower caps
USAGE = _("%(prog)s [OPTIONS]")


class ArgumentParser(_ArgumentParser):
    def print_help(self) -> None:
        sys.stdout.write(self.format_help())

    def error(self, msg: str) -> None:
        """
        Override default error handler to localize

        prints command usage, then the error string, and exits.
        """
        self.print_usage(sys.stderr)
        # translators: arg 1 is the program name, arg 2 is the error message
        print((_("{prog}: error: {msg}")).format(prog=self.prog, msg=msg))
        self.exit(2)
