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

import os
import sys
import signal
import re
import logging
import gettext
_ = gettext.gettext
import ethtool
import socket
import commands
import platform

from subprocess import Popen, PIPE


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


log = logging.getLogger('rhsm-app.' + __name__)


class ClassicCheck:

    def is_registered_with_classic(self):
        try:
            sys.path.append('/usr/share/rhn')
            from up2date_client import up2dateAuth
        except ImportError:
            return False

        return up2dateAuth.getSystemId() is not None


class DmiInfo(object):

    def __init__(self):
        self.info = self.getDmiInfo()

    def getDmiInfo(self):
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

    def getUnameInfo(self):

        uname_data = os.uname()
        uname_keys = ('uname.sysname', 'uname.nodename', 'uname.release',
                      'uname.version', 'uname.machine')
        self.unameinfo = dict(zip(uname_keys, uname_data))
        self.allhw.update(self.unameinfo)
        return self.unameinfo

    def getReleaseInfo(self):
        distro_keys = ('distribution.name', 'distribution.version',
                       'distribution.id')
        self.releaseinfo = dict(zip(distro_keys, self.getDistribution()))
        self.allhw.update(self.releaseinfo)
        return self.releaseinfo

    def _open_release(self, filename):
        return open(filename, 'r')

    # this version os very RHEL/Fedora specific...
    def getDistribution(self):

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

    def getMemInfo(self):
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
        except:
            print _("Error reading system memory information:"), sys.exc_type
        self.allhw.update(self.meminfo)
        return self.meminfo

    def _getSocketIdForCpu(self, cpu):
        physical_package_id = "%s/topology/physical_package_id" % cpu

        # this can happen for a couple of cases. xen hosts/guests don't
        # seem to populate this at all. cross arch kvm guests only seem
        # to populate it for cpu0.
        try:
            f = open(physical_package_id)
        except IOError:
            log.warn("no physical_package_id found for cpu: %s" % cpu)
            return None
        socket_id = f.readline()
        return socket_id

    def getCpuInfo(self):
        # TODO:(prad) Revisit this and see if theres a better way to parse /proc/cpuinfo
        # perhaps across all arches
        self.cpuinfo = {}

        # we also have cpufreq, etc in this dir, so match just the numbs
        cpu_re = r'cpu([0-9]+$)'

        cpu_files = []
        sys_cpu_path = "/sys/devices/system/cpu/"
        for cpu in os.listdir(sys_cpu_path):
            if re.match(cpu_re, cpu):
                cpu_files.append("%s/%s" % (sys_cpu_path, cpu))

        cpu_count = 0
        socket_dict = {}

        for cpu in cpu_files:
            cpu_count = cpu_count + 1
            socket_id = self._getSocketIdForCpu(cpu)

            if socket_id is None:
                continue

            if socket_id not in socket_dict:
                socket_dict[socket_id] = 1
            else:
                socket_dict[socket_id] = socket_dict[socket_id] + 1

        # we didn't detect any cpu socket info, for example
        # xen hosts that do not export any cpu  topology info
        # assume one socket
        num_sockets = len(socket_dict)
        if num_sockets == 0:
            num_sockets = 1
        self.cpuinfo['cpu.cpu_socket(s)'] = num_sockets
        self.cpuinfo['cpu.core(s)_per_socket'] = cpu_count / num_sockets
        self.cpuinfo["cpu.cpu(s)"] = cpu_count
        self.allhw.update(self.cpuinfo)
        return self.cpuinfo

    def getLsCpuInfo(self):
        # if we have `lscpu`, let's use it for facts as well, under
        # the `lscpu` name space

        if not os.access('/usr/bin/lscpu', os.R_OK):
            return

        self.lscpuinfo = {}
        try:
            cpudata = commands.getstatusoutput('LANG=en_US.UTF-8 /usr/bin/lscpu')[-1].split('\n')
            for info in cpudata:
                key, value = info.split(":")
                nkey = '.'.join(["lscpu", key.lower().strip().replace(" ", "_")])
                self.lscpuinfo[nkey] = "%s" % value.strip()
        except:
            print _("Error reading system cpu information:"), sys.exc_type
        self.allhw.update(self.lscpuinfo)
        return self.lscpuinfo

    def getNetworkInfo(self):
        self.netinfo = {}
        try:
            host = socket.gethostname()
            self.netinfo['network.hostname'] = host

            try:
                info = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
                ip_list = set([x[4][0] for x in info])
                self.netinfo['network.ipv4_address'] = ', '.join(ip_list)
            except:
                self.netinfo['network.ipv4_address'] = "127.0.0.1"

            try:
                info = socket.getaddrinfo(host, None, socket.AF_INET6, socket.SOCK_STREAM)
                ip_list = set([x[4][0] for x in info])
                self.netinfo['network.ipv6_address'] = ', '.join(ip_list)
            except:
                self.netinfo['network.ipv6_address'] = "::1"

        except:
            print _("Error reading networking information:"), sys.exc_type
        self.allhw.update(self.netinfo)
        return self.netinfo

    def getNetworkInterfaces(self):
        netinfdict = {}
        metakeys = ['mac_address', 'ipv4_address', 'ipv4_netmask', 'ipv4_broadcast']
        ipv6_metakeys = ['address', 'netmask']
        try:
            for info in ethtool.get_interfaces_info(ethtool.get_devices()):
                for addr in info.get_ipv6_addresses():
                    for mkey in ipv6_metakeys:
                        # ethtool returns a different scope for "public" IPv6 addresses
                        # on different versions of RHEL.  EL5 is "global", while EL6 is
                        # "universe".  Make them consistent.
                        scope = addr.scope
                        if scope == 'universe':
                            scope = 'global'

                        key = '.'.join(['net.interface', info.device, 'ipv6_%s' % (mkey), scope])
                        attr = getattr(addr, mkey)
                        if attr:
                            netinfdict[key] = attr
                        else:
                            netinfdict[key] = "Unknown"

                # XXX: The kernel supports multiple IPv4 addresses on a single
                # interface when using iproute2.  However, the ethtool.etherinfo.ipv4_*
                # members will only return the last retrieved IPv4 configuration.  As
                # of 25 Jan 2012 work on a patch was in progress.  See BZ 759150.
                for mkey in metakeys:
                    key = '.'.join(['net.interface', info.device, mkey])
                    attr = getattr(info, mkey)
                    if attr:
                        netinfdict[key] = attr
                    else:
                        netinfdict[key] = "Unknown"
        except:
            print _("Error reading network interface information:"), sys.exc_type
        self.allhw.update(netinfdict)
        return netinfdict

    def getVirtInfo(self):
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

    def getPlatformSpecificInfo(self):
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

    def _getVirtUUID(self):
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

    def getAll(self):
        hardware_methods = [self.getUnameInfo,
                            self.getReleaseInfo,
                            self.getMemInfo,
                            self.getCpuInfo,
                            self.getLsCpuInfo,
                            self.getNetworkInfo,
                            self.getNetworkInterfaces,
                            self.getVirtInfo,
                            self.getPlatformSpecificInfo]
        # try each hardware method, and try/except around, since
        # these tend to be fragile
        for hardware_method in hardware_methods:
            try:
                hardware_method()
            except Exception, e:
                log.warn("Hardware detection failed: %s" % e)

        #we need to know the DMI info and VirtInfo before determining UUID.
        #Thus, we can't figure it out within the main data collection loop.
        if self.allhw['virt.is_guest']:
            self._getVirtUUID()

        import dmidecode
        dmiwarnings = dmidecode.get_warnings()
        if dmiwarnings:
            log.warn(_("Error reading system DMI information: %s"), dmiwarnings)
            dmidecode.clear_warnings()
        return self.allhw


if __name__ == '__main__':
    for hkey, hvalue in Hardware().getAll().items():
        print "'%s' : '%s'" % (hkey, hvalue)
