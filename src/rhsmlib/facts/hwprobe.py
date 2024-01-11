# Module to probe Hardware info from the system
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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
import json
import logging
import os
import platform
import re
import subprocess
import sys

import datetime
from rhsmlib.facts import cpuinfo
from rhsmlib.facts import collector

from typing import Callable, Dict, Optional, List, TextIO, Tuple, Union

log = logging.getLogger(__name__)


class ClassicCheck:
    def is_registered_with_classic(self) -> bool:
        try:
            sys.path.append("/usr/share/rhn")
            from up2date_client import up2dateAuth
        except ImportError:
            return False

        return up2dateAuth.getSystemId() is not None


# take a string like '1-4' and returns a list of
# ints like [1,2,3,4]
# 31-37 return [31,32,33,34,35,36,37]
def parse_range(range_str: str) -> List[int]:
    range_list: List[str] = range_str.split("-")
    start = int(range_list[0])
    end = int(range_list[-1])

    return list(range(start, end + 1))


# util to total up the values represented by a cpu siblings list
# ala /sys/devices/cpu/cpu0/topology/core_siblings_list
#
# which can be a comma separated list of ranges
#  1,2,3,4
#  1-2, 4-6, 8-10, 12-14
#
def gather_entries(entries_string: str) -> List[int]:
    entries: List[int] = []
    entry_parts: List[str] = entries_string.split(",")
    for entry_part in entry_parts:
        # return a list of enumerated items
        entry_range: List[int] = parse_range(entry_part)
        for entry in entry_range:
            entries.append(entry)
    return entries


# FIXME This class does not seem to be used anywhere
class GenericPlatformSpecificInfoProvider:
    """Default provider for platform without a specific platform info provider.
    ie, all platforms except those with DMI (ie, intel platforms)"""

    def __init__(self, hardware_info, dump_file=None):
        self.info = {}

    @staticmethod
    def log_warnings():
        pass


class HardwareCollector(collector.FactsCollector):
    LSCPU_CMD: str = "/usr/bin/lscpu"

    def __init__(
        self,
        arch: str = None,
        prefix: str = None,
        testing: bool = None,
        collected_hw_info: Dict[str, Union[str, int, bool, None]] = None,
    ):
        super(HardwareCollector, self).__init__(
            arch=arch, prefix=prefix, testing=testing, collected_hw_info=None
        )

        self.hardware_methods: List[Callable] = [
            self.get_uname_info,
            self.get_release_info,
            self.get_mem_info,
            self.get_last_boot,
            self.get_proc_cpuinfo,
            self.get_proc_stat,
            self.get_cpu_info,
            self.get_ls_cpu_info,
        ]

    def get_uname_info(self) -> Dict[str, str]:
        uname_data: os.uname_result = os.uname()
        uname_keys: Tuple[str, ...] = (
            "uname.sysname",
            "uname.nodename",
            "uname.release",
            "uname.version",
            "uname.machine",
        )
        uname_info: Dict[str, str] = dict(list(zip(uname_keys, uname_data)))
        return uname_info

    def get_release_info(self) -> Dict[str, str]:
        distro_info: tuple = self.get_distribution()
        release_info: Dict[str, str] = {
            "distribution.name": distro_info[0],
            "distribution.version": distro_info[1],
            "distribution.id": distro_info[2],
            "distribution.version.modifier": distro_info[3],
        }
        return release_info

    def _open_release(self, filename: str) -> TextIO:
        return open(filename, "r")

    # this version os very RHEL/Fedora specific...
    def get_distribution(self) -> Tuple[str, str, str, str, str, List[str]]:
        version: str = "Unknown"
        distname: str = "Unknown"
        dist_id: str = "Unknown"
        id: str = "Unknown"
        id_like: List[str] = [""]
        version_modifier: str = ""

        if os.path.exists("/etc/os-release"):
            f: TextIO = open("/etc/os-release", "r")
            os_release: List[str] = f.readlines()
            f.close()
            data: Dict[str, str] = {
                "PRETTY_NAME": "Unknown",
                "NAME": distname,
                "ID": id,
                "ID_LIKE": "",
                "VERSION": dist_id,
                "VERSION_ID": version,
                "CPE_NAME": "Unknown",
            }
            for line in os_release:
                split: List[str] = [piece.strip('"\n ') for piece in line.split("=")]
                if len(split) != 2:
                    continue
                data[split[0]] = split[1]

            version = data["VERSION_ID"]
            distname = data["NAME"]
            dist_id = data["VERSION"]
            dist_id_search: Optional[re.Match] = re.search(r"\((.*?)\)", dist_id)
            if dist_id_search:
                dist_id: str = dist_id_search.group(1)
            id_like = data["ID_LIKE"].split()
            id = data["ID"]
            # Split on ':' that is not preceded by '\'
            vers_mod_data: List[str] = re.split(r"(?<!\\):", data["CPE_NAME"])
            if len(vers_mod_data) >= 6:
                version_modifier = vers_mod_data[5].lower().replace("\\:", ":")
        elif os.path.exists("/etc/redhat-release"):
            # from platform.py from python2.
            _lsb_release_version: re.Pattern = re.compile(
                r"(.+) release ([\d.]+)\s*(?!\()(\S*)\s*[^(]*(?:\((.+)\))?"
            )
            f: TextIO = self._open_release("/etc/redhat-release")
            firstline: str = f.readline()
            f.close()

            m: re.Match = _lsb_release_version.match(firstline)

            if m is not None:
                (distname, version, tmp_modifier, dist_id) = tuple(m.groups())
                if tmp_modifier:
                    version_modifier = tmp_modifier.lower()

        elif hasattr(platform, "linux_distribution"):
            (distname, version, dist_id) = platform.linux_distribution()
            version_modifier = "Unknown"

        # FIXME Return collections.namedtuple instead?
        return distname, version, dist_id, version_modifier, id, id_like

    def get_mem_info(self) -> Dict[str, str]:
        meminfo: Dict[str, str] = {}

        # most of this mem info changes constantly, which makes deciding
        # when to update facts painful, so lets try to just collect the
        # useful bits

        useful: List[str] = ["MemTotal", "SwapTotal"]
        try:
            parser: re.Pattern = re.compile(r"^(?P<key>\S*):\s*(?P<value>\d*)\s*kB")
            memdata: TextIO = open("/proc/meminfo")
            for info in memdata:
                match: Optional[re.Match] = parser.match(info)
                if not match:
                    continue
                key, value = match.groups(["key", "value"])
                if key in useful:
                    nkey: str = ".".join(["memory", key.lower()])
                    meminfo[nkey] = "%s" % int(value)
        except Exception as e:
            log.warning("Error reading system memory information: %s", e)
        return meminfo

    def get_last_boot(self) -> Dict[str, str]:
        last_boot: str = "unknown"

        # Use a date for uptime instead of the actual uptime since that
        # would force a refresh for every run. This was inspired by the
        # spacewalk client at https://github.com/spacewalkproject/
        # spacewalk/blob/master/client/rhel/rhn-client-tools/src/bin/rhn_check.py
        try:
            uptime = float(open("/proc/uptime", "r").read().split()[0])
            uptime_delta = datetime.timedelta(seconds=uptime)
            now = datetime.datetime.now(datetime.timezone.utc)
            last_boot_date: datetime.datetime = now - uptime_delta
            last_boot: str = last_boot_date.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
        except Exception as e:
            log.warning("Error reading uptime information %s", e)
        return {"last_boot": last_boot}

    def count_cpumask_entries(self, cpu: str, field: str) -> Optional[int]:
        try:
            f: TextIO = open("%s/topology/%s" % (cpu, field), "r")
        except IOError:
            return None

        # ia64 entries seem to be null padded, or perhaps
        # that's a collection error
        # FIXME
        entries: str = f.read().rstrip("\n\x00")
        f.close()
        # these fields can exist, but be empty. For example,
        # thread_siblings_list from s390x-rhel64-zvm-2cpu-has-topo
        # test data

        if len(entries):
            cpumask_entries: List[int] = gather_entries(entries)
            return len(cpumask_entries)
        # that field was empty
        return None

    def is_a64fx(self) -> bool:
        if self.arch != "aarch64":
            return False
        try:
            # MIDR_EL1 register shows the identifer of ARM64 CPU.
            # MIDR_EL1 of A64FX is as follows:
            # FX700:  0x00000000461f0010
            # FX1000: 0x00000000460f0010
            f: TextIO = open("/sys/devices/system/cpu/cpu0/regs/identification/midr_el1", "r")
        except IOError:
            return False

        midr: str = f.read().rstrip("\n")
        f.close()
        if midr == "0x00000000461f0010" or midr == "0x00000000460f0010":
            return True

        return False

    # replace/add with getting CPU Totals for s390x
    # FIXME cpu_count is not used
    def _parse_s390x_sysinfo_topology(self, cpu_count: int, sysinfo: List[str]) -> Optional[Dict[str, int]]:
        # to quote lscpu.c:
        # CPU Topology SW:      0 0 0 4 6 4
        # /* s390 detects its cpu topology via /proc/sysinfo, if present.
        # * Using simply the cpu topology masks in sysfs will not give
        # * usable results since everything is virtualized. E.g.
        # * virtual core 0 may have only 1 cpu, but virtual core 2 may
        # * five cpus.
        # * If the cpu topology is not exported (e.g. 2nd level guest)
        # * fall back to old calculation scheme.
        # */
        for line in sysinfo:
            if line.startswith("CPU Topology SW:"):
                parts: List[str] = line.split(":", 1)
                s390_topo_str: str = parts[1]
                topo_parts: List[str] = s390_topo_str.split()

                # indexes 3/4/5 being books/sockets_per_book,
                # and cores_per_socket based on lscpu.c
                book_count = int(topo_parts[3])
                sockets_per_book = int(topo_parts[4])
                cores_per_socket = int(topo_parts[5])

                socket_count: int = book_count * sockets_per_book
                cores_count: int = socket_count * cores_per_socket

                return {
                    "socket_count": socket_count,
                    "cores_count": cores_count,
                    "book_count": book_count,
                    "sockets_per_book": sockets_per_book,
                    "cores_per_socket": cores_per_socket,
                }
        log.debug("Looking for 'CPU Topology SW' in sysinfo, but it was not found")
        return None

    def has_s390x_sysinfo(self, proc_sysinfo: str) -> bool:
        return os.access(proc_sysinfo, os.R_OK)

    # FIXME cpu_count is not used
    def read_s390x_sysinfo(self, cpu_count, proc_sysinfo: str) -> List[str]:
        lines: List[str] = []
        try:
            f: TextIO = open(proc_sysinfo, "r")
        except IOError:
            return lines

        lines = f.readlines()
        f.close()
        return lines

    def read_physical_id(self, cpu_file: str) -> Optional[str]:
        try:
            f: TextIO = open("%s/physical_id" % cpu_file, "r")
        except IOError:
            return None

        buf: str = f.read().strip()
        f.close()
        return buf

    def _ppc64_fallback(self, cpu_files: List[str]) -> Optional[int]:
        # ppc64, particular POWER5/POWER6 machines, show almost
        # no cpu information on rhel5. There is a "physical_id"
        # associated with each cpu that seems to map to a
        # cpu, in a socket
        log.debug("trying ppc64 specific cpu topology detection")
        # try to find cpuN/physical_id
        physical_ids = set()
        for cpu_file in cpu_files:
            physical_id: Optional[str] = self.read_physical_id(cpu_file)
            # offline cpu's show physical id of -1. Normally
            # we count all present cpu's even if offline, but
            # in this case, we can't get any cpu info from the
            # cpu since it is offline, so don't count it
            if physical_id != "-1":
                physical_ids.add(physical_id)

        if physical_ids:
            # For rhel6 or newer, we have more cpu topology info
            # exposed by the kernel which will override this
            socket_count: int = len(physical_ids)
            # add marker here so we know we fail back to this
            log.debug("Using /sys/devices/system/cpu/cpu*/physical_id for cpu info on ppc64")
            return socket_count

        return None

    def check_for_cpu_topo(self, cpu_topo_dir: str) -> bool:
        return os.access(cpu_topo_dir, os.R_OK)

    def get_proc_cpuinfo(self) -> Dict[str, str]:
        proc_cpuinfo: Dict[str, str] = {}
        fact_namespace: str = "proc_cpuinfo"

        proc_cpuinfo_source = cpuinfo.SystemCpuInfoFactory.from_uname_machine(self.arch, prefix=self.prefix)

        for key, value in list(proc_cpuinfo_source.cpu_info.common.items()):
            proc_cpuinfo["%s.common.%s" % (fact_namespace, key)] = value

        # NOTE: cpu_info.other is a potentially ordered non-uniq list, so may
        # not make sense for shoving into a list.
        for key, value in proc_cpuinfo_source.cpu_info.other:
            proc_cpuinfo["%s.system.%s" % (fact_namespace, key)] = value

        # we could enumerate each processor here as proc_cpuinfo.cpu.3.key =
        # value, but that is a lot of fact table entries
        return proc_cpuinfo

    def get_proc_stat(self) -> Dict[str, str]:
        proc_stat: Dict[str, str] = {}
        fact_namespace: str = "proc_stat"
        proc_stat_path: str = "/proc/stat"

        btime_re: str = r"btime\W*([0-9]+)\W*$"
        try:
            with open(proc_stat_path, "r") as proc_stat_file:
                for line in proc_stat_file.readlines():
                    match: re.Match = re.match(btime_re, line.strip())
                    if match:
                        proc_stat["%s.btime" % (fact_namespace)] = match.group(1)
                        break  # We presently only care about the btime fact
        except Exception as e:
            # This fact is not required, only log failure to gather it at the debug level
            log.debug("Could not gather proc_stat facts: %s", e)
        return proc_stat

    def get_cpu_info(self) -> Dict[str, Union[str, int]]:
        cpu_info: Dict[str, Union[str, int]] = {}
        # we also have cpufreq, etc. in this dir, so match just the numbers
        cpu_re: str = r"cpu([0-9]+$)"

        cpu_files: List[str] = []
        sys_cpu_path: str = self.prefix + "/sys/devices/system/cpu/"
        for cpu in os.listdir(sys_cpu_path):
            if re.match(cpu_re, cpu):
                cpu_topo_dir: str = os.path.join(sys_cpu_path, cpu, "topology")

                # see rhbz#1070908
                # ppc64 machines running on LPARs will add
                # a sys cpu entry for every cpu thread on the
                # physical machine, regardless of how many are
                # allocated to the LPAR. This throws off the cpu
                # thread count, which throws off the cpu socket count.
                # The entries for the unallocated or offline cpus
                # do not have topology info however.
                # So, skip sys cpu entries without topology info.
                #
                # NOTE: this assumes RHEL6+, prior to rhel5, on
                # some arches like ppc and s390, there is no topology
                # info ever, so this will break.
                if self.check_for_cpu_topo(cpu_topo_dir):
                    cpu_files.append("%s/%s" % (sys_cpu_path, cpu))

        # for systems with no cpus
        if not cpu_files:
            return cpu_info

        cpu_count: int = len(cpu_files)

        # see if we have a /proc/sysinfo ala s390, if so
        # prefer that info
        proc_sysinfo: str = self.prefix + "/proc/sysinfo"
        has_sysinfo: bool = self.has_s390x_sysinfo(proc_sysinfo)

        # s390x can have cpu 'books'
        books: bool = False

        socket_count: int
        cores_per_socket: int
        cores_per_cpu: int

        # assume each socket has the same number of cores, and
        # each core has the same number of threads.
        #
        # This is not actually true sometimes... *cough*s390x*cough*
        # but lscpu makes the same assumption

        threads_per_core: int = self.count_cpumask_entries(cpu_files[0], "thread_siblings_list")
        if self.is_a64fx():
            # core_siblings_list of A64FX shows the cpu mask which is in a same CMG,
            # not the socket. A64FX has always 4 CMGs on the socket.
            cores_per_cpu = self.count_cpumask_entries(cpu_files[0], "core_siblings_list") * 4
        else:
            cores_per_cpu = self.count_cpumask_entries(cpu_files[0], "core_siblings_list")

        # if we find valid values in cpu/cpuN/topology/*siblings_list
        # sometimes it's not there, particularly on rhel5
        if threads_per_core and cores_per_cpu:
            cores_per_socket = cores_per_cpu // threads_per_core
            cpu_info["cpu.topology_source"] = "kernel /sys cpu sibling lists"

            # rhel6 s390x can have /sys cpu topo, but we can't make assumption
            # about it being evenly distributed, so if we also have topo info
            # in sysinfo, prefer that
            if self.arch == "s390x" and has_sysinfo:
                # for s390x on lpar, try to see if /proc/sysinfo has any
                # topo info
                log.debug("/proc/sysinfo found, attempting to gather cpu topology info")
                sysinfo_lines: List[str] = self.read_s390x_sysinfo(cpu_count, proc_sysinfo)
                if sysinfo_lines:
                    sysinfo = self._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)

                    # verify the sysinfo has system level virt info
                    if sysinfo:
                        cpu_info["cpu.topology_source"] = "s390x sysinfo"
                        socket_count = sysinfo["socket_count"]
                        book_count = sysinfo["book_count"]
                        sockets_per_book = sysinfo["sockets_per_book"]
                        cores_per_socket = sysinfo["cores_per_socket"]
                        threads_per_core = 1

                        # we can have a mismatch between /sys and /sysinfo. We
                        # defer to sysinfo in this case even for cpu_count
                        # cpu_count = sysinfo['cores_count'] * threads_per_core
                        books = True

        else:
            # we have found no valid socket information, I only know
            # the number of cpu's, but no threads, no cores, no sockets
            log.debug("No cpu socket information found")

            # how do we get here?
            #   no cpu topology info, ala s390x on rhel5,
            #   no sysinfo topology info, ala s390x with zvm on rhel5
            # we have no great topo info here,
            # assume each cpu thread = 1 core = 1 socket
            threads_per_core = 1
            cores_per_cpu = 1
            cores_per_socket = 1
            socket_count = None

            # lets try some arch/platform specific approaches
            if self.arch == "ppc64":
                socket_count = self._ppc64_fallback(cpu_files)

                if socket_count:
                    log.debug("Using ppc64 cpu physical id for cpu topology info")
                    cpu_info["cpu.topology_source"] = "ppc64 physical_package_id"

            else:
                # all of our usual methods failed us...
                log.debug("No cpu socket info found for real or virtual hardware")
                # so we can track if we get this far
                cpu_info["cpu.topology_source"] = "fallback one socket"
                socket_count = cpu_count

            # for some odd cases where there are offline ppc64 cpu's,
            # this can end up not being a whole number...
            cores_per_socket = cpu_count // socket_count

        if cores_per_socket and threads_per_core:
            # for s390x with sysinfo topo, we use the sysinfo numbers except
            # for cpu_count, which takes offline cpus into account. This is
            # mostly just to match lscpu behaviour here
            if cpu_info["cpu.topology_source"] != "s390x sysinfo":
                socket_count = cpu_count // cores_per_socket // threads_per_core

        # s390 etc
        # for s390, socket calculations are per book, and we can have multiple
        # books, so multiply socket count by book count
        # see if we are on a s390 with book info
        # all s390 platforms show book siblings, even the ones that also
        # show sysinfo (lpar)... Except on rhel5, where there is no
        # cpu topology info with lpar
        #
        # if we got book info from sysinfo, prefer it
        book_siblings_per_cpu: int = None
        if not books:
            book_siblings_per_cpu = self.count_cpumask_entries(cpu_files[0], "book_siblings_list")
            if book_siblings_per_cpu:
                book_count = cpu_count // book_siblings_per_cpu
                sockets_per_book = book_count // socket_count
                cpu_info["cpu.topology_source"] = "s390 book_siblings_list"
                books = True

        # we should always know this...
        cpu_info["cpu.cpu(s)"] = cpu_count

        # these may be unknown...
        if socket_count:
            cpu_info["cpu.cpu_socket(s)"] = socket_count
        if cores_per_socket:
            cpu_info["cpu.core(s)_per_socket"] = cores_per_socket
        if threads_per_core:
            cpu_info["cpu.thread(s)_per_core"] = threads_per_core

        if book_siblings_per_cpu:
            cpu_info["cpu.book(s)_per_cpu"] = book_siblings_per_cpu

        if books:
            cpu_info["cpu.socket(s)_per_book"] = sockets_per_book
            cpu_info["cpu.book(s)"] = book_count

        return cpu_info

    def get_ls_cpu_info(self) -> Dict:
        # if we have `lscpu`, let's use it for facts as well, under
        # the `lscpu` name space
        if not os.access(self.LSCPU_CMD, os.R_OK):
            return {}

        # copy of parent process environment
        lscpu_env: Dict[str, str] = dict(os.environ)

        # # LANGUAGE trumps LC_ALL, LC_CTYPE, LANG. See rhbz#1225435, rhbz#1450210
        lscpu_env.update({"LANGUAGE": "en_US.UTF-8"})

        if self._check_lscpu_json(lscpu_env):
            return self._parse_lscpu_json_output(lscpu_env)

        return self._parse_lscpu_human_readable_output(lscpu_env)

    def _check_lscpu_json(self, lscpu_env: Dict[str, str]) -> bool:
        lscpu_cmd: List[str] = [self.LSCPU_CMD, "--help"]

        try:
            output: bytes = subprocess.check_output(lscpu_cmd, env=lscpu_env)
        except subprocess.CalledProcessError as e:
            log.warning("Failed to run 'lscpu --help': %s", e)
            return False

        return b"--json" in output

    def _parse_lscpu_human_readable_output(self, lscpu_env: Dict[str, str]) -> Dict[str, str]:
        lscpu_info: Dict[str, str] = {}
        lscpu_cmd: List[str] = [self.LSCPU_CMD]

        if self.testing:
            lscpu_cmd += ["-s", self.prefix]

        # For display/message only
        lscpu_cmd_string: str = " ".join(lscpu_cmd)

        try:
            lscpu_out_raw: bytes = subprocess.check_output(lscpu_cmd, env=lscpu_env)
            lscpu_out: str = lscpu_out_raw.decode("utf-8")
        except subprocess.CalledProcessError as e:
            log.exception(e)
            log.warning("Error with lscpu (%s) subprocess: %s", lscpu_cmd_string, e)
            return lscpu_info

        errors: List[Exception] = []
        try:
            cpu_data: List[str] = lscpu_out.strip().split("\n")
            for info in cpu_data:
                try:
                    key, value = info.split(":")
                    nkey: str = ".".join(["lscpu", key.lower().strip().replace(" ", "_")])
                    lscpu_info[nkey] = "%s" % value.strip()
                except ValueError as e:
                    # sometimes lscpu outputs weird things. Or fails.
                    # But this is per line, so keep track but let it pass.
                    errors.append(e)

        except Exception as e:
            log.warning("Error reading system CPU information: %s", e)
        if errors:
            log.debug("Errors while parsing lscpu output: %s", errors)

        return lscpu_info

    def _parse_lscpu_json_output(self, lscpu_env: Dict[str, str]) -> Dict[str, str]:
        lscpu_cmd: List[str] = [self.LSCPU_CMD, "--json"]
        if self.testing:
            lscpu_cmd += ["-s", self.prefix]

        try:
            output: bytes = subprocess.check_output(lscpu_cmd, env=lscpu_env)
        except subprocess.CalledProcessError as e:
            log.warning("Failed to run 'lscpu --json': %s", e)
            return {}

        try:
            output_json: dict = json.loads(output)
        except json.JSONDecodeError:
            log.exception("Failed to load the lscpu JSON: %s", output)
            return {}

        try:
            main_object: dict = output_json["lscpu"]
        except KeyError:
            log.warning("Failed to load the lscpu JSON: missing 'lscpu' " "root object")
            return {}

        lscpu_info: Dict[str, str] = {}

        def parse_item(obj: dict) -> None:
            try:
                # get 'field' and 'data', considering them mandatory, and thus
                # ignoring this element and all its children if they are
                # missing; note that 'data' can be null, see later on
                key = obj["field"]
                value = obj["data"]
            except KeyError:
                log.warning(
                    "Failed to load the lscpu JSON: object lacks " "missing 'field' and 'data' fields: %s",
                    obj,
                )
                return
            # 'data' is null, which means the field is an "header"; ignore it
            if value is not None:
                if key.endswith(":"):
                    key = key[:-1]
                nkey: str = ".".join(["lscpu", key.lower().strip().replace(" ", "_")])
                lscpu_info[nkey] = value.strip()
            try:
                children = obj["children"]
                parse_list(children)
            except KeyError:
                # no 'children' field available, which is OK
                pass

        def parse_list(json_list) -> None:
            for list_item in json_list:
                parse_item(list_item)

        parse_list(main_object)

        return lscpu_info


if __name__ == "__main__":
    _LIBPATH = "/usr/share/rhsm"
    # add to the path if need be
    if _LIBPATH not in sys.path:
        sys.path.append(_LIBPATH)

    from rhsm import logutil

    logutil.init_logger()

    hw = HardwareCollector(prefix=sys.argv[1], testing=True)

    if len(sys.argv) > 1:
        hw.prefix = sys.argv[1]
        hw.testing = True
    hw_dict = hw.get_all()

    # just show the facts collected, unless we specify data dir and well,
    # anything else
    if len(sys.argv) > 2:
        for hkey, hvalue in sorted(hw_dict.items()):
            print("'%s' : '%s'" % (hkey, hvalue))

    if not hw.testing:
        sys.exit(0)

    # verify the cpu socket info collection we use for rhel5 matches lscpu
    cpu_items: List[Tuple[str, str]] = [
        ("cpu.core(s)_per_socket", "lscpu.core(s)_per_socket"),
        ("cpu.cpu(s)", "lscpu.cpu(s)"),
        # NOTE: the substring is different for these two folks...
        # FIXME: follow up to see if this has changed
        ("cpu.cpu_socket(s)", "lscpu.socket(s)"),
        ("cpu.book(s)", "lscpu.book(s)"),
        ("cpu.thread(s)_per_core", "lscpu.thread(s)_per_core"),
        ("cpu.socket(s)_per_book", "lscpu.socket(s)_per_book"),
    ]
    failed: bool = False
    failed_list: List[Tuple[str, str, int, int]] = []
    for cpu_item in cpu_items:
        value_0 = int(hw_dict.get(cpu_item[0], -1))
        value_1 = int(hw_dict.get(cpu_item[1], -1))

        if value_0 != value_1 and ((value_0 != -1) and (value_1 != -1)):
            failed_list.append((cpu_item[0], cpu_item[1], value_0, value_1))

    must_haves = ["cpu.cpu_socket(s)", "cpu.cpu(s)", "cpu.core(s)_per_socket", "cpu.thread(s)_per_core"]
    missing_set = set(must_haves).difference(set(hw_dict))

    if failed:
        print("cpu detection error")
    for failed in failed_list:
        print("The values %s %s do not match (|%s| != |%s|)" % (failed[0], failed[1], failed[2], failed[3]))
    if missing_set:
        for missing in missing_set:
            print("cpu info fact: %s was missing" % missing)

    if failed:
        sys.exit(1)
