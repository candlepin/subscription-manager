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
import re
import gettext
_ = gettext.gettext
import dmidecode
import ethtool
import socket
import commands

import subprocess
from subprocess import CalledProcessError

class Hardware:

    def __init__(self):
        self.allhw = {}
        self.dmiinfo = {}

    def getUnameInfo(self):

        uname_data = os.uname()
        uname_keys = ('uname.sysname', 'uname.nodename', 'uname.release',
                      'uname.version', 'uname.machine')
        self.unameinfo = dict(zip(uname_keys, uname_data))
        self.allhw.update(self.unameinfo)
        return self.unameinfo

    def getReleaseInfo(self):
        import platform
        distro_data = platform.linux_distribution()
        distro_keys = ('distribution.name', 'distribution.version',
                       'distribution.id')
        self.releaseinfo = dict(zip(distro_keys, distro_data))
        self.allhw.update(self.releaseinfo)
        return self.releaseinfo

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

    def getCpuInfo(self):
        # TODO:(prad) Revisit this and see if theres a better way to parse /proc/cpuinfo
        # perhaps across all arches
        self.cpuinfo = {}
        try:
            cpudata = commands.getstatusoutput('LANG=en_US.UTF-8 /usr/bin/lscpu')[-1].split('\n')
            for info in cpudata:
                key, value = info.split(":")
                nkey = '.'.join(["cpu", key.lower().strip().replace(" ", "_")])
                self.cpuinfo[nkey] = "%s" % value.strip()
        except:
            print _("Error reading system cpu information:"), sys.exc_type
        self.allhw.update(self.cpuinfo)
        return self.cpuinfo

    def getDmiInfo(self):
        try:
            dmi_data = {
                "dmi.bios.": dmidecode.bios(),
                "dmi.processor.": dmidecode.processor(),
                "dmi.baseboard.": dmidecode.baseboard(),
                "dmi.chassis.": dmidecode.chassis(),
                "dmi.slot.": dmidecode.slot(),
                "dmi.system.": dmidecode.system(),
                "dmi.memory.": dmidecode.memory(),
                "dmi.connector.": dmidecode.connector(),
            }

            for tag, func in dmi_data.items():
                self.dmiinfo = self._get_dmi_data(func, tag, self.dmiinfo)
        except:
            print _("Error reading system DMI information:"), sys.exc_type
        self.allhw.update(self.dmiinfo)
        return self.dmiinfo

    def _get_dmi_data(self, func, tag, ddict):
        for key, value in func.items():
            for key1, value1 in value['data'].items():
                if not isinstance(value1, str):
                    continue
                nkey = ''.join([tag, key1.lower()]).replace(" ", "_")
                ddict[nkey] = str(value1)

        return ddict

    def getNetworkInfo(self):
        self.netinfo = {}
        try:
            self.netinfo['network.hostname'] = socket.gethostname()
            try:
                self.netinfo['network.ipaddr'] = socket.gethostbyname(self.netinfo['network.hostname'])
            except:
                self.netinfo['network.ipaddr'] = "127.0.0.1"
        except:
            print _("Error reading networking information:"), sys.exc_type
        self.allhw.update(self.netinfo)
        return self.netinfo

    def getNetworkInterfaces(self):
        netinfdict = {}
        metakeys = ['hwaddr', 'ipaddr', 'netmask', 'broadcast']
        try:
            for interface in ethtool.get_devices():
                for mkey in metakeys:
                    key = '.'.join(['net.interface', interface, mkey])
                    try:
                        netinfdict[key] = getattr(
                                            ethtool, 'get_' + mkey)(interface)
                    except:
                        netinfdict[key] = "unknown"
        except:
            print _("Error reading net Interface information:"), sys.exc_type
        self.allhw.update(netinfdict)
        return netinfdict

    def getVirtInfo(self):
        virt_dict = {}

        try:
            host_type = subprocess.check_output('virt-what').strip()
            virt_dict['virt.host_type'] = host_type

            # If this is blank, then not a guest
            virt_dict['virt.is_guest'] = bool(host_type)
        except CalledProcessError:
            # Otherwise there was an error running virt-what - who knows
            virt_dict['virt.is_guest'] = 'Unknown'

        self.allhw.update(virt_dict)
        return virt_dict

    def getAll(self):
        self.getUnameInfo()
        self.getReleaseInfo()
        self.getDmiInfo()
        self.getMemInfo()
        self.getCpuInfo()
        self.getNetworkInfo()
        self.getNetworkInterfaces()
        self.getVirtInfo()
        return self.allhw

if __name__ == '__main__':
    for hkey, hvalue in Hardware().getAll().items():
        print "'%s' : '%s'" % (hkey, hvalue)

