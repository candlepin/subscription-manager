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

import cStringIO

from mock import patch
from mock import Mock

from subscription_manager import hwprobe

PROC_BONDING_RR = """Ethernet Channel Bonding Driver: v3.6.0 (September 26, 2009)

Bonding Mode: load balancing (round-robin)
MII Status: up
MII Polling Interval (ms): 100
Up Delay (ms): 0
Down Delay (ms): 0

Slave Interface: eth0
MII Status: up
Speed: 100 Mbps
Duplex: full
Link Failure Count: 0
Permanent HW addr: 52:54:00:07:03:ba
Slave queue ID: 0

Slave Interface: eth1
MII Status: up
Speed: 100 Mbps
Duplex: full
Link Failure Count: 0
Permanent HW addr: 52:54:00:66:20:f7
Slave queue ID: 0
"""

PROC_BONDING_ALB = """Ethernet Channel Bonding Driver: v3.6.0 (September 26, 2009)

Bonding Mode: adaptive load balancing
Primary Slave: None
Currently Active Slave: eth0
MII Status: up
MII Polling Interval (ms): 100
Up Delay (ms): 0
Down Delay (ms): 0

Slave Interface: eth0
MII Status: up
Speed: 100 Mbps
Duplex: full
Link Failure Count: 0
Permanent HW addr: 52:54:00:07:03:ba
Slave queue ID: 0

Slave Interface: eth1
MII Status: up
Speed: 100 Mbps
Duplex: full
Link Failure Count: 0
Permanent HW addr: 52:54:00:66:20:f7
Slave queue ID: 0
"""


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
        self.assertEquals(hw.getReleaseInfo(), {'distribution.version': 'Unknown', 'distribution.name': 'Unknown', 'distribution.id': 'Unknown'})

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
        self.assertEquals(len(net), 3)
        for key in net:
            assert key in ['network.hostname', 'network.ipv4_address', 'network.ipv6_address']

    def test_network_interfaces(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)
        self.assertFalse('net.interface.sit0.mac_address' in net_int)

    # simulate some wacky interfaces
    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_none(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int, {})

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_multiple_ipv4(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        MockGetDevices.return_value = ['eth0']
        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="eth0")
        mock_info.get_ipv6_addresses.return_value = []
        mock_ipv4s = [Mock(address="10.0.0.1", netmask="24", broadcast="Unknown"),
                      Mock(address="10.0.0.2", netmask="24", broadcast="Unknown")]
        mock_info.get_ipv4_addresses = Mock(return_value=mock_ipv4s)
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.getNetworkInterfaces()

        # FIXME/TODO/NOTE: We currently expect to get just the last interface
        # listed in this scenario. But... that is wrong. We should really
        # be supporting multiple addresses per interface in some yet
        # undetermined fashion
        self.assertEquals(net_int['net.interface.eth0.ipv4_address'], '10.0.0.2')

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockGetDevices.return_value = ['lo']
        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="lo")

        mock_info.get_ipv6_addresses.return_value = []
        mock_ipv4 = Mock(address="127.0.0.1",
                         netmask="24",
                         broadcase="Unknown")
        mock_info.get_ipv4_addresses = Mock(return_value=[mock_ipv4])
        MockGetInterfacesInfo.return_value = [mock_info]
        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_sit(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockGetDevices.return_value = ['sit0']
        mock_ipv6 = Mock(address="::1",
                         netmask="/128",
                         scope="global")

        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="sit0")
        mock_info.get_ipv6_addresses.return_value = [mock_ipv6]
        mock_info.get_ipv4_addresses.return_value = []
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.getNetworkInterfaces()
        # ignore mac address for sit* interfaces (bz #838123)
        self.assertFalse('net.interface.sit0.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo_ethtool_no_get_ipv4_addresses(self,
                                                                      MockGetInterfacesInfo,
                                                                      MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockGetDevices.return_value = ['lo']
        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="lo",
                         ipv4_address="127.0.0.1",
                         ipv4_netmask="24",
                         ipv4_broadcast="Unknown")
        mock_info.get_ipv6_addresses.return_value = []

        # mock etherinfo not having a get_ipv4_addresses method
        # if this fails, you need a mock that supports deleting
        # attributes from mocks, ala mock 1.0+
        try:
            del mock_info.get_ipv4_addresses
        except AttributeError:
            self.fail("You probably need a newer version of 'mock' installed, 1.0 or newer")

        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo_ipv6(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockGetDevices.return_value = ['lo']

        mock_ipv6 = Mock(address="::1",
                         netmask="/128",
                         scope="global")

        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="lo")
        mock_info.get_ipv6_addresses.return_value = [mock_ipv6]
        mock_info.get_ipv4_addresses.return_value = []
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.getNetworkInterfaces()
        self.assertEquals(net_int['net.interface.lo.ipv6_address.global'], '::1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch("__builtin__.open")
    def test_get_slave_hwaddr_rr(self, MockOpen):
        reload(hwprobe)
        MockOpen.return_value = cStringIO.StringIO(PROC_BONDING_RR)
        hw = hwprobe.Hardware()
        slave_hw = hw._get_slave_hwaddr("bond0", "eth0")
        # note we .upper the result
        self.assertEquals("52:54:00:07:03:BA", slave_hw)

    @patch("__builtin__.open")
    def test_get_slave_hwaddr_alb(self, MockOpen):
        reload(hwprobe)
        MockOpen.return_value = cStringIO.StringIO(PROC_BONDING_ALB)
        hw = hwprobe.Hardware()
        slave_hw = hw._get_slave_hwaddr("bond0", "eth0")
        # note we .upper the result
        self.assertEquals("52:54:00:07:03:BA", slave_hw)

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
