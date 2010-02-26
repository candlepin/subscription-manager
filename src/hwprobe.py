#
# Copyright (c) 1999--2010 Red Hat Inc.
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
dmidict = {}

def read_memory():
    parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB' )
    memdict = {}
    meminfo = open('/proc/meminfo')
    for info in meminfo:
        match = parser.match(info)
        if not match:
            continue
        key, value = match.groups(['key', 'value'])
        memdict["memory."+key] = int(value)

    return memdict

def read_dmi():
    global dmidict
    def _get_dmi_data(func, tag, dmidict):
        for key, value in func.items():
            for key1,value1 in value['data'].items():
                dmidict[tag+key1.lower().replace(" ", "_")] = value1
        return dmidict

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

    dmidict = {}
    for tag, func in dmi_data.items():
        dmidict = _get_dmi_data(func, tag, dmidict)

    return dmidict


def get_virt_info():
    try:
        if os.path.exists("/proc/xen/xsd_port"):
            return get_fully_virt_info()
    except IOError:
        pass

    # This is not a virt host system.  Check if it's a para-virt guest.
    virtinfo = get_para_virt_info()
    if virtinfo['virt.uuid'] is not None:
        return virtinfo
        
    # This is not a para-virt guest.  Check if it's a fully-virt guest.
    virtinfo = get_fully_virt_info()
    if virtinfo['virt.uuid'] is not None:
        return virtinfo

    # If we got here, we have a system that does not have virtualization
    # enabled.
    return {'virt.type' : None, 'virt.uuid' : None}

def get_para_virt_info():
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

def get_fully_virt_info():
    vendor = dmidict["dmi.bios.vendor"]
    uuid =   dmidict["dmi.system.uuid"]
    virtinfo = {'virt.type' : None, 'virt.uuid' : None}
    if vendor.lower() == "xen":
        virtinfo['virt.uuid'] = uuid.lower().replace('-', '')
        virtinfo['virt.type'] = "fully"
    return virtinfo

def _is_host_uuid(uuid):
    uuid = eval('0x%s' % uuid)
    return long(uuid) == 0L


def read_network():
    netinfo = {}
    netinfo['network.hostname'] = gethostname()
    try:
        netinfo['network.ipaddr']   = gethostbyname(gethostname())
    except:
        netinfo['network.ipaddr'] = "127.0.0.1"

    return netinfo

class Hardware:
    def __init__(self):
        self.allhw = []
        self.dmiinfo = {}
        self.meminfo = {}
        self.cpuinfo = {}
        self.virtinfo = {}

    def getDmiInfo(self):
        try:
            self.dmiinfo = read_dmi()
        except:
            pass
        self.allhw.append(self.dmiinfo)
        return self.dmiinfo

    def getVirtInfo(self):
        try:
            self.virtinfo = get_virt_info()
        except:
            print _("Error reading virt info:"), sys.exc_type
        self.allhw.append(self.virtinfo)
        return self.virtinfo

    def getCpuInfo(self):
        return self.cpuinfo

    def getMemInfo(self):
        try:
            self.meminfo = read_memory()
        except:
            print _("Error reading system memory information:"), sys.exc_type
        self.allhw.append(self.meminfo)
        return self.meminfo

    def getNetworkInfo(self):
        try:
            self.netinfo = read_network()
        except:
            print _("Error reading networking information:"), sys.exc_type
        self.allhw.append(self.netinfo)
        return self.netinfo

    def getAll(self):
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
