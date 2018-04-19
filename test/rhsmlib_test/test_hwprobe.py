from __future__ import print_function, division, absolute_import

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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import six

from mock import patch
from mock import Mock
from mock import mock_open

import test.fixture
from test.fixture import OPEN_FUNCTION
from rhsmlib.facts import hwprobe

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

PROC_STAT = """cpu  1251631 1521 234099 26677635 43020 53378 18245 0 136791 0
cpu0 170907 672 36975 5235552 21053 18369 7169 0 8215 0
cpu1 162918 87 22790 3049644 2898 7180 2735 0 37398 0
cpu2 167547 104 36469 3045029 6222 6375 2022 0 5443 0
cpu3 116384 86 21325 3103226 2006 3503 999 0 3330 0
cpu4 214747 243 36747 3002774 3602 6008 1688 0 51985 0
cpu5 116967 88 20921 3104477 1791 3092 875 0 4196 0
cpu6 182738 158 37153 3035995 3449 6016 1926 0 19461 0
cpu7 119420 79 21716 3100934 1997 2833 828 0 6759 0
intr 69987280 31 176 0 0 0 0 0 0 1 11832 0 0 723 0 0 0 67 0 26095 0 0 0 0 77 0 0 733270 16903338 0 305 2485413 22 35708 147 618373 6713 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 176256990
btime 1524062304
processes 66111
procs_running 2
procs_blocked 1
softirq 40290891 49 19260365 9256 986071 674800 7 521934 11078954 0 7759455
"""

OS_RELEASE = """NAME="Awesome OS"
VERSION="42 (Go4It)"
ID="awesomeos"
VERSION_ID="42"
PRETTY_NAME="Awesome OS 42 (Go4It)"
CPE_NAME="cpe:/o:awesomeos:best_linux:42:beta:server"

REDHAT_BUGZILLA_PRODUCT="AwesomeOS Enterprise 42"
REDHAT_BUGZILLA_PRODUCT_VERSION=42.0
REDHAT_SUPPORT_PRODUCT="AwesomeOS Enterprise"
REDHAT_SUPPORT_PRODUCT_VERSION=42.0"""

OS_RELEASE_COLON = """NAME="Awesome OS"
VERSION="42 (Go4It)"
ID="awesomeos"
VERSION_ID="42"
PRETTY_NAME="Awesome OS 42 (Go4It)"
CPE_NAME="cpe:/o:awesomeos:best_linux:42:be\:ta:server"

REDHAT_BUGZILLA_PRODUCT="AwesomeOS Enterprise 42"
REDHAT_BUGZILLA_PRODUCT_VERSION=42.0
REDHAT_SUPPORT_PRODUCT="AwesomeOS Enterprise"
REDHAT_SUPPORT_PRODUCT_VERSION=42.0"""


class TestParseRange(unittest.TestCase):
    def test_single(self):
        r = '1'
        r_list = hwprobe.parse_range(r)
        self.assertEqual([1], r_list)

    def test_range_1_4(self):
        r = '1-4'
        r_list = hwprobe.parse_range(r)
        self.assertEqual([1, 2, 3, 4], r_list)


class TestGatherEntries(unittest.TestCase):
    def test_single(self):
        ent = "1"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(1, len(ent_list))

    def test_multiple(self):
        ent = "1,2,3,4"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(4, len(ent_list))

    def test_range_1_2(self):
        ent = "1-2"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(2, len(ent_list))

    def test_range_2_ranges(self):
        ent = "1-4,9-12"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(8, len(ent_list))

    def test_range_64cpu_example(self):
        ent = "0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(16, len(ent_list))

    def test_range_0_2(self):
        ent = "0,2"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEqual(2, len(ent_list))


class GenericPlatformSpecificInfoProviderTest(test.fixture.SubManFixture):
    def test(self):
        hw_info = {}
        platform_info = hwprobe.GenericPlatformSpecificInfoProvider(hw_info)
        self.assertEqual(0, len(platform_info.info))

    def test_does_nothing(self):
        hw_info = {'foo': '1'}
        platform_info = hwprobe.GenericPlatformSpecificInfoProvider(hw_info)
        self.assertEqual(0, len(platform_info.info))
        self.assertFalse('foo' in platform_info.info)


class HardwareProbeTest(test.fixture.SubManFixture):
    def setUp(self):
        # Note this is patching an *instance* of HardwareCollector, not the class.
        self.hw_check_topo = hwprobe.HardwareCollector()
        self.hw_check_topo_patcher = patch.object(
            self.hw_check_topo,
            'check_for_cpu_topo',
            Mock(return_value=True)
        )
        self.hw_check_topo_patcher.start()
        super(HardwareProbeTest, self).setUp()

    def tearDown(self):
        self.hw_check_topo_patcher.stop()
        super(HardwareProbeTest, self).tearDown()

    @patch(OPEN_FUNCTION)
    def test_distro_no_release(self, MockOpen):
        hw = hwprobe.HardwareCollector()
        MockOpen.side_effect = IOError()
        self.assertRaises(IOError, hw.get_release_info)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_distro_bogus_content_no_platform_module(self, MockOpen, MockExists):
        hw = hwprobe.HardwareCollector()
        MockExists.side_effect = [False, True]
        with patch('rhsmlib.facts.hwprobe.platform'):
            MockOpen.return_value.readline.return_value = "this is not really a release file of any sort"
            expected = {
                'distribution.version': 'Unknown',
                'distribution.name': 'Unknown',
                'distribution.id': 'Unknown',
                'distribution.version.modifier': ''
            }
            self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_distro(self, MockOpen, MockExists):
        MockExists.side_effect = [False, True]
        hw = hwprobe.HardwareCollector()
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)"
        expected = {
            'distribution.version': '42',
            'distribution.name': 'Awesome OS',
            'distribution.id': 'Go4It',
            'distribution.version.modifier': ''
        }
        self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_distro_newline_in_release(self, MockOpen, MockExists):
        hw = hwprobe.HardwareCollector()
        MockExists.side_effect = [False, True]
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)\n\n"
        expected = {
            'distribution.version': '42',
            'distribution.name': 'Awesome OS',
            'distribution.id': 'Go4It',
            'distribution.version.modifier': ''
        }
        self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_manual_distro_bogus_content_os_release(self, MockOpen, MockExists):
        hw = hwprobe.HardwareCollector()
        with patch('rhsmlib.facts.hwprobe.platform'):
            MockExists.return_value = True
            MockOpen.return_value.readlines.return_value = ["This is not really a release file of any sort"]
            expected = {
                'distribution.version': 'Unknown',
                'distribution.name': 'Unknown',
                'distribution.id': 'Unknown',
                'distribution.version.modifier': ''
            }
            self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION, mock_open(read_data="Awesome OS release 42 Mega (Go4It)"))  # TODO figure out why necessary...
    def test_distro_with_platform(self, MockExists):
        MockExists.return_value = False
        hw = hwprobe.HardwareCollector()
        expected = {
            'distribution.version': '42',
            'distribution.name': 'Awesome OS',
            'distribution.id': 'Go4It',
            'distribution.version.modifier': 'Unknown'
        }
        self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_manual_distro_with_modifier(self, MockOpen, MockExists):
        MockExists.side_effect = [False, True]
        hw = hwprobe.HardwareCollector()
        with patch('rhsmlib.facts.hwprobe.platform'):
            MockOpen.return_value.readline.return_value = "Awesome OS release 42 Mega (Go4It)"
            expected = {
                'distribution.version': '42',
                'distribution.name': 'Awesome OS',
                'distribution.id': 'Go4It',
                'distribution.version.modifier': 'mega'
            }
            self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_distro_os_release(self, MockOpen, MockExists):
        MockExists.return_value = True
        hw = hwprobe.HardwareCollector()
        with patch('rhsmlib.facts.hwprobe.platform'):
            MockOpen.return_value.readlines.return_value = OS_RELEASE.split('\n')
            expected = {
                'distribution.version': '42',
                'distribution.name': 'Awesome OS',
                'distribution.id': 'Go4It',
                'distribution.version.modifier': 'beta'
            }
            self.assertEqual(hw.get_release_info(), expected)

    @patch("os.path.exists")
    @patch(OPEN_FUNCTION)
    def test_distro_os_release_colon(self, MockOpen, MockExists):
        MockExists.return_value = True
        hw = hwprobe.HardwareCollector()
        with patch('rhsmlib.facts.hwprobe.platform'):
            MockOpen.return_value.readlines.return_value = OS_RELEASE_COLON.split('\n')
            expected = {
                'distribution.version': '42',
                'distribution.name': 'Awesome OS',
                'distribution.id': 'Go4It',
                'distribution.version.modifier': 'be:ta'
            }
            self.assertEqual(hw.get_release_info(), expected)

    def test_meminfo(self):
        hw = hwprobe.HardwareCollector()
        mem = hw.get_mem_info()
        # not great tests, but alas
        self.assertEqual(len(mem), 2)
        for key in mem:
            assert key in ['memory.memtotal', 'memory.swaptotal']

    # this test will probably fail on a machine with
    # no network.
    def test_networkinfo(self):
        hw = hwprobe.HardwareCollector()
        net = hw.get_network_info()
        expected = set(['network.fqdn', 'network.hostname', 'network.ipv4_address', 'network.ipv6_address'])
        self.assertEqual(expected, set(net.keys()))

    def test_network_interfaces(self):
        hw = hwprobe.HardwareCollector()
        net_int = hw.get_network_interfaces()
        self.assertEqual(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)
        self.assertFalse('net.interface.sit0.mac_address' in net_int)

    # simulate some wacky interfaces
    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_none(self, MockGetInterfacesInfo, MockGetDevices):
        hw = hwprobe.HardwareCollector()
        net_int = hw.get_network_interfaces()
        self.assertEqual(net_int, {})

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_multiple_ipv4(self, MockGetInterfacesInfo, MockGetDevices):
        hw = hwprobe.HardwareCollector()

        MockGetDevices.return_value = ['eth0']
        mock_info = Mock(mac_address="00:00:00:00:00:00", device="eth0")
        mock_info.get_ipv6_addresses.return_value = []
        mock_ipv4s = [Mock(address="10.0.0.1", netmask="24", broadcast="Unknown"),
                      Mock(address="10.0.0.2", netmask="24", broadcast="Unknown")]
        mock_info.get_ipv4_addresses = Mock(return_value=mock_ipv4s)
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.get_network_interfaces()

        self.assertEqual(net_int['net.interface.eth0.ipv4_address'], '10.0.0.2')
        self.assertEqual(net_int['net.interface.eth0.ipv4_address_list'], '10.0.0.1, 10.0.0.2')

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo(self, MockGetInterfacesInfo, MockGetDevices):
        hw = hwprobe.HardwareCollector()
        MockGetDevices.return_value = ['lo']
        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="lo")

        mock_info.get_ipv6_addresses.return_value = []
        mock_ipv4 = Mock(address="127.0.0.1",
                         netmask="24",
                         broadcase="Unknown")
        mock_info.get_ipv4_addresses = Mock(return_value=[mock_ipv4])
        MockGetInterfacesInfo.return_value = [mock_info]
        net_int = hw.get_network_interfaces()
        self.assertEqual(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_sit(self, MockGetInterfacesInfo, MockGetDevices):
        hw = hwprobe.HardwareCollector()
        MockGetDevices.return_value = ['sit0']
        mock_ipv6 = Mock(address="::1",
                         netmask="/128",
                         scope="global")

        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="sit0")
        mock_info.get_ipv6_addresses.return_value = [mock_ipv6]
        mock_info.get_ipv4_addresses.return_value = []
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.get_network_interfaces()
        # ignore mac address for sit* interfaces (bz #838123)
        self.assertFalse('net.interface.sit0.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo_ethtool_no_get_ipv4_addresses(self,
        MockGetInterfacesInfo, MockGetDevices):

        hw = hwprobe.HardwareCollector()
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

        net_int = hw.get_network_interfaces()
        self.assertEqual(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_just_lo_ipv6(self, MockGetInterfacesInfo, MockGetDevices):
        hw = hwprobe.HardwareCollector()
        MockGetDevices.return_value = ['lo']

        mock_ipv6 = Mock(address="::1",
                         netmask="/128",
                         scope="global")

        mock_info = Mock(mac_address="00:00:00:00:00:00",
                         device="lo")
        mock_info.get_ipv6_addresses.return_value = [mock_ipv6]
        mock_info.get_ipv4_addresses.return_value = []
        MockGetInterfacesInfo.return_value = [mock_info]

        net_int = hw.get_network_interfaces()
        self.assertEqual(net_int['net.interface.lo.ipv6_address.global'], '::1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)

    @patch(OPEN_FUNCTION)
    def test_get_slave_hwaddr_rr(self, MockOpen):
        MockOpen.return_value = six.StringIO(PROC_BONDING_RR)
        hw = hwprobe.HardwareCollector()
        slave_hw = hw._get_slave_hwaddr("bond0", "eth0")
        # note we .upper the result
        self.assertEqual("52:54:00:07:03:BA", slave_hw)

    @patch(OPEN_FUNCTION)
    def test_get_slave_hwaddr_alb(self, MockOpen):
        MockOpen.return_value = six.StringIO(PROC_BONDING_ALB)
        hw = hwprobe.HardwareCollector()
        slave_hw = hw._get_slave_hwaddr("bond0", "eth0")
        # note we .upper the result
        self.assertEqual("52:54:00:07:03:BA", slave_hw)

    def test_parse_s390_sysinfo_empty(self):
        cpu_count = 0
        sysinfo_lines = []

        ret = self.hw_check_topo._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)
        self.assertTrue(ret is None)

    def test_parse_s390_sysinfo(self):
        cpu_count = 24
        sysinfo_lines = ["CPU Topology SW:      0 0 0 4 6 4"]

        ret = self.hw_check_topo._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)

        self.assertEqual(24, ret['socket_count'])
        self.assertEqual(4, ret['book_count'])
        self.assertEqual(6, ret['sockets_per_book'])
        self.assertEqual(4, ret['cores_per_socket'])

    @patch(OPEN_FUNCTION, mock_open(read_data=PROC_STAT))
    def test_parse_proc_stat_btime(self):
        expected_btime = "1524062304"

        hw = hwprobe.HardwareCollector()
        ret = hw.get_proc_stat()
        self.assertEqual(expected_btime, ret['proc_stat.btime'])

    @patch.object(hwprobe.HardwareCollector, 'count_cpumask_entries')
    @patch("os.listdir")
    def test_cpu_info_s390(self, mock_list_dir, mock_mask):
        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 3)]

        # 32 cpus
        # 16 cores, 2 threads per core = each cpu has two thread siblings
        # 1 core per socket
        # 8 sockets per book, = each cpu has 8 core siblings
        # 2 books, each check has 16 book siblings
        def count_cpumask(cpu, field):
            cpumask_vals = {
                'thread_siblings_list': 1,
                'core_siblings_list': 1,
                'book_siblings_list': 1
            }
            return cpumask_vals[field]

        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 3,
                'cpu.socket(s)_per_book': 1,
                'cpu.core(s)_per_socket': 1,
                'cpu.thread(s)_per_core': 1,
                'cpu.cpu_socket(s)': 3,
                'cpu.book(s)': 3,
                'cpu.book(s)_per_cpu': 1,
                'cpu.topology_source': 's390 book_siblings_list'
            }

            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch.object(hwprobe.HardwareCollector, 'has_s390x_sysinfo')
    @patch.object(hwprobe.HardwareCollector, 'read_s390x_sysinfo')
    @patch.object(hwprobe.HardwareCollector, 'check_for_cpu_topo')
    @patch("os.listdir")
    def test_cpu_info_s390_sysinfo(self, mock_list_dir, mock_topo, mock_read_sysinfo, mock_has_sysinfo):
        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 20)]
        mock_has_sysinfo.return_value = True
        mock_topo.return_value = True
        mock_read_sysinfo.return_value = ["CPU Topology SW:      0 0 0 4 6 4"]

        self.hw_check_topo.arch = 's390x'

        # 20 cpus
        # 24 cores, 1 threads per core
        # 1 thread per core, 1 core per socket, 1 socket per book via /sys, but
        # /proc/sysinfo says 4 books of 6 sockets of 4 cores
        #
        # even though we have cpu topo from sysinfo, we also have
        # info from the kernel, which we use in that case
        #
        # and we prefer /proc/sysinfo
        # how do 24 sockets have 20 cpu? The hardware itself
        # has 96 cpus. 54 of those are enabled at the
        # hardware level. Of those 51, 21 are "configured".
        # The LPAR is setup to use 20 of those 21 cpus
        # (and in this setup, actually only 18 of those
        # are "configured").
        def count_cpumask(cpu, field):
            cpumask_vals = {
                'thread_siblings_list': 1,
                'core_siblings_list': 1,
                'book_siblings_list': 1
            }
            return cpumask_vals[field]

        # for this case, we prefer the sysinfo numbers
        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 20,
                'cpu.socket(s)_per_book': 6,
                'cpu.core(s)_per_socket': 4,
                'cpu.thread(s)_per_core': 1,
                'cpu.book(s)': 4,
                'cpu.cpu_socket(s)': 24,
                'cpu.topology_source': 's390x sysinfo'
            }
            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch.object(hwprobe.HardwareCollector, 'count_cpumask_entries')
    @patch("os.listdir")
    def test_cpu_info(self, mock_list_dir, mock_count):
        def count_cpumask(cpu, field):
            cpumask_vals = {
                'thread_siblings_list': 1,
                'core_siblings_list': 2,
                'book_siblings_list': None
            }
            return cpumask_vals[field]

        mock_list_dir.return_value = ["cpu0", "cpu1"]
        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 2,
                'cpu.core(s)_per_socket': 2,
                'cpu.cpu_socket(s)': 1,
                'cpu.thread(s)_per_core': 1,
                'cpu.topology_source': 'kernel /sys cpu sibling lists'
            }
            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch("os.listdir")
    def test_cpu_info_no_topo(self, mock_list_dir):
        def count_cpumask(cpu, field):
            cpumask_vals = {
                'thread_siblings_list': None,
                'core_siblings_list': None,
                'book_siblings_list': None
            }
            return cpumask_vals[field]

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 16)]

        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 16,
                'cpu.core(s)_per_socket': 1,
                'cpu.cpu_socket(s)': 16,
                'cpu.thread(s)_per_core': 1,
                'cpu.topology_source': "fallback one socket"
            }
            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch.object(hwprobe.HardwareCollector, "read_physical_id")
    @patch("os.listdir")
    def test_cpu_info_no_topo_ppc64_physical_id(self, mock_list_dir,
                                                mock_read_physical):
        self.hw_check_topo.arch = "ppc64"

        def get_physical(cpu_file):
            # pretend we have two physical package ids
            return int(cpu_file[-1]) % 2

        def count_cpumask(cpu, field):
            cpumask_vals = {
                'thread_siblings_list': None,
                'core_siblings_list': None,
                'book_siblings_list': None
            }
            return cpumask_vals[field]

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 8)]
        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            with patch.object(self.hw_check_topo, 'read_physical_id', Mock(side_effect=get_physical)):
                expected = {
                    'cpu.cpu(s)': 8,
                    'cpu.core(s)_per_socket': 4,
                    'cpu.cpu_socket(s)': 2,
                    'cpu.thread(s)_per_core': 1,
                    'cpu.topology_source': 'ppc64 physical_package_id'
                }
                self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch("os.listdir")
    def test_cpu_info_lots_cpu(self, mock_list_dir):
        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 2000)]

        def count_cpumask(cpu, field):
            vals = {
                'thread_siblings_list': 1,
                #'core_siblings_list': 2,
                'core_siblings_list': 2000,
                'book_siblings_list': None
            }
            return vals[field]

        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 2000,
                'cpu.core(s)_per_socket': 2000,
                'cpu.thread(s)_per_core': 1,
                'cpu.cpu_socket(s)': 1,
                'cpu.topology_source': 'kernel /sys cpu sibling lists'
            }
            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())

    @patch("os.listdir")
    def test_cpu_info_other_files(self, mock_list_dir):
        mock_list_dir.return_value = [
            "cpu0", "cpu1",  # normal cpu ids (valid)
            "cpu123123",     # big cpu   (valid)
            "cpu_",          # not valid
            "cpufreq",       # this exists but is not a cpu
            "cpuidle",       # also exists
            "cpu0foo",       # only cpuN are valid
            "cpu11111111 ",  # trailing space, not valie
            "cpu00"          # odd name, but valid I guess
        ]

        def count_cpumask(cpu, field):
            vals = {
                'thread_siblings_list': 1,
                #'core_siblings_list': 2,
                'core_siblings_list': 4,
                'book_siblings_list': None
            }
            return vals[field]

        with patch.object(self.hw_check_topo, 'count_cpumask_entries', Mock(side_effect=count_cpumask)):
            expected = {
                'cpu.cpu(s)': 4,
                'cpu.core(s)_per_socket': 4,
                'cpu.thread(s)_per_core': 1,
                'cpu.cpu_socket(s)': 1,
                'cpu.topology_source': 'kernel /sys cpu sibling lists'
            }
            self.assert_equal_dict(expected, self.hw_check_topo.get_cpu_info())


class TestLscpu(unittest.TestCase):
    @patch('os.environ', {
        'LANGUAGE': 'ja_JP.eucJP',
        'LC_ALL': 'ja_JP.eucJP',
        'LC_CTYPE': 'ja_JP.eucJP',
        'LANG': 'ja_JP.eucJP',
    })
    def test_lscpu_ignores_locale(self):
        hw_check_topo = hwprobe.HardwareCollector()
        facts = hw_check_topo.get_ls_cpu_info()
        # if all values can be encoded as ascii, then lscpu is not using JP locale
        for key, value in facts.items():
            key.encode('ascii')
            value.encode('ascii')
