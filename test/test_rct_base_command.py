#
# Copyright (c) 2012 Red Hat, Inc.
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

import unittest
from rct.commands import RCTCliCommand

from subscription_manager.cli import InvalidCLIOptionError


class RCTCliCommandTests(unittest.TestCase):

    def test_file_arg_required(self):
        command = RCTCliCommand()
        try:
            command.main([])
            self.fail("Expected InvalidCLIOptionError since no file arg.")
        except InvalidCLIOptionError, e:
            self.assertEqual("You must specify a certificate file.",
                             str(e))

    def test_invalid_file_arg(self):
        command = RCTCliCommand()
        try:
            command.main(["this_file_does_not_exist.crt"])
            self.fail("Expected InvalidCLIOptionError since no file does not exist.")
        except InvalidCLIOptionError, e:
            self.assertEqual("The specified certificate file does not exist.", str(e))
