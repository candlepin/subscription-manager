#
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

import commands
import ethtool
import gettext
import logging
import os
import platform
import re
import socket
from subprocess import PIPE, Popen
import sys

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


# Exception classes used by this module.
# from later versions of subprocess, but not there on 2.4, so include our version
class CalledProcessError(Exception):
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


class ClassicCheck:

    def is_registered_with_classic(self):
        try:
            sys.path.append('/usr/share/rhn')
            from up2date_client import up2dateAuth
        except ImportError:
            return False

        return up2dateAuth.getSystemId() is not None


# take a string like '1-4' and returns a list of
# ints like [1,2,3,4]
# 31-37 return [31,32,33,34,35,36,37]
def parse_range(range_str):
    range_list = range_str.split('-')
    start = int(range_list[0])
    end = int(range_list[-1])

    return range(start, end + 1)


# util to total up the values represented by a cpu siblings list
# ala /sys/devices/cpu/cpu0/topology/core_siblings_list
#
# which can be a comma seperated list of ranges
#  1,2,3,4
#  1-2, 4-6, 8-10, 12-14
#
def gather_entries(entries_string):
    entries = []
    entry_parts = entries_string.split(',')
    for entry_part in entry_parts:
        # return a list of enumerated items
        entry_range = parse_range(entry_part)
        for entry in entry_range:
            entries.append(entry)
    return entries


class DmiInfo(object):

    def __init__(self, hardware_info, dump_file=None):
        self.hardware_info = hardware_info
        self.dump_file = dump_file
        self.socket_designation = []
        self.info = self.get_gmi_info()

    def get_gmi_info(self):
        import dmidecode
        if self.dump_file:
            if os.access(self.dump_file, os.R_OK):
                dmidecode.set_dev(self.dump_file)

        dmiinfo = {}
        dmi_data = {
            "dmi.bios.": self._read_dmi(dmidecode.bios),
            "dmi.processor.": self._read_dmi(dmidecode.processor),
            "dmi.baseboard.": self._read_dmi(dmidecode.baseboard),
            "dmi.chassis.": self._read_dmi(dmidecode.chassis),
            "dmi.slot.": self._read_dmi(dmidecode.slot),
            "dmi.system.": self._read_dmi(dmidecode.system),
            "dmi.memory.": self._read_dmi(dmidecode.memory),
            "dmi.connector.": self._read_dmi(dmidecode.connector),
        }

        try:
            for tag, func in dmi_data.items():
                dmiinfo = self._get_dmi_data(func, tag, dmiinfo)
        except Exception, e:
            log.warn(_("Error reading system DMI information: %s"), e)

        # cpu topology reporting on xen dom0 machines is wrong. So
        # if we are a xen dom0, and we found socket info in dmiinfo,
        # replace our normal cpu socket calculation with the dmiinfo one
        # we have to do it after the virt data and cpu data collection
        if 'virt.host_type' in self.hardware_info:
            if self.hardware_info['virt.host_type'].find('dom0') > -1:
                if self.socket_designation:
                    socket_count = len(self.socket_designation)
                    self.hardware_info['cpu.cpu_socket(s)'] = socket_count
                    if 'cpu.cpu(s)' in self.hardware_info:
                        self.hardware_info['cpu.core(s)_per_socket'] = \
                                int(self.hardware_info['cpu.cpu(s)']) / socket_count

        return dmiinfo

    def _read_dmi(self, func):
        try:
            return func()
        except Exception, e:
            log.warn(_("Error reading system DMI information with %s: %s"), func, e)
            return None

    def _get_dmi_data(self, func, tag, ddict):
        for key, value in func.items():
            for key1, value1 in value['data'].items():
                # FIXME: this loses useful data...
                if not isinstance(value1, str):
                    # we are skipping things like int and bool values, as
                    # well as lists and dicts
                    continue

                # keep track of any cpu socket info we find, we have to do
                # it here, since we flatten it and lose the info creating nkey
                if tag == 'dmi.processor.' and key1 == 'Socket Designation':
                    self.socket_designation.append(value1)

                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                ddict[nkey] = str(value1)

        return ddict


class Hardware:

    def __init__(self, prefix=None, testing=None):
        self.allhw = {}
        # prefix to look for /sys, for testing
        self.prefix = prefix or ''
        self.testing = testing or False

        # we need this so we can decide which of the
        # arch specific code bases to follow
        self.arch = self._get_arch()

    def _get_arch(self):

        if self.testing and self.prefix:
            arch_file = "%s/arch" % self.prefix
            if os.access(arch_file, os.R_OK):
                try:
                    f = open(arch_file, 'r')
                except IOError:
                    return platform.machine()
                buf = f.read().strip()
                f.close()
                return buf
            return platform.machine()
        return platform.machine()

    def get_uname_info(self):

        uname_data = os.uname()
        uname_keys = ('uname.sysname', 'uname.nodename', 'uname.release',
                      'uname.version', 'uname.machine')
        self.unameinfo = dict(zip(uname_keys, uname_data))
        self.allhw.update(self.unameinfo)
        return self.unameinfo

    def get_release_info(self):
        distro_keys = ('distribution.name', 'distribution.version',
                       'distribution.id')
        self.releaseinfo = dict(zip(distro_keys, self.get_distribution()))
        self.allhw.update(self.releaseinfo)
        return self.releaseinfo

    def _open_release(self, filename):
        return open(filename, 'r')

    # this version os very RHEL/Fedora specific...
    def get_distribution(self):

        if hasattr(platform, 'linux_distribution'):
            return platform.linux_distribution()

        # from platform.py from python2.
        _lsb_release_version = re.compile(r'(.+)'
                                          ' release '
                                          '([\d.]+)'
                                          '[^(]*(?:\((.+)\))?')
        f = self._open_release('/etc/redhat-release')
        firstline = f.readline()
        f.close()

        version = "Unknown"
        distname = "Unknown"
        dist_id = "Unknown"

        m = _lsb_release_version.match(firstline)

        if m is not None:
            return tuple(m.groups())

        return distname, version, dist_id

    def get_mem_info(self):
        self.meminfo = {}

        # most of this mem info changes constantly, which makes decding
        # when to update facts painful, so lets try to just collect the
        # useful bits

        useful = ["MemTotal", "SwapTotal"]
        try:
            parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
            memdata = open('/proc/meminfo')
            for info in memdata:
                match = parser.match(info)
                if not match:
                    continue
                key, value = match.groups(['key', 'value'])
                if key in useful:
                    nkey = '.'.join(["memory", key.lower()])
                    self.meminfo[nkey] = "%s" % int(value)
        except Exception, e:
            print _("Error reading system memory information:"), e
        self.allhw.update(self.meminfo)
        return self.meminfo

    def count_cpumask_entries(self, cpu, field):
        try:
            f = open("%s/topology/%s" % (cpu, field), 'r')
        except IOError:
            return None

        # ia64 entries seem to be null padded, or perhaps
        # that's a collection error
        # FIXME
        entries = f.read().rstrip('\n\x00')
        f.close()
        # these fields can exist, but be empty. For example,
        # thread_siblings_list from s390x-rhel64-zvm-2cpu-has-topo
        # test data

        if len(entries):
            cpumask_entries = gather_entries(entries)
            return len(cpumask_entries)
        # that field was empty
        return None

    # replace/add with getting CPU Totals for s390x
    def _parse_s390x_sysinfo_topology(self, cpu_count, sysinfo):
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
                parts = line.split(':', 1)
                s390_topo_str = parts[1]
                topo_parts = s390_topo_str.split()

                # indexes 3/4/5 being books/sockets_per_book,
                # and cores_per_socket based on lscpu.c
                book_count = int(topo_parts[3])
                sockets_per_book = int(topo_parts[4])
                cores_per_socket = int(topo_parts[5])

                socket_count = book_count * sockets_per_book
                cores_count = socket_count * cores_per_socket

                return {'socket_count': socket_count,
                        'cores_count': cores_count,
                        'book_count': book_count,
                        'sockets_per_book': sockets_per_book,
                        'cores_per_socket': cores_per_socket}
        log.debug("Looking for 'CPU Topology SW' in sysinfo, but it was not found")
        return None

    def has_s390x_sysinfo(self, proc_sysinfo):
        if not os.access(proc_sysinfo, os.R_OK):
            return False

        return True

    def read_s390x_sysinfo(self, cpu_count, proc_sysinfo):
        lines = []
        try:
            f = open(proc_sysinfo, 'r')
        except IOError:
            return lines

        lines = f.readlines()
        f.close()
        return lines

    def read_physical_id(self, cpu_file):
        try:
            f = open("%s/physical_id" % cpu_file, 'r')
        except IOError:
            return None

        buf = f.read().strip()
        f.close()
        return buf

    def _ppc64_fallback(self, cpu_files):

        # ppc64, particular POWER5/POWER6 machines, show almost
        # no cpu information on rhel5. There is a "physical_id"
        # associated with each cpu that seems to map to a
        # cpu, in a socket
        log.debug("trying ppc64 specific cpu topology detection")
        # try to find cpuN/physical_id
        physical_ids = set()
        for cpu_file in cpu_files:
            physical_id = self.read_physical_id(cpu_file)
            # offline cpu's show physical id of -1. Normally
            # we count all present cpu's even if offline, but
            # in this case, we can't get any cpu info from the
            # cpu since it is offline, so don't count it
            if physical_id != '-1':
                physical_ids.add(physical_id)

        if physical_ids:
            # For rhel6 or newer, we have more cpu topology info
            # exposed by the kernel which will override this
            socket_count = len(physical_ids)
            # add marker here so we know we fail back to this
            log.debug("Using /sys/devices/system/cpu/cpu*/physical_id for cpu info on ppc64")
            return socket_count

        return None

    def get_cpu_info(self):
        self.cpuinfo = {}
        # we also have cpufreq, etc in this dir, so match just the numbs
        cpu_re = r'cpu([0-9]+$)'

        cpu_files = []
        sys_cpu_path = self.prefix + "/sys/devices/system/cpu/"
        for cpu in os.listdir(sys_cpu_path):
            if re.match(cpu_re, cpu):
                cpu_files.append("%s/%s" % (sys_cpu_path, cpu))

        cpu_count = len(cpu_files)

        # see if we have a /proc/sysinfo ala s390, if so
        # prefer that info
        proc_sysinfo = self.prefix + "/proc/sysinfo"
        has_sysinfo = self.has_s390x_sysinfo(proc_sysinfo)

        # s390x can have cpu 'books'
        books = False

        cores_per_socket = None

        # assume each socket has the same number of cores, and
        # each core has the same number of threads.
        #
        # This is not actually true sometimes... *cough*s390x*cough*
        # but lscpu makes the same assumption

        threads_per_core = self.count_cpumask_entries(cpu_files[0],
                                                      'thread_siblings_list')
        cores_per_cpu = self.count_cpumask_entries(cpu_files[0],
                                                   'core_siblings_list')

        # if we find valid values in cpu/cpuN/topology/*siblings_list
        # sometimes it's not there, particularly on rhel5
        if threads_per_core and cores_per_cpu:
            cores_per_socket = cores_per_cpu / threads_per_core
            self.cpuinfo["cpu.topology_source"] = "kernel /sys cpu sibling lists"

            # rhel6 s390x can have /sys cpu topo, but we can't make assumption
            # about it being evenly distributed, so if we also have topo info
            # in sysinfo, prefer that
            if self.arch == "s390x" and has_sysinfo:
                # for s390x on lpar, try to see if /proc/sysinfo has any
                # topo info
                log.debug("/proc/sysinfo found, attempting to gather cpu topology info")
                sysinfo_lines = self.read_s390x_sysinfo(cpu_count, proc_sysinfo)
                if sysinfo_lines:
                    sysinfo = self._parse_s390x_sysinfo_topology(cpu_count, sysinfo_lines)

                    # verify the sysinfo has system level virt info
                    if sysinfo:
                        self.cpuinfo["cpu.topology_source"] = "s390x sysinfo"
                        socket_count = sysinfo['socket_count']
                        book_count = sysinfo['book_count']
                        sockets_per_book = sysinfo['sockets_per_book']
                        cores_per_socket = sysinfo['cores_per_socket']
                        threads_per_core = 1

                        # we can have a mismatch between /sys and /sysinfo. We
                        # defer to sysinfo in this case even for cpu_count
        #                cpu_count = sysinfo['cores_count'] * threads_per_core
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
                    self.cpuinfo["cpu.topology_source"] = "ppc64 physical_package_id"

            else:
                # all of our usual methods failed us...
                log.debug("No cpu socket info found for real or virtual hardware")
                # so we can track if we get this far
                self.cpuinfo["cpu.topology_source"] = "fallback one socket"
                socket_count = cpu_count

            # for some odd cases where there are offline ppc64 cpu's,
            # this can end up not being a whole number...
            cores_per_socket = cpu_count / socket_count

        if cores_per_socket and threads_per_core:
            # for s390x with sysinfo topo, we use the sysinfo numbers except
            # for cpu_count, which takes offline cpus into account. This is
            # mostly just to match lscpu behaviour here
            if self.cpuinfo["cpu.topology_source"] != "s390x sysinfo":
                socket_count = cpu_count / cores_per_socket / threads_per_core

        # s390 etc
        # for s390, socket calculations are per book, and we can have multiple
        # books, so multiply socket count by book count
        # see if we are on a s390 with book info
        # all s390 platforms show book siblings, even the ones that also
        # show sysinfo (lpar)... Except on rhel5, where there is no
        # cpu topology info with lpar
        #
        # if we got book info from sysinfo, prefer it
        book_siblings_per_cpu = None
        if not books:
            book_siblings_per_cpu = self.count_cpumask_entries(cpu_files[0],
                                                            'book_siblings_list')
            if book_siblings_per_cpu:
                book_count = cpu_count / book_siblings_per_cpu
                sockets_per_book = book_count / socket_count
                self.cpuinfo["cpu.topology_source"] = "s390 book_siblings_list"
                books = True

        # we should always know this...
        self.cpuinfo["cpu.cpu(s)"] = cpu_count

        # these may be unknown...
        if socket_count:
            self.cpuinfo['cpu.cpu_socket(s)'] = socket_count
        if cores_per_socket:
            self.cpuinfo['cpu.core(s)_per_socket'] = cores_per_socket
        if threads_per_core:
            self.cpuinfo["cpu.thread(s)_per_core"] = threads_per_core

        if book_siblings_per_cpu:
            self.cpuinfo["cpu.book(s)_per_cpu"] = book_siblings_per_cpu

        if books:
            self.cpuinfo["cpu.socket(s)_per_book"] = sockets_per_book
            self.cpuinfo["cpu.book(s)"] = book_count

        log.debug("cpu info: %s" % self.cpuinfo)
        self.allhw.update(self.cpuinfo)
        return self.cpuinfo

    def get_ls_cpu_info(self):
        # if we have `lscpu`, let's use it for facts as well, under
        # the `lscpu` name space
        if not os.access('/usr/bin/lscpu', os.R_OK):
            return

        self.lscpuinfo = {}
        # let us specify a test dir of /sys info for testing
        ls_cpu_path = 'LANG=en_US.UTF-8 /usr/bin/lscpu'
        ls_cpu_cmd = ls_cpu_path

        if self.testing:
            ls_cpu_cmd = "%s -s %s" % (ls_cpu_cmd, self.prefix)
        try:
            cpudata = commands.getstatusoutput(ls_cpu_cmd)[-1].split('\n')
            for info in cpudata:
                try:
                    key, value = info.split(":")
                    nkey = '.'.join(["lscpu", key.lower().strip().replace(" ", "_")])
                    self.lscpuinfo[nkey] = "%s" % value.strip()
                except ValueError:
                    # sometimes lscpu outputs weird things. Or fails.
                    #
                    pass
        except Exception, e:
            print _("Error reading system CPU information:"), e
        self.allhw.update(self.lscpuinfo)
        return self.lscpuinfo

    def get_network_info(self):
        self.netinfo = {}
        try:
            host = socket.gethostname()
            self.netinfo['network.hostname'] = host

            try:
                info = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
                ip_list = set([x[4][0] for x in info])
                self.netinfo['network.ipv4_address'] = ', '.join(ip_list)
            except Exception:
                self.netinfo['network.ipv4_address'] = "127.0.0.1"

            try:
                info = socket.getaddrinfo(host, None, socket.AF_INET6, socket.SOCK_STREAM)
                ip_list = set([x[4][0] for x in info])
                self.netinfo['network.ipv6_address'] = ', '.join(ip_list)
            except Exception:
                self.netinfo['network.ipv6_address'] = "::1"

        except Exception, e:
            print _("Error reading networking information:"), e
        self.allhw.update(self.netinfo)
        return self.netinfo

    def _should_get_mac_address(self, device):
        if (device.startswith('sit') or device.startswith('lo')):
            return False
        return True

    def get_network_interfaces(self):
        netinfdict = {}
        old_ipv4_metakeys = ['ipv4_address', 'ipv4_netmask', 'ipv4_broadcast']
        ipv4_metakeys = ['address', 'netmask', 'broadcast']
        ipv6_metakeys = ['address', 'netmask']
        try:
            interfaces_info = ethtool.get_interfaces_info(ethtool.get_devices())
            for info in interfaces_info:
                master = None
                mac_address = info.mac_address
                device = info.device
                # Omit mac addresses for sit and lo device types. See BZ838123
                # mac address are per interface, not per address
                if self._should_get_mac_address(device):
                    key = '.'.join(['net.interface', device, 'mac_address'])
                    netinfdict[key] = mac_address

                # all of our supported versions of python-ethtool support
                # get_ipv6_addresses
                for addr in info.get_ipv6_addresses():
                    # ethtool returns a different scope for "public" IPv6 addresses
                    # on different versions of RHEL.  EL5 is "global", while EL6 is
                    # "universe".  Make them consistent.
                    scope = addr.scope
                    if scope == 'universe':
                        scope = 'global'

                    # FIXME: this doesn't support multiple addresses per interface
                    # (it finds them, but collides on the key name and loses all
                    # but the last write). See bz #874735
                    for mkey in ipv6_metakeys:
                        key = '.'.join(['net.interface', info.device, 'ipv6_%s' % (mkey), scope])
                        # we could specify a default here... that could hide
                        # api breakage though and unit testing hw detect is... meh
                        attr = getattr(addr, mkey) or 'Unknown'
                        netinfdict[key] = attr

                # However, old version of python-ethtool do not support
                # get_ipv4_address
                #
                # python-ethtool's api changed between rhel6.3 and rhel6.4
                # (0.6-1.el6 to 0.6-2.el6)
                # (without revving the upstream version... bad python-ethtool!)
                # note that 0.6-5.el5 (from rhel5.9) has the old api
                #
                # previously, we got the 'ipv4_address' from the etherinfo object
                # directly. In the new api, that isn't exposed, so we get the list
                # of addresses on the interface, and populate the info from there.
                #
                # That api change as to address bz #759150. The bug there was that
                # python-ethtool only showed one ip address per interface. To
                # accomdate the finer grained info, the api changed...
                #
                # FIXME: see FIXME for get_ipv6_address, we don't record multiple
                # addresses per interface
                if hasattr(info, 'get_ipv4_addresses'):
                    for addr in info.get_ipv4_addresses():
                        for mkey in ipv4_metakeys:
                            # append 'ipv4_' to match the older interface and keeps facts
                            # consistent
                            key = '.'.join(['net.interface', info.device, 'ipv4_%s' % (mkey)])
                            attr = getattr(addr, mkey) or 'Unknown'
                            netinfdict[key] = attr
                # check to see if we are actually an ipv4 interface
                elif hasattr(info, 'ipv4_address'):
                    for mkey in old_ipv4_metakeys:
                        key = '.'.join(['net.interface', device, mkey])
                        attr = getattr(info, mkey) or 'Unknown'
                        netinfdict[key] = attr
                # otherwise we are ipv6 and we handled that already

                # bonded slave devices can have their hwaddr changed
                #
                # "master" here refers to the slave's master device.
                # If we find a master link, we are a  slave, and we need
                # to check the /proc/net/bonding info to see what the
                # "permanent" hw address are for this slave
                try:
                    master = os.readlink('/sys/class/net/%s/master' % info.device)
                #FIXME
                except Exception:
                    master = None

                if master:
                    master_interface = os.path.basename(master)
                    permanent_mac_addr = self._get_slave_hwaddr(master_interface, info.device)
                    key = '.'.join(['net.interface', info.device, "permanent_mac_address"])
                    netinfdict[key] = permanent_mac_addr

        except Exception:
            print _("Error reading network interface information:"), sys.exc_type
        self.allhw.update(netinfdict)
        return netinfdict

    # from rhn-client-tools  hardware.py
    # see bz#785666
    def _get_slave_hwaddr(self, master, slave):
        hwaddr = ""
        try:
            bonding = open('/proc/net/bonding/%s' % master, "r")
        except:
            return hwaddr

        slave_found = False
        for line in bonding.readlines():
            if slave_found and line.find("Permanent HW addr: ") != -1:
                hwaddr = line.split()[3].upper()
                break

            if line.find("Slave Interface: ") != -1:
                ifname = line.split()[2]
                if ifname == slave:
                    slave_found = True

        bonding.close()
        return hwaddr

    def get_virt_info(self):
        virt_dict = {}

        try:
            host_type = self._get_output('virt-what')

            # If this is blank, then not a guest
            virt_dict['virt.is_guest'] = bool(host_type)
            if bool(host_type):
                virt_dict['virt.is_guest'] = True
                virt_dict['virt.host_type'] = host_type
            else:
                virt_dict['virt.is_guest'] = False
                virt_dict['virt.host_type'] = "Not Applicable"
        # TODO:  Should this only catch OSErrors?
        except Exception, e:
            # Otherwise there was an error running virt-what - who knows
            log.exception(e)
            virt_dict['virt.is_guest'] = 'Unknown'

        # xen dom0 is a guest for virt-what's purposes, but is a host for
        # our purposes. Adjust is_guest accordingly. (#757697)
        try:
            if virt_dict['virt.host_type'].find('dom0') > -1:
                virt_dict['virt.is_guest'] = False
        except KeyError:
            # if host_type is not defined, do nothing (#768397)
            pass

        self.allhw.update(virt_dict)
        return virt_dict

    def _get_output(self, cmd):
        process = Popen([cmd], stdout=PIPE)
        output = process.communicate()[0].strip()

        returncode = process.poll()
        if returncode:
            raise CalledProcessError(returncode,
                                     cmd,
                                     output=output)

        return output

    def get_platform_specific_info(self):
        """
        Read and parse data that comes from platform specific interfaces.
        This is only dmi/smbios data for now (which isn't on ppc/s390).
        """

        no_dmi_arches = ['ppc', 'ppc64', 's390', 's390x']
        arch = self.arch
        if arch in no_dmi_arches:
            log.debug("not looking for dmi info due to system arch '%s'" % arch)
            platform_specific_info = {}
        else:
            if self.testing and self.prefix:
                dump_file = "%s/dmi.dump" % self.prefix
                platform_specific_info = DmiInfo(self.allhw, dump_file=dump_file).info
            else:
                platform_specific_info = DmiInfo(self.allhw).info

        self.allhw.update(platform_specific_info)

    def get_virt_uuid(self):
        """
        Given a populated fact list, add on a virt.uuid fact if appropriate.
        Partially adapted from Spacewalk's rhnreg.py, example hardware reporting
        found in virt-what tests
        """
        no_uuid_platforms = ['powervm_lx86', 'xen-dom0', 'ibm_systemz']

        self.allhw['virt.uuid'] = 'Unknown'

        try:
            for v in no_uuid_platforms:
                if self.allhw['virt.host_type'].find(v) > -1:
                    raise Exception(_("Virtualization platform does not support UUIDs"))
        except Exception, e:
            log.warn(_("Error finding UUID: %s"), e)
            return  # nothing more to do

        #most virt platforms record UUID via DMI/SMBIOS info.
        if 'dmi.system.uuid' in self.allhw:
            self.allhw['virt.uuid'] = self.allhw['dmi.system.uuid']

        #potentially override DMI-determined UUID with
        #what is on the file system (xen para-virt)
        try:
            uuid_file = open('/sys/hypervisor/uuid', 'r')
            uuid = uuid_file.read()
            uuid_file.close()
            self.allhw['virt.uuid'] = uuid.rstrip("\r\n")
        except IOError:
            pass

    def get_all(self):
        hardware_methods = [self.get_uname_info,
                            self.get_release_info,
                            self.get_mem_info,
                            self.get_cpu_info,
                            self.get_ls_cpu_info,
                            self.get_network_info,
                            self.get_network_interfaces,
                            self.get_virt_info,
                            # this has to happen after everything else, since
                            # it expects to check virt and processor info
                            self.get_platform_specific_info]
        # try each hardware method, and try/except around, since
        # these tend to be fragile
        for hardware_method in hardware_methods:
            try:
                hardware_method()
            except Exception, e:
                log.warn("%s" % hardware_method)
                log.warn("Hardware detection failed: %s" % e)

        #we need to know the DMI info and VirtInfo before determining UUID.
        #Thus, we can't figure it out within the main data collection loop.
        if self.allhw.get('virt.is_guest'):
            self.get_virt_uuid()

        import dmidecode
        dmiwarnings = dmidecode.get_warnings()
        if dmiwarnings:
            log.warn(_("Error reading system DMI information: %s"), dmiwarnings)
            dmidecode.clear_warnings()
        return self.allhw


if __name__ == '__main__':
    _LIBPATH = "/usr/share/rhsm"
      # add to the path if need be
    if _LIBPATH not in sys.path:
        sys.path.append(_LIBPATH)

    from subscription_manager import logutil
    logutil.init_logger()

    hw = Hardware(prefix=sys.argv[1], testing=True)

    if len(sys.argv) > 1:
        hw.prefix = sys.argv[1]
        hw.testing = True
    hw_dict = hw.get_all()

    # just show the facts collected
    if not hw.testing:
        for hkey, hvalue in sorted(hw_dict.items()):
            print "'%s' : '%s'" % (hkey, hvalue)

    if not hw.testing:
        sys.exit(0)

    # verify the cpu socket info collection we use for rhel5 matches lscpu
    cpu_items = [('cpu.core(s)_per_socket', 'lscpu.core(s)_per_socket'),
                 ('cpu.cpu(s)', 'lscpu.cpu(s)'),
                 # NOTE: the substring is different for these two folks...
                 # FIXME: follow up to see if this has changed
                 ('cpu.cpu_socket(s)', 'lscpu.socket(s)'),
                 ('cpu.book(s)', 'lscpu.book(s)'),
                 ('cpu.thread(s)_per_core', 'lscpu.thread(s)_per_core'),
                 ('cpu.socket(s)_per_book', 'lscpu.socket(s)_per_book')]
    failed = False
    failed_list = []
    for cpu_item in cpu_items:
        value_0 = int(hw_dict.get(cpu_item[0], -1))
        value_1 = int(hw_dict.get(cpu_item[1], -1))

        #print "%s/%s: %s %s" % (cpu_item[0], cpu_item[1], value_0, value_1)

        if value_0 != value_1 and ((value_0 != -1) and (value_1 != -1)):
            failed_list.append((cpu_item[0], cpu_item[1], value_0, value_1))

    must_haves = ['cpu.cpu_socket(s)', 'cpu.cpu(s)', 'cpu.core(s)_per_socket', 'cpu.thread(s)_per_core']
    missing_set = set(must_haves).difference(set(hw_dict))

    if failed:
        print "cpu detection error"
    for failed in failed_list:
        print "The values %s %s do not match (|%s| != |%s|)" % (failed[0], failed[1],
                                                                failed[2], failed[3])
    if missing_set:
        for missing in missing_set:
            print "cpu info fact: %s was missing" % missing

    if failed:
        sys.exit(1)
