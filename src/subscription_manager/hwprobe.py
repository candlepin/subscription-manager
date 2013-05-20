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
import signal
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
    # not a range, just a string ala, 7
    # return a list of [7]
    if '-' not in range_str:
        return [int(range_str)]

    range_ends = range_str.split('-')
    start = int(range_ends[0])
    end = int(range_ends[1])

    range_list = []
    for i in range(start, end + 1):
        range_list.append(i)
    return range_list


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

    def __init__(self):
        self.info = self.get_gmi_info()

    def get_gmi_info(self):
        import dmidecode
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
                if not isinstance(value1, str):
                    continue
                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                ddict[nkey] = str(value1)

        return ddict


class Hardware:

    def __init__(self):
        self.allhw = {}
        # prefix to look for /sys, for testing
        self.prefix = ''
        self.testing = False

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
        cpumask_entries = gather_entries(entries)
        return len(cpumask_entries)

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

        # assume each socket has the same number of cores, and
        # each core has the same number of threads.
        #
        # This is not actually true sometimes... *cough*s390x*cough*
        # but lscpu makes the same assumption

        threads_per_cpu = self.count_cpumask_entries(cpu_files[0], 'thread_siblings_list')
        cores_per_cpu = self.count_cpumask_entries(cpu_files[0], 'core_siblings_list') / threads_per_cpu
        book_siblings_per_cpu = self.count_cpumask_entries(cpu_files[0], 'book_siblings_list')

        #print cpu_count, cores_per_cpu, threads_per_cpu
        socket_count = cpu_count / cores_per_cpu / threads_per_cpu

        # for s390, socket calculates are per book, and we can have multiple
        # books, so multiply socket count by book count

        if book_siblings_per_cpu:
            book_count = cpu_count / book_siblings_per_cpu

        self.cpuinfo['cpu.cpu_socket(s)'] = socket_count
        self.cpuinfo['cpu.core(s)_per_socket'] = cores_per_cpu
        self.cpuinfo["cpu.cpu(s)"] = cpu_count
        self.cpuinfo["cpu.thread(s)_per_core"] = threads_per_cpu

        # s390 etc
        if book_siblings_per_cpu:
            self.cpuinfo["cpu.book(s)_per_cpu"] = book_siblings_per_cpu
            self.cpuinfo["cpu.socket(s)_per_book"] = book_count / socket_count
            self.cpuinfo["cpu.book(s)"] = book_count

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
                key, value = info.split(":")
                nkey = '.'.join(["lscpu", key.lower().strip().replace(" ", "_")])
                self.lscpuinfo[nkey] = "%s" % value.strip()
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
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        process = Popen([cmd], stdout=PIPE)
        output = process.communicate()[0].strip()

        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        returncode = process.poll()
        if returncode:
            raise CalledProcessError(returncode, cmd, output=output)

        return output

    def get_platform_specific_info(self):
        """
        Read and parse data that comes from platform specific interfaces.
        This is only dmi/smbios data for now (which isn't on ppc/s390).
        """

        no_dmi_arches = ['ppc', 'ppc64', 's390', 's390x']
        arch = platform.machine()
        if arch in no_dmi_arches:
            log.debug("not looking for dmi info due to system arch '%s'" % arch)
            platform_specific_info = {}
        else:
            platform_specific_info = DmiInfo().info
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

    hw = Hardware()

    if len(sys.argv) > 1:
        hw.prefix = sys.argv[1]
        hw.testing = True
    #print "hw.prefix", hw.prefix, sys.argv
    #print "hw.testing", hw.testing
    hw_dict = hw.get_all()
    #print "foo"
    if True or not hw.testing:
        for hkey, hvalue in sorted(hw_dict.items()):
            print "'%s' : '%s'" % (hkey, hvalue)
    #print "bar"

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
        #print "blip", hw_dict.get(cpu_item[0])
        value_0 = int(hw_dict.get(cpu_item[0], -1))
        value_1 = int(hw_dict.get(cpu_item[1], -1))
        print "| %s | %s |" % (cpu_item[0], cpu_item[1])
        print "%s  %s" % (value_0, value_1)
        if value_0 != value_1 and ((value_0 != -1) and (value_1 != -1)):
            failed_list.append((cpu_item[0], cpu_item[1], value_0, value_1))

    if failed:
        print "cpu detection error"
    for failed in failed_list:
            print "The values %s %s do not match (|%s| != |%s|)" % (failed[0], failed[1],
                                                                    failed[2], failed[3])

    if failed:
        sys.exit(1)
