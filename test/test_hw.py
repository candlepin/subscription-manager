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

import fixture
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


class TestParseRange(unittest.TestCase):
    def test_single(self):
        r = '1'
        r_list = hwprobe.parse_range(r)
        self.assertEquals([1], r_list)

    def test_range_1_4(self):
        r = '1-4'
        r_list = hwprobe.parse_range(r)
        self.assertEquals([1, 2, 3, 4], r_list)


class TestGatherEntries(unittest.TestCase):
    def test_single(self):
        ent = "1"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(1, len(ent_list))

    def test_multiple(self):
        ent = "1,2,3,4"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(4, len(ent_list))

    def test_range_1_2(self):
        ent = "1-2"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(2, len(ent_list))

    def test_range_2_ranges(self):
        ent = "1-4,9-12"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(8, len(ent_list))

    def test_range_64cpu_example(self):
        ent = "0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(16, len(ent_list))

    def test_range_0_2(self):
        ent = "0,2"
        ent_list = hwprobe.gather_entries(ent)
        self.assertEquals(2, len(ent_list))


class HardwareProbeTests(fixture.SubManFixture):

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
        self.assertEquals(expected, hw.get_virt_info())

    @patch('subprocess.Popen')
    def test_virt_bare_metal(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 0

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': False, 'virt.host_type': 'Not Applicable'}
        self.assertEquals(expected, hw.get_virt_info())

    @patch('subprocess.Popen')
    def test_virt_error(self, MockPopen):
        MockPopen.return_value.communicate.return_value = ['', None]
        MockPopen.return_value.poll.return_value = 255

        reload(hwprobe)
        hw = hwprobe.Hardware()
        expected = {'virt.is_guest': 'Unknown'}
        self.assertEquals(expected, hw.get_virt_info())

    @patch("__builtin__.open")
    def test_distro_no_release(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.side_effect = IOError()
        self.assertRaises(IOError, hw.get_release_info)

    @patch("__builtin__.open")
    def test_distro_bogus_content_no_platform_module(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        hwprobe.platform = None
        MockOpen.return_value.readline.return_value = "this is not really a release file of any sort"
        self.assertEquals(hw.get_release_info(), {'distribution.version': 'Unknown', 'distribution.name': 'Unknown', 'distribution.id': 'Unknown'})

    @patch("__builtin__.open")
    def test_distro(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)"
        self.assertEquals(hw.get_release_info(), {'distribution.version': '42', 'distribution.name': 'Awesome OS', 'distribution.id': 'Go4It'})

    @patch("__builtin__.open")
    def test_distro_newline_in_release(self, MockOpen):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        MockOpen.return_value.readline.return_value = "Awesome OS release 42 (Go4It)\n\n"
        self.assertEquals(hw.get_release_info(), {'distribution.version': '42', 'distribution.name': 'Awesome OS', 'distribution.id': 'Go4It'})

    def test_meminfo(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        mem = hw.get_mem_info()
        # not great tests, but alas
        self.assertEquals(len(mem), 2)
        for key in mem:
            assert key in ['memory.memtotal', 'memory.swaptotal']

    # this test will probably fail on a machine with
    # no network.
    def test_networkinfo(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net = hw.get_network_info()
        self.assertEquals(len(net), 3)
        for key in net:
            assert key in ['network.hostname', 'network.ipv4_address', 'network.ipv6_address']

    def test_network_interfaces(self):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net_int = hw.get_network_interfaces()
        self.assertEquals(net_int['net.interface.lo.ipv4_address'], '127.0.0.1')
        self.assertFalse('net.interface.lo.mac_address' in net_int)
        self.assertFalse('net.interface.sit0.mac_address' in net_int)

    # simulate some wacky interfaces
    @patch("ethtool.get_devices")
    @patch("ethtool.get_interfaces_info")
    def test_network_interfaces_none(self, MockGetInterfacesInfo, MockGetDevices):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        net_int = hw.get_network_interfaces()
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

        net_int = hw.get_network_interfaces()

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
        net_int = hw.get_network_interfaces()
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

        net_int = hw.get_network_interfaces()
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

        net_int = hw.get_network_interfaces()
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

        net_int = hw.get_network_interfaces()
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
#        platform_info = hw.get_platform_specific_info()
#        # this is going to be empty as non root
#        print platform_info

    def test_parse_s390_sysinfo_empty(self):
        cpu_count = 0
        sysinfo_lines = []

        reload(hwprobe)
        hw = hwprobe.Hardware()

        ret = hw._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)
        self.assertTrue(ret is None)

    def test_parse_s390_sysinfo(self):
        cpu_count = 24
        sysinfo_lines = ["CPU Topology SW:      0 0 0 4 6 4"]

        reload(hwprobe)
        hw = hwprobe.Hardware()

        ret = hw._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)

        self.assertEquals(24, ret['socket_count'])
        self.assertEquals(4, ret['book_count'])
        self.assertEquals(6, ret['sockets_per_book'])
        self.assertEquals(4, ret['cores_per_socket'])

    @patch("os.listdir")
    def test_cpu_info_s390(self, mock_list_dir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 3)]

        def count_cpumask(cpu, field):
            return self.cpumask_vals[field]

        # 32 cpus
        # 16 cores, 2 threads per core = each cpu has two thread siblings
        # 1 core per socket
        # 8 sockets per book, = each cpu has 8 core siblings
        # 2 books, each check has 16 book siblings
        self.cpumask_vals = {'thread_siblings_list': 1,
                             'core_siblings_list': 1,
                             'book_siblings_list': 1}

        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        self.assert_equal_dict({'cpu.cpu(s)': 3,
                                'cpu.socket(s)_per_book': 1,
                                'cpu.core(s)_per_socket': 1,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.cpu_socket(s)': 3,
                                'cpu.book(s)': 3,
                                'cpu.book(s)_per_cpu': 1,
                                'cpu.cpu_socket(s)': 3,
                                'cpu.topology_source': 's390 book_siblings_list'},
                               hw.get_cpu_info())

    @patch("subscription_manager.hwprobe.Hardware.has_s390x_sysinfo")
    @patch("subscription_manager.hwprobe.Hardware.read_s390x_sysinfo")
    @patch("os.listdir")
    def test_cpu_info_s390_sysinfo(self, mock_list_dir,
                                   mock_read_sysinfo, mock_has_sysinfo):
        #reload(hwprobe)

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 20)]
        mock_has_sysinfo.return_value = True
        mock_read_sysinfo.return_value = ["CPU Topology SW:      0 0 0 4 6 4"]

        hw = hwprobe.Hardware()
        hw.arch = "s390x"

        def count_cpumask(cpu, field):
            return self.cpumask_vals[field]

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
        self.cpumask_vals = {'thread_siblings_list': 1,
                             'core_siblings_list': 1,
                             'book_siblings_list': 1}

        # for this case, we prefer the sysinfo numbers
        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        self.assert_equal_dict({'cpu.cpu(s)': 20,
                                'cpu.socket(s)_per_book': 6,
                                'cpu.core(s)_per_socket': 4,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.book(s)': 4,
                                'cpu.cpu_socket(s)': 24,
                                'cpu.topology_source':
                                    's390x sysinfo'},
                               hw.get_cpu_info())

    @patch('subscription_manager.hwprobe.Hardware.count_cpumask_entries')
    @patch("os.listdir")
    def test_cpu_info(self, mock_list_dir, mock_count):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        def count_cpumask(cpu, field):
            return self.cpumask_vals[field]

        self.cpumask_vals = {'thread_siblings_list': 1,
                             'core_siblings_list': 2,
                             'book_siblings_list': None}

        mock_list_dir.return_value = ["cpu0", "cpu1"]
        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        #print hw.get_cpu_info()
        self.assert_equal_dict({'cpu.cpu(s)': 2,
                                'cpu.core(s)_per_socket': 2,
                                'cpu.cpu_socket(s)': 1,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.topology_source':
                                    'kernel /sys cpu sibling lists'},
                               hw.get_cpu_info())

    @patch("os.listdir")
    def test_cpu_info_no_topo(self, mock_list_dir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        def count_cpumask(cpu, field):
            return self.cpumask_vals[field]

        self.cpumask_vals = {'thread_siblings_list': None,
                             'core_siblings_list': None,
                             'book_siblings_list': None}

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 16)]
        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)

        self.assert_equal_dict({'cpu.cpu(s)': 16,
                                'cpu.core(s)_per_socket': 1,
                                'cpu.cpu_socket(s)': 16,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.topology_source': "fallback one socket"},
                               hw.get_cpu_info())

    @patch("subscription_manager.hwprobe.Hardware.read_physical_id")
    @patch("os.listdir")
    def test_cpu_info_no_topo_ppc64_physical_id(self, mock_list_dir,
                                                mock_read_physical):
        reload(hwprobe)
        hw = hwprobe.Hardware()
        hw.arch = "ppc64"

        def get_physical(cpu_file):
            # pretend we have two physical package ids
            return int(cpu_file[-1]) % 2

        def count_cpumask(cpu, field):
            return self.cpumask_vals[field]

        self.cpumask_vals = {'thread_siblings_list': None,
                             'core_siblings_list': None,
                             'book_siblings_list': None}

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 8)]
        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        hw.read_physical_id = Mock(side_effect=get_physical)

        self.assert_equal_dict({'cpu.cpu(s)': 8,
                                'cpu.core(s)_per_socket': 4,
                                'cpu.cpu_socket(s)': 2,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.topology_source': 'ppc64 physical_package_id'},
                               hw.get_cpu_info())

    @patch("os.listdir")
    def test_cpu_info_lots_cpu(self, mock_list_dir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        mock_list_dir.return_value = ["cpu%s" % i for i in range(0, 2000)]

        def count_cpumask(cpu, field):
            vals = {'thread_siblings_list': 1,
                    #'core_siblings_list': 2,
                    'core_siblings_list': 2000,
                    'book_siblings_list': None}
            return vals[field]

        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        self.assert_equal_dict({'cpu.cpu(s)': 2000,
                               'cpu.core(s)_per_socket': 2000,
                               'cpu.thread(s)_per_core': 1,
                               'cpu.cpu_socket(s)': 1,
                               'cpu.topology_source':
                                    'kernel /sys cpu sibling lists'},
                               hw.get_cpu_info(),
)

    @patch("os.listdir")
    def test_cpu_info_other_files(self, mock_list_dir):
        reload(hwprobe)
        hw = hwprobe.Hardware()

        mock_list_dir.return_value = ["cpu0", "cpu1",  # normal cpu ids (valid)
                                      "cpu123123",     # big cpu   (valid)
                                      "cpu_",          # not valid
                                      "cpufreq",       # this exists but is not a cpu
                                      "cpuidle",       # also exists
                                      "cpu0foo",       # only cpuN are valid
                                      "cpu11111111 ",  # trailing space, not valie
                                      "cpu00"]          # odd name, but valid I guess

        def count_cpumask(cpu, field):
            vals = {'thread_siblings_list': 1,
                    #'core_siblings_list': 2,
                    'core_siblings_list': 4,
                    'book_siblings_list': None}
            return vals[field]

        hw.count_cpumask_entries = Mock(side_effect=count_cpumask)
        self.assert_equal_dict({'cpu.cpu(s)': 4,
                                'cpu.core(s)_per_socket': 4,
                                'cpu.thread(s)_per_core': 1,
                                'cpu.cpu_socket(s)': 1,
                                'cpu.topology_source':
                                    'kernel /sys cpu sibling lists'},
                               hw.get_cpu_info())
