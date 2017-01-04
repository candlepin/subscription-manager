# Copyright (c) 2016 Red Hat, Inc.
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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
from test.fixture import open_mock

from rhsmlib.facts import collector


class GetArchTest(unittest.TestCase):
    @mock.patch('platform.machine')
    def test_returns_arch(self, mock_machine):
        mock_machine.return_value = "hello_arch"
        arch = collector.get_arch()
        self.assertEqual("hello_arch", arch)

    def test_returns_arch_override(self):
        with open_mock(content="hello_arch"):
            arch = collector.get_arch(prefix="/does/not/exist")
            self.assertEqual("hello_arch", arch)
