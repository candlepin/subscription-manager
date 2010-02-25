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

# This thing gets the hardware configuraion out of a system
"""Used to read hardware info from kudzu, /proc, etc"""
from socket import gethostname
from socket import gethostbyname
import socket
import re
import os
import sys
import string
import config

import ethtool
import gettext
_ = gettext.gettext

import dmidecode

# Some systems don't have the _locale module installed
try:
    import locale
except ImportError:
    locale = None


def read_cpuinfo():
    def get_entry(a, entry):
        e = string.lower(entry)
        if not a.has_key(e):
            return ""
        return a[e]

    if not os.access("/proc/cpuinfo", os.R_OK):
        return {}

    if locale:
        locale.setlocale(locale.LC_NUMERIC, "C")

    cpulist = open("/proc/cpuinfo", "r").read()
    hwdict = { "cpu.desc" : "Processor",
               }
    hwdict['cpu.platform'] = string.lower(os.uname()[4])

    count = 0
    tmpdict = {}
    for cpu in string.split(cpulist, "\n\n"):
        if not len(cpu):
            continue
        count = count + 1
        if count > 1:
            continue # just count the rest
        for cpu_attr in string.split(cpu, "\n"):
            if not len(cpu_attr):
                continue
            vals = string.split(cpu_attr, ":")
            if len(vals) != 2:
                # XXX: make at least some effort to recover this data...
                continue
            name, value = string.strip(vals[0]), string.strip(vals[1])
            tmpdict[string.lower(name)] = value

    hwdict['cpu.count']         = count
    hwdict['cpu.type']          = get_entry(tmpdict, 'vendor_id')
    hwdict['cpu.model']         = get_entry(tmpdict, 'model name')
    hwdict['cpu.cpu_family']  = get_entry(tmpdict, 'cpu family')
    hwdict['cpu.model_ver']     = get_entry(tmpdict, 'model')
    hwdict['cpu.model_rev']     = get_entry(tmpdict, 'stepping')
    hwdict['cpu.cache']         = get_entry(tmpdict, 'cache size')
    hwdict['cpu.bogomips']      = get_entry(tmpdict, 'bogomips')
    hwdict['cpu.other']         = get_entry(tmpdict, 'flags')
    mhz_speed               = get_entry(tmpdict, 'cpu mhz')

    # Arch based info
        

    return hwdict

def read_memory():
    parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB' )
    memdict = {}
    for info in open('/proc/meminfo'):
        match = parser.match(info)
        if not match:
            continue
        key, value = match.groups(['key', 'value'])
        memdict["memory."+key] = int(value)

    return memdict

def read_dmi():
    dmidict = {}
    dmidict["class"] = "DMI" 

    for k in dmidict.keys()[:]:
        if dmidict[k] is None:
            del dmidict[k]
    return dmidict

def get_virt_info():
    """
    This function returns the UUID and virtualization type of this system, if
    it is a guest.  Otherwise, it returns None.  To figure this out, we'll
    use a number of heuristics (list in order of precedence):

       1.  Check /proc/xen/xsd_port.  If exists, we know the system is a
           host; exit.
       2.  Check /sys/hypervisor/uuid.  If exists and is non-zero, we know
           the system is a para-virt guest; exit.
       3.  Check SMBIOS.  If vendor='Xen' and UUID is non-zero, we know the
           system is a fully-virt guest; exit.
       4.  If non of the above checks worked; we know we have a
           non-xen-enabled system; exit. 
    """

    # First, check whether /proc/xen/xsd_port exists.  If so, we know this is
    # a host system.
    try:
        if os.path.exists("/proc/xen/xsd_port"):
            # Ok, we know this is *at least* a host system.  However, it may
            # also be a fully-virt guest.  Check for that next.  If it is, we'll
            # just report that instead since we only support one level of 
            # virtualization.
            (uuid, virt_type) = get_fully_virt_info()
            return (uuid, virt_type)
    except IOError:
        # Failed.  Move on to next strategy.
        pass

    # This is not a virt host system.  Check if it's a para-virt guest.
    (uuid, virt_type) = get_para_virt_info()
    if uuid is not None:
        return (uuid, virt_type)
        
    # This is not a para-virt guest.  Check if it's a fully-virt guest.
    (uuid, virt_type) = get_fully_virt_info()
    if uuid is not None:
        return (uuid, virt_type)

    # If we got here, we have a system that does not have virtualization
    # enabled.
    return (None, None)

def get_para_virt_info():
    """
    This function checks /sys/hypervisor/uuid to see if the system is a 
    para-virt guest.  It returns a (uuid, virt_type) tuple.
    """
    try:
        uuid_file = open('/sys/hypervisor/uuid', 'r')
        uuid = uuid_file.read()
        uuid_file.close()
        uuid = uuid.lower().replace('-', '').rstrip("\r\n")
        virt_type = "para"
        return (uuid, virt_type)
    except IOError:
        # Failed; must not be para-virt.
        pass

    return (None, None)

def get_fully_virt_info():
    """
    This function looks in the SMBIOS area to determine if this is a 
    fully-virt guest.  It returns a (uuid, virt_type) tuple.
    """
    vendor = dmi_vendor()
    uuid = dmi_system_uuid()
    if vendor.lower() == "xen":
        uuid = uuid.lower().replace('-', '')
        virt_type = "fully"
        return (uuid, virt_type)
    else:
        return (None, None)

def _is_host_uuid(uuid):
    uuid = eval('0x%s' % uuid)
    return long(uuid) == 0L


def read_network():
    return {}

# this one reads it all
def Hardware():
    allhw = []

    try:
        ret = get_virt_info()
        if ret: allhw.append({'virt-info' : ret})
    except:
        pass
        #print _("Error reading virt info:"), sys.exc_type

    # cpu info
    try:
        ret = read_cpuinfo()
        print ret
        if ret: allhw.append(ret)
    except:
        print _("Error reading cpu information:"), sys.exc_type
        
    # memory size info
    try:
        ret = read_memory()
        if ret: allhw.append(ret)
    except:
        print _("Error reading system memory information:"), sys.exc_type
        
    # minimal networking info
    try:
        ret = read_network()
        if ret: 
            allhw.append(ret)
    except:
        pass
        #print _("Error reading networking information:"), sys.exc_type

    # minimal DMI info
    try:
        ret = read_dmi()
        if ret:
            allhw.append(ret)
    except:
        pass 
    
    return allhw

#
# Main program
#
if __name__ == '__main__':
    for hw in Hardware():
        for k in hw.keys():
            print "'%s' : '%s'" % (k, hw[k])
        print
