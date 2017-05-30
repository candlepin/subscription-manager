from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

from rhsmlib.compat import subprocess_compat as compat
from subprocess import CalledProcessError
from mock import patch


class SubprocessCompatTest(unittest.TestCase):
    @patch('subprocess.Popen')
    def test_command_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 2

        # Pick up the mocked class
        self.assertRaises(CalledProcessError, compat.check_output_2_6, 'bad_command')
