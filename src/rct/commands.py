from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

import sys

from subscription_manager.cli import AbstractCLICommand


class RCTCliCommand(AbstractCLICommand):
    FILE_ARG_IDX = 0

    def __init__(self, name="cli", aliases=None, shortdesc=None, primary=False):
        AbstractCLICommand.__init__(self, name=name, aliases=aliases,
                shortdesc=shortdesc, primary=primary)

    def main(self, args=None):
        # In testing we sometimes specify args, otherwise use the default:
        if args is None:
            # Skip the program name and the command name.
            args = sys.argv[2:]

        (self.options, self.args) = self.parser.parse_args(args)

        self._validate_options()
        return_code = self._do_command()
        if return_code is not None:
            return return_code

    def _get_file_from_args(self):
        if not len(self.args) > self.FILE_ARG_IDX:
            return ''
        return self.args[self.FILE_ARG_IDX]
