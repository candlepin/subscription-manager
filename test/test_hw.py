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

import unittest
from mock import patch

import hwprobe
import subprocess

class HardwareProbeTests(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_command_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 2

        # Pick up the mocked class
        reload(hwprobe)
        hw = hwprobe.Hardware()
        self.assertRaises(subprocess.CalledProcessError, hw._get_output, 'test')

    @patch('subprocess.Popen')
    def test_commond_valid(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['this is valid', None]
        MockPopen.return_value.poll.return_value = 0

        # Pick up the mocked class
        reload(hwprobe)
        hw = hwprobe.Hardware()
        self.assertEquals('this is valid', hw._get_output('testing'))

    @patch('subprocess.Popen')
    def test_virt_guest(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['kvm', None]
        MockPopen.return_value.poll.return_value = 0

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': True, 'virt.host_type': 'kvm'}
        self.assertEquals(expected, hw.getVirtInfo())

    @patch('subprocess.Popen')
    def test_virt_bare_metal(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 0

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': False, 'virt.host_type': ''}
        self.assertEquals(expected, hw.getVirtInfo())

    @patch('subprocess.Popen')
    def test_virt_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 255

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': 'Unknown'}
        self.assertEquals(expected, hw.getVirtInfo())

