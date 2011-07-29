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
from mock import Mock

from subscription_manager import hwprobe


class HardwareProbeTests(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_command_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 2

        # Pick up the mocked class
        reload(hwprobe)
        hw = hwprobe.Hardware()
        self.assertRaises(hwprobe.CalledProcessError, hw._get_output, 'test')

    @patch('subprocess.Popen')
    def test_command_valid(self, MockPopen):
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
        expected = {'virt.is_guest': False, 'virt.host_type': 'Not Applicable'}
        self.assertEquals(expected, hw.getVirtInfo())

    @patch('subprocess.Popen')
    def test_virt_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 255

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': 'Unknown'}
        self.assertEquals(expected, hw.getVirtInfo())

    @patch("__builtin__.open")
    def test_distro_no_release(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.side_effect = IOError()
        self.assertRaises(IOError, hw.getReleaseInfo)

    @patch("__builtin__.open")
    def test_distro_bogus_content_no_platform_module(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        hwprobe.platform = None
        MockOpen.return_value.readline.return_value = "this is not really a release file of any sort"
        self.assertEquals(hw.getReleaseInfo(), {'distribution.version': 'unknown', 'distribution.name': 'unknown', 'distribution.id': 'unknown'})

    @patch("__builtin__.open")
    def test_distro(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)"
        self.assertEquals(hw.getReleaseInfo(), {'distribution.version': '42', 'distribution.name': 'Awesome OS', 'distribution.id': 'Go4It'})

    @patch("__builtin__.open")
    def test_distro_newline_in_release(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)\n\n"
        self.assertEquals(hw.getReleaseInfo(), {'distribution.version': '42', 'distribution.name': 'Awesome OS', 'distribution.id': 'Go4It'})

    def test_meminfo(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        mem = hw.getMemInfo()
        # not great tests, but alas
        self.assertEquals(len(mem), 2)
        for key in mem:
            assert key in ['memory.memtotal', 'memory.swaptotal']

    # this test will probably fail on a machine with
    # no network.
    def test_networkinfo(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net = hw.getNetworkInfo()
        self.assertEquals(len(net), 2)
        for key in net:
            assert key in ['network.hostname', 'network.ipaddr']

    def test_network_interfaces(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int['net.interface.lo.ipaddr'], '127.0.0.1')

# FIXME: not real useful as non-root, plus noisy
#    def test_platform_specific_info(self):
#        reload(hwprobe)
#        hw = hwprobe.Hardware()
#        platform_info = hw.getPlatformSpecificInfo()
#        # this is going to be empty as non root
#        print platform_info

    @patch("os.listdir")
    def test_cpu_info(self, MockListdir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        MockSocketId = Mock()
        MockListdir.return_value = ["cpu0", "cpu1"]
        MockSocketId.return_value = "0"
        hw._getSocketIdForCpu = MockSocketId
        self.assertEquals(hw.getCpuInfo(), {'cpu.cpu(s)': 2, 'cpu.core(s)_per_socket': 2, 'cpu.cpu_socket(s)': 1})

    @patch("os.listdir")
    def test_cpu_info_lots_cpu(self, MockListdir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        MockSocketId = Mock()
        MockListdir.return_value = ["cpu%s" % i for i in range(0, 2000)]
        MockSocketId.return_value = "0"
        hw._getSocketIdForCpu = MockSocketId
        self.assertEquals(hw.getCpuInfo(), {'cpu.cpu(s)': 2000, 'cpu.core(s)_per_socket': 2000, 'cpu.cpu_socket(s)': 1})

    @patch("os.listdir")
    def test_cpu_info_other_files(self, MockListdir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        MockSocketId = Mock()
        MockListdir.return_value = ["cpu0", "cpu1",  # normal cpu ids (valid)
                                    "cpu123123",     # big cpu   (valid)
                                    "cpu_",          # not valid
                                    "cpufreq",       # this exists but is not a cpu
                                    "cpuidle",       # also exists
                                    "cpu0foo",       # only cpuN are valid
                                    "cpu11111111 ",  # trailing space, not valie
                                    "cpu00"]          # odd name, but valid I guess
        MockSocketId.return_value = "0"
        hw._getSocketIdForCpu = MockSocketId
        self.assertEquals(hw.getCpuInfo(), {'cpu.cpu(s)': 4, 'cpu.core(s)_per_socket': 4, 'cpu.cpu_socket(s)': 1})
