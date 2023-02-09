import json
import pathlib
import unittest
from unittest.mock import patch

import rhsmlib.facts.network


def load_data_file(name: str) -> dict:
    this = pathlib.Path(__file__).absolute()
    file = this.parent / "network_data" / name
    if not file.is_file():
        raise FileNotFoundError(f"File {file!s} does not exist.")
    with file.open("r") as handle:
        data = json.load(handle)
    return data


DATA = {
    "laptop.json": load_data_file("laptop.json"),
    "vm_no_connection.json": load_data_file("vm_no_connection.json"),
    "vm_no_connection_ipv4.json": load_data_file("vm_no_connection_ipv4.json"),
    "vm_no_connection_ipv6.json": load_data_file("vm_no_connection_ipv6.json"),
    "vm_bond.json": load_data_file("vm_bond.json"),
    "vm_team.json": load_data_file("vm_team.json"),
    "server.json": load_data_file("server.json"),
    "server_bond.json": load_data_file("server_bond.json"),
}
"""Real-life `ip --json a` captures.

- laptop.json: Workstation.
    Loopback, enabled ethernet (loc v4, link+global v6), disabled ethernet, disabled Wi-Fi, libvirt (v4, v6).
- vm_no_connection.json: Virtual machine.
    Loopback.
- vm_no_connection_ipv4.json: Virtual machine.
    Loopback with IPv6 disabled.
- vm_no_connection_ipv6.json: Virtual machine.
    Loopback with IPv4 disabled.
- vm_bond.json: Virtual machine.
    Loopback, two ethernet connections joined into one bond.
- vm_team.json: Virtual machine.
    Loopback, ethernet connection, two ethernet connections joined into one team.
- server.json: Server.
    8 enabled interfaces, 3 disabled interfaces. Total of 59 addresses (local v4, local & link v6).
- server_bond.json: Server.
    10 enabled interfaces, 4 bonded interfaces, 2 disabled interfaces. Total of 28 addresses.
"""


class TestNetworkCollector(unittest.TestCase):
    def setUp(self) -> None:
        query_patch = patch("rhsmlib.facts.network.NetworkCollector._query_ip_command")
        self.query = query_patch.start()
        self.addCleanup(query_patch.stop)

        # This tells pytest not to cut off the differing JSON output on error
        self.maxDiff = None

    def test_get_network(self):
        """Test the function on laptop data."""
        hostname_patch = patch("socket.gethostname")
        fqdn_patch = patch("socket.getfqdn")

        expected = {
            "network.fqdn": "fake.example.com",
            "network.hostname": "fake.example.com",
            "network.ipv4_address": "10.0.0.56, 192.168.122.1",
            "network.ipv6_address": "2620:52:0:0:0:1:2:3, fe80::0:1:2:3, 2038:dead:beef::1",
        }

        self.query.return_value = DATA["laptop.json"]
        hostname_patch.start().return_value = expected["network.hostname"]
        fqdn_patch.start().return_value = expected["network.fqdn"]

        collector = rhsmlib.facts.network.NetworkCollector()

        self.assertEqual(collector.get_network(), expected)

    def test_get_network__no_network(self):
        """Test the function when the system does not have the network."""
        hostname_patch = patch("socket.gethostname")
        fqdn_patch = patch("socket.getfqdn")

        expected = {
            "network.fqdn": "fake.example.com",
            "network.hostname": "fake.example.com",
            "network.ipv4_address": "",
            "network.ipv6_address": "",
        }

        self.query.return_value = {}
        hostname_patch.start().return_value = expected["network.hostname"]
        fqdn_patch.start().return_value = expected["network.fqdn"]

        collector = rhsmlib.facts.network.NetworkCollector()

        self.assertEqual(collector.get_network(), expected)

    def test_get_interfaces__nothing(self):
        """System with no network."""
        # FIXME This may not be even possible, loopback should exist every time.
        expected = {}
        self.query.return_value = {}
        collector = rhsmlib.facts.network.NetworkCollector()
        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__omit_mac(self):
        """Ensure that selected interface do not contain MAC address."""
        # TODO Find a system with sit interface as an example (BZ#838123).
        self.query.return_value = DATA["laptop.json"]

        self.query.return_value = [
            {
                "ifname": "lo",
                "flags": ["LOOPBACK", "UP", "LOWER_UP"],
                "address": "00:00:00:00:00:00",
                "addr_info": [
                    {
                        "family": "inet",
                        "local": "127.0.0.1",
                        "prefixlen": 8,
                        "scope": "host",
                        "label": "lo",
                        "valid_life_time": 4294967295,
                        "preferred_life_time": 4294967295,
                    },
                ],
            },
            {
                "ifname": "renamed-lo",
                "flags": ["LOOPBACK", "UP", "LOWER_UP"],
                "address": "00:00:00:00:00:00",
                "addr_info": [
                    {
                        "family": "inet",
                        "local": "127.0.0.1",
                        "prefixlen": 8,
                        "scope": "host",
                        "label": "lo",
                        "valid_life_time": 4294967295,
                        "preferred_life_time": 4294967295,
                    },
                ],
            },
        ]

        collector = rhsmlib.facts.network.NetworkCollector()
        result = collector.get_interfaces()

        self.assertNotIn("net.interface.lo.mac_address", result.keys())
        self.assertNotIn("net.interface.renamed-lo.mac_address", result.keys())
        self.assertNotIn("net.interface.sit0.mac_address", result.keys())

    def test_get_interfaces__more_v4s(self):
        """An interface can have more than one IPv4 address."""
        expected = {
            "net.interface.fake0.mac_address": "00:11:22:33:44:55",
            "net.interface.fake0.ipv4_address": "10.0.1.10",
            "net.interface.fake0.ipv4_address_list": "10.0.1.10, 10.0.2.247",
            "net.interface.fake0.ipv4_broadcast": "10.0.1.255",
            "net.interface.fake0.ipv4_broadcast_list": "10.0.1.255, 10.0.2.255",
            "net.interface.fake0.ipv4_netmask": "24",
            "net.interface.fake0.ipv4_netmask_list": "24, 28",
        }

        self.query.return_value = [
            {
                "ifname": "fake0",
                "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"],
                "address": "00:11:22:33:44:55",
                "addr_info": [
                    {
                        "family": "inet",
                        "local": "10.0.1.10",
                        "prefixlen": 24,
                        "scope": "global",
                        "broadcast": "10.0.1.255",
                    },
                    {
                        "family": "inet",
                        "local": "10.0.2.247",
                        "prefixlen": 28,
                        "scope": "global",
                        "broadcast": "10.0.2.255",
                    },
                ],
            }
        ]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__more_v6s(self):
        """An interface can have more than one IPv6 address."""
        expected = {
            "net.interface.fake0.mac_address": "00:11:22:33:44:55",
            "net.interface.fake0.ipv6_address.global": "2620:52:0:0:0:1:2:3",
            "net.interface.fake0.ipv6_address.global_list": "2620:52:0:0:0:1:2:3, 2620:52:0:0:0:1:2:4",
            "net.interface.fake0.ipv6_netmask.global": "64",
            "net.interface.fake0.ipv6_netmask.global_list": "64, 64",
        }

        self.query.return_value = [
            {
                "ifname": "fake0",
                "address": "00:11:22:33:44:55",
                "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"],
                "addr_info": [
                    {
                        "family": "inet6",
                        "local": "2620:52:0:0:0:1:2:3",
                        "prefixlen": 64,
                        "scope": "global",
                    },
                    {
                        "family": "inet6",
                        "local": "2620:52:0:0:0:1:2:4",
                        "prefixlen": 64,
                        "scope": "global",
                    },
                ],
            }
        ]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()
        print(result)

        self.assertEqual(expected, result)

    def test_get_interfaces__no_connection(self):
        """The system may not have a connection."""
        expected = {
            "net.interface.lo.ipv4_address": "127.0.0.1",
            "net.interface.lo.ipv4_address_list": "127.0.0.1",
            "net.interface.lo.ipv4_broadcast": "Unknown",
            "net.interface.lo.ipv4_broadcast_list": "Unknown",
            "net.interface.lo.ipv4_netmask": "8",
            "net.interface.lo.ipv4_netmask_list": "8",
            "net.interface.lo.ipv6_address.host": "::1",
            "net.interface.lo.ipv6_address.host_list": "::1",
            "net.interface.lo.ipv6_netmask.host": "128",
            "net.interface.lo.ipv6_netmask.host_list": "128",
        }

        self.query.return_value = DATA["vm_no_connection.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__no_connection__ipv4_only(self):
        """The system may not have a connection with IPv6 disabled."""
        expected = {
            "net.interface.lo.ipv4_address": "127.0.0.1",
            "net.interface.lo.ipv4_address_list": "127.0.0.1",
            "net.interface.lo.ipv4_broadcast": "Unknown",
            "net.interface.lo.ipv4_broadcast_list": "Unknown",
            "net.interface.lo.ipv4_netmask": "8",
            "net.interface.lo.ipv4_netmask_list": "8",
        }

        self.query.return_value = DATA["vm_no_connection_ipv4.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__no_connection__ipv6_only(self):
        """The system may not have a connection with IPv4 disabled."""
        expected = {
            "net.interface.lo.ipv6_address.host": "::1",
            "net.interface.lo.ipv6_address.host_list": "::1",
            "net.interface.lo.ipv6_netmask.host": "128",
            "net.interface.lo.ipv6_netmask.host_list": "128",
        }

        self.query.return_value = DATA["vm_no_connection_ipv6.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__emoji(self):
        """An interface can have more than one IPv4 address."""
        self.query.return_value = [
            {
                "ifname": "🍉",
                "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"],
                "address": "00:11:22:33:44:55",
                "addr_info": [
                    {
                        "family": "inet",
                        "local": "10.0.1.10",
                        "prefixlen": 24,
                        "scope": "global",
                        "broadcast": "10.0.1.255",
                    },
                ],
            }
        ]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertIn("net.interface.\N{WATERMELON}.ipv4_address", result)

    def test_get_interfaces__laptop(self):
        """Test the function on laptop.json data."""
        expected = {
            "net.interface.lo.ipv4_address": "127.0.0.1",
            "net.interface.lo.ipv4_address_list": "127.0.0.1",
            "net.interface.lo.ipv4_broadcast": "Unknown",
            "net.interface.lo.ipv4_broadcast_list": "Unknown",
            "net.interface.lo.ipv4_netmask": "8",
            "net.interface.lo.ipv4_netmask_list": "8",
            "net.interface.lo.ipv6_address.host": "::1",
            "net.interface.lo.ipv6_address.host_list": "::1",
            "net.interface.lo.ipv6_netmask.host": "128",
            "net.interface.lo.ipv6_netmask.host_list": "128",
            "net.interface.enp0s20f0u2u1.mac_address": "a4:ae:12:01:02:03",
            "net.interface.enp0s20f0u2u1.ipv4_address": "10.0.0.56",
            "net.interface.enp0s20f0u2u1.ipv4_address_list": "10.0.0.56",
            "net.interface.enp0s20f0u2u1.ipv4_broadcast": "10.0.0.255",
            "net.interface.enp0s20f0u2u1.ipv4_broadcast_list": "10.0.0.255",
            "net.interface.enp0s20f0u2u1.ipv4_netmask": "24",
            "net.interface.enp0s20f0u2u1.ipv4_netmask_list": "24",
            "net.interface.enp0s20f0u2u1.ipv6_address.global": "2620:52:0:0:0:1:2:3",
            "net.interface.enp0s20f0u2u1.ipv6_address.global_list": "2620:52:0:0:0:1:2:3",
            "net.interface.enp0s20f0u2u1.ipv6_address.link": "fe80::0:1:2:3",
            "net.interface.enp0s20f0u2u1.ipv6_address.link_list": "fe80::0:1:2:3",
            "net.interface.enp0s20f0u2u1.ipv6_netmask.global": "64",
            "net.interface.enp0s20f0u2u1.ipv6_netmask.global_list": "64",
            "net.interface.enp0s20f0u2u1.ipv6_netmask.link": "64",
            "net.interface.enp0s20f0u2u1.ipv6_netmask.link_list": "64",
            "net.interface.enp0s31f6.mac_address": "38:f3:ab:01:02:03",
            "net.interface.wlp0s20f3.mac_address": "d6:73:ed:01:02:03",
            "net.interface.wlp0s20f3.permanent_mac_address": "28:d0:ea:01:02:03",
            "net.interface.virbr0.mac_address": "52:54:00:01:02:03",
            "net.interface.virbr0.ipv4_address": "192.168.122.1",
            "net.interface.virbr0.ipv4_address_list": "192.168.122.1",
            "net.interface.virbr0.ipv4_broadcast": "192.168.122.255",
            "net.interface.virbr0.ipv4_broadcast_list": "192.168.122.255",
            "net.interface.virbr0.ipv4_netmask": "24",
            "net.interface.virbr0.ipv4_netmask_list": "24",
            "net.interface.virbr0.ipv6_address.global": "2038:dead:beef::1",
            "net.interface.virbr0.ipv6_address.global_list": "2038:dead:beef::1",
            "net.interface.virbr0.ipv6_netmask.global": "96",
            "net.interface.virbr0.ipv6_netmask.global_list": "96",
        }

        self.query.return_value = DATA["laptop.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__vm_bond(self):
        """Test the function on vm_bond.json data."""
        expected = {
            "net.interface.lo.ipv4_address": "127.0.0.1",
            "net.interface.lo.ipv4_address_list": "127.0.0.1",
            "net.interface.lo.ipv4_broadcast": "Unknown",
            "net.interface.lo.ipv4_broadcast_list": "Unknown",
            "net.interface.lo.ipv4_netmask": "8",
            "net.interface.lo.ipv4_netmask_list": "8",
            "net.interface.lo.ipv6_address.host": "::1",
            "net.interface.lo.ipv6_address.host_list": "::1",
            "net.interface.lo.ipv6_netmask.host": "128",
            "net.interface.lo.ipv6_netmask.host_list": "128",
            "net.interface.enp1s0.permanent_mac_address": "52:54:00:00:00:01",
            "net.interface.enp1s0.mac_address": "72:4b:f3:aa:aa:aa",
            "net.interface.enp2s0.permanent_mac_address": "52:54:00:00:00:02",
            "net.interface.enp2s0.mac_address": "72:4b:f3:aa:aa:aa",
            "net.interface.bond0.mac_address": "72:4b:f3:aa:aa:aa",
            "net.interface.bond0.ipv4_address": "192.168.122.35",
            "net.interface.bond0.ipv4_address_list": "192.168.122.35",
            "net.interface.bond0.ipv4_broadcast": "192.168.122.255",
            "net.interface.bond0.ipv4_broadcast_list": "192.168.122.255",
            "net.interface.bond0.ipv4_netmask": "24",
            "net.interface.bond0.ipv4_netmask_list": "24",
            "net.interface.bond0.ipv6_address.global": "2038:dead:beef::1",
            "net.interface.bond0.ipv6_address.global_list": "2038:dead:beef::1",
            "net.interface.bond0.ipv6_address.link": "fe80::1",
            "net.interface.bond0.ipv6_address.link_list": "fe80::1",
            "net.interface.bond0.ipv6_netmask.global": "128",
            "net.interface.bond0.ipv6_netmask.global_list": "128",
            "net.interface.bond0.ipv6_netmask.link": "64",
            "net.interface.bond0.ipv6_netmask.link_list": "64",
        }

        self.query.return_value = DATA["vm_bond.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        self.assertEqual(expected, result)

    def test_get_interfaces__vm_team(self):
        """Test the function on vm_team.json data."""
        self.query.return_value = DATA["vm_team.json"]

        collector = rhsmlib.facts.network.NetworkCollector()

        result = collector.get_interfaces()

        # The second interface should contain permanent MAC address, see RHBZ#2077757
        self.assertEqual(result["net.interface.enp7s0.mac_address"], "52:54:00:00:00:01")
        self.assertEqual(result["net.interface.enp8s0.mac_address"], "52:54:00:00:00:01")
        self.assertEqual(result["net.interface.enp8s0.permanent_mac_address"], "52:54:00:00:00:02")
        self.assertEqual(result["net.interface.team0.mac_address"], "52:54:00:00:00:01")
