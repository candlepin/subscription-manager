#!/usr/bin/python
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
from socket import gethostname,gethostbyname
import gettext
_ = gettext.gettext

import dmidecode

class Hardware:
    def __init__(self):
        self.allhw = []
        self.dmiinfo = {}

    def getUnameInfo(self):
        
        uname_data = os.uname()
        uname_keys = ('uname.sysname', 'uname.nodename', 'uname.release', 
                      'uname.version', 'uname.machine')
        self.unameinfo = dict(zip(uname_keys, uname_data))
        self.allhw.append(self.unameinfo)
        return self.unameinfo

    def getReleaseInfo(self):
        import platform
        distro_data = platform.linux_distribution()
        distro_keys = ('distribution.name','distribution.version', 
                       'distribution.id')
        self.releaseinfo = dict(zip(distro_keys, distro_data))
        self.allhw.append(self.releaseinfo)
        return self.releaseinfo

    def getMemInfo(self):
        self.meminfo = {}
        try:
            parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB' )
            memdata = open('/proc/meminfo')
            for info in memdata:
                match = parser.match(info)
                if not match:
                    continue
                key, value = match.groups(['key', 'value'])
                self.meminfo["memory."+key.lower().replace(" ", "_")] = \
                                   int(value)
        except:
            print _("Error reading system memory information:"), sys.exc_type
        self.allhw.append(self.meminfo)
        return self.meminfo

    def getDmiInfo(self):
        try:
            dmi_data = { 
                "dmi.bios." : dmidecode.bios(),
                "dmi.processor." : dmidecode.processor(),
                "dmi.baseboard." : dmidecode.baseboard(),
                "dmi.chassis." : dmidecode.chassis(),
                "dmi.slot."  : dmidecode.slot(),
                "dmi.system." : dmidecode.system(),
                "dmi.memory." : dmidecode.memory(),
                "dmi.connector." : dmidecode.connector(),
            }

            for tag, func in dmi_data.items():
                self.dmiinfo = self._get_dmi_data(func, tag, self.dmiinfo)
        except:
            print _("Error reading system DMI information:"), sys.exc_type
        self.allhw.append(self.dmiinfo)
        return self.dmiinfo

    def _get_dmi_data(self, func, tag, ddict):
        for key, value in func.items():
            for key1, value1 in value['data'].items():
                ddict[tag+key1.lower().replace(" ", "_")] = value1
        return ddict

    def getVirtInfo(self):
        self.virtinfo = {'virt.type' : None, 'virt.uuid' : None}
        try:
            if os.path.exists("/proc/xen/xsd_port"):
                self.virtinfo = self._get_fully_virt_info()

            # Check if it's a para virt guest
            if not self.virtinfo:
                self.virtinfo = get_para_virt_info()
        
            # This is not a para-virt guest.Check if it's a fully-virt guest.
            if not self.virtinfo:
                self.virtinfo = get_fully_virt_info()
        except:
            print _("Error reading virt info:"), sys.exc_type
        self.allhw.append(self.virtinfo)
        return self.virtinfo

    def _get_para_virt_info(self):
        virtinfo = {'virt.type' : None, 'virt.uuid' : None}
        try:
            uuid_file = open('/sys/hypervisor/uuid', 'r')
            uuid = uuid_file.read()
            uuid_file.close()
            virtinfo['virt.uuid'] = uuid.lower().replace('-', '').rstrip("\r\n")
            virtinfo['virt.type'] = "para"
            return virtinfo
        except IOError:
            # Failed; must not be para-virt.
            pass
        return virtinfo

    def _get_fully_virt_info(self):
        virtinfo = {'virt.type' : None, 'virt.uuid' : None}
        if not self.dmiinfo:
            self.getDmiInfo()
        vendor = self.dmiinfo["dmi.bios.vendor"]
        uuid =   self.dmiinfo["dmi.system.uuid"]
        if vendor.lower() == "xen":
            virtinfo['virt.uuid'] = uuid.lower().replace('-', '')
            virtinfo['virt.type'] = "fully"
        return virtinfo

    def getCpuInfo(self):
        return {}

    def getNetworkInfo(self):
        self.netinfo = {}
        try:
            self.netinfo['network.hostname'] = gethostname()
            try:
                self.netinfo['network.ipaddr']   = gethostbyname(gethostname())
            except:
                self.netinfo['network.ipaddr'] = "127.0.0.1"
        except:
            print _("Error reading networking information:"), sys.exc_type
        self.allhw.append(self.netinfo)
        return self.netinfo

    def getAll(self):
        self.getUnameInfo()
        self.getReleaseInfo()
        self.getDmiInfo()
        self.getVirtInfo()
        self.getCpuInfo()
        self.getMemInfo()
        self.getNetworkInfo()
        return self.allhw

if __name__ == '__main__':
    for hw in Hardware().getAll():
        for k in hw.keys():
            print "'%s' : '%s'" % (k, hw[k])
        print
