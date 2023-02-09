# Copyright (c) 2023 Red Hat, Inc.
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
import json
import logging
import socket
import subprocess
from typing import Callable, Dict, List, Literal, Union

from rhsmlib.facts import collector

log = logging.getLogger(__name__)


class NetworkCollector(collector.FactsCollector):
    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        collected_hw_info: Dict[str, Union[str, int, bool, None]] = None,
    ):
        super().__init__(arch=arch, prefix=prefix, testing=testing, collected_hw_info=None)

        self.hardware_methods: List[Callable] = [
            self.get_network,
            self.get_interfaces,
        ]

    def _query_ip_command(self) -> List[dict]:
        """Call system's 'ip' command and return its value as a dictionary."""
        output = subprocess.run(["ip", "--json", "address"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if output.stderr != b"":
            log.error(f"Could not query 'ip' for network facts: {output.stderr}")
            return []
        stdout: str = output.stdout.decode("utf-8")
        return json.loads(stdout)

    def _get_fqdn(self) -> str:
        """Obtain system's FQDN."""
        # We use this approach because '/etc/bin/hostname -f' cannot be read
        # under RHEL's SELinux policy (RHBZ 1447722).
        # We must also stay compatible with Puppet and Katello: they use
        # 'hostname -f' which prefers IPv4, but 'socket.getfqdn()' prefers
        # IPv6 (RHBZ 1401394).
        hostname: str = socket.gethostname()

        try:
            addrinfo: list[tuple] = socket.getaddrinfo(
                # host, port, family, type, proto, flags
                hostname,
                None,
                socket.AF_UNSPEC,
                socket.SOCK_DGRAM,
                0,
                socket.AI_CANONNAME,
            )

            # getaddrinfo() returns 1+ items. The first one contains the
            # canonical name, the rest of the items contain empty string.
            # Note: When hostname is equal to one of CNAME in DNS record, then
            # canonical name will be different from hostname.
            if len(addrinfo) > 0 and addrinfo[0][3] != "":
                return addrinfo[0][3]
        except socket.gaierror as exc:
            log.debug(f"Could not obtain hostname using getaddrinfo: {exc}")

        return hostname

    def _extract_address_list(self, family: Literal["inet", "inet6"], data: List[dict]) -> List[str]:
        """Extract IPv4 or IPv6 addresses from 'ip' output.

        The list excludes loopback and link-local addresses.
        """
        result: List[str] = []
        for interface in data:
            if "LOOPBACK" in interface["flags"]:
                continue
            result += [address["local"] for address in interface["addr_info"] if address["family"] == family]
        return result

    def get_network(self) -> dict:
        """Get general network facts.

        Hostname, FQDN and a list of IPv4/IPv6 addresses get collected here.

        Resulting facts have 'network.' prefix.
        """
        # These socket functions work even with no network available
        data = self._query_ip_command()

        result: Dict[str, str] = {
            "network.hostname": socket.gethostname(),
            "network.fqdn": self._get_fqdn(),
            "network.ipv4_address": ", ".join(self._extract_address_list("inet", data)),
            "network.ipv6_address": ", ".join(self._extract_address_list("inet6", data)),
        }
        return result

    def get_interfaces(self) -> dict:
        """Get detailed network interface facts.

        Interface names, IPv4/IPv6 addresses and masks get collected here.

        Resulting facts have 'net.' prefix.
        """
        data = self._query_ip_command()
        result: Dict[str, Union[str, int]] = {}

        for interface in data:
            prefix: str = f"net.interface.{interface['ifname']}"

            # MAC address
            skip_mac: bool = "LOOPBACK" in interface["flags"] or "NOARP" in interface["flags"]
            # Loopback has a MAC address of '00:00:00:00:00:00'.
            # Tunnels have their MAC randomized every time, see BZ#838123.
            if not skip_mac:
                result[f"{prefix}.mac_address"] = interface["address"]
                if "permaddr" in interface:
                    # Wireless interfaces have permanent address and temporary
                    # address they use to identify to unknown access points.
                    result[f"{prefix}.permanent_mac_address"] = interface["permaddr"]

            # IP address
            ipv4_addresses: List[str] = []
            ipv4_broadcasts: List[str] = []
            ipv4_netmasks: List[int] = []

            ipv6_global_addresses: List[str] = []
            ipv6_link_addresses: List[str] = []
            ipv6_host_addresses: List[str] = []
            ipv6_global_netmasks: List[int] = []
            ipv6_link_netmasks: List[int] = []
            ipv6_host_netmasks: List[int] = []

            for address in interface["addr_info"]:
                if address["family"] == "inet":
                    ipv4_addresses.append(address["local"])
                    # Localhost does not have a broadcast address
                    if "broadcast" in address:
                        ipv4_broadcasts.append(address["broadcast"])
                    else:
                        # FIXME Should localhost's broadcast be simply omitted?
                        ipv4_broadcasts.append("Unknown")
                    ipv4_netmasks.append(address["prefixlen"])

                elif address["family"] == "inet6":
                    if address["scope"] == "global":
                        ipv6_global_addresses.append(address["local"])
                        ipv6_global_netmasks.append(address["prefixlen"])
                    elif address["scope"] == "link":
                        ipv6_link_addresses.append(address["local"])
                        ipv6_link_netmasks.append(address["prefixlen"])
                    elif address["scope"] == "host":
                        ipv6_host_addresses.append(address["local"])
                        ipv6_host_netmasks.append(address["prefixlen"])

            def add_addresses(infix: str, items: list) -> None:
                """Fill in the 'result' dictionary.

                :param infix: Fact name.
                :param items: List of addresses or masks.
                :return: Nothing, the 'result' dictionary is updated in-place.
                """
                if not len(items):
                    return
                result[f"{prefix}.{infix}"] = str(items[0])
                result[f"{prefix}.{infix}_list"] = ", ".join([str(x) for x in items])

            add_addresses("ipv4_address", ipv4_addresses)
            add_addresses("ipv4_broadcast", ipv4_broadcasts)
            add_addresses("ipv4_netmask", ipv4_netmasks)

            add_addresses("ipv6_address.global", ipv6_global_addresses)
            add_addresses("ipv6_netmask.global", ipv6_global_netmasks)
            add_addresses("ipv6_address.link", ipv6_link_addresses)
            add_addresses("ipv6_netmask.link", ipv6_link_netmasks)
            add_addresses("ipv6_address.host", ipv6_host_addresses)
            add_addresses("ipv6_netmask.host", ipv6_host_netmasks)

        return result
