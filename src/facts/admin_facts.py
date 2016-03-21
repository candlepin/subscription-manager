#
# Probe hardware info that requires root
#
# Copyright (c) 2010-2016 Red Hat, Inc.
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

import gettext
import logging
import subprocess

from rhsm.facts import hwprobe
from rhsm.facts import firmware_info

log = logging.getLogger(__name__)

_ = gettext.gettext


# TODO/FIXME: This can go away, or at the very least, move
#             to a utility module
def get_output(cmd):
    log.debug("Running '%s'" % cmd)
    process = subprocess.Popen([cmd],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    (std_output, std_error) = process.communicate()

    log.debug("%s stdout: %s" % (cmd, std_output))
    log.debug("%s stderr: %s" % (cmd, std_error))

    output = std_output.strip()

    returncode = process.poll()
    if returncode:
        raise CalledProcessError(returncode, cmd,
                                 output=output)

    return output


# FIXME: ditto, move or remove
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


class AdminFacts(object):
    """Collect facts that require elevated privs (ie, root).

    hwprobe.Hardware() can be invoked as a user, but this class
    will need to run as root or equilivent.

    Facts collected include DMI info and virt status and virt.uuid."""

    def __init__(self, prefix=None, testing=None):
        self.allhw = {}
        self.arch = hwprobe.get_arch()
        self.prefix = prefix or ''
        self.testing = testing or False

        # Note: unlike system uuid in DMI info, the virt.uuid is
        # available to non-root users on ppc64*
        # ppc64 LPAR has it's virt.uuid in /proc/devicetree
        # so parts of this don't need to be in AdminHardware
        self.devicetree_vm_uuid_arches = ['ppc64', 'ppc64le']

        self.hardware_methods = [self.get_firmware_info,
                                 self.get_virt_info,
                                 self.get_virt_uuid]

    def get_all(self):

        # try each hardware method, and try/except around, since
        # these tend to be fragile
        for hardware_method in self.hardware_methods:
            try:
                hardware_method()
            except Exception, e:
                log.exception(e)
                raise
                log.warn("%s" % hardware_method)
                log.warn("Hardware detection failed: %s" % e)

        log.info("collected virt facts: virt.is_guest=%s, virt.host_type=%s, virt.uuid=%s",
                 self.allhw.get('virt.is_guest', 'Not Set'),
                 self.allhw.get('virt.host_type', 'Not Set'),
                 self.allhw.get('virt.uuid', 'Not Set'))

        return self.allhw

    def get_firmware_info(self):
        """Read and parse data that comes from platform specific interfaces.

        This is only dmi/smbios data for now (which isn't on ppc/s390).
        """
        firmware_info_provider = firmware_info.get_firmware_provider(arch=self.arch,
                                                                     prefix=self.prefix,
                                                                     testing=self.testing)

        # Pass in collected hardware so DMI etc can potentially override it
        firmware_info_dict = firmware_info_provider.get_info(all_hwinfo=self.allhw)

        # This can potentially overrite facts that already existed in self.allhw
        # (and is supposed to).
        self.allhw.update(firmware_info_dict)

    # NOTE/TODO/FIXME: Not all platforms require admin privs to determine virt type or uuid
    def get_virt_info(self):
        virt_dict = {}

        try:
            host_type = get_output('virt-what')
            # BZ1018807 xen can report xen and xen-hvm.
            # Force a single line
            host_type = ", ".join(host_type.splitlines())

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
                    # FIXME: better exception class
                    raise Exception(_("Virtualization platform does not support UUIDs"))
        except Exception, e:
            log.warn(_("Error finding UUID: %s"), e)
            return  # nothing more to do

        # most virt platforms record UUID via DMI/SMBIOS info.
        # But only for guests, otherwise it's physical system uuid.
        if self.allhw.get('virt.is_guest') and 'dmi.system.uuid' in self.allhw:
            self.allhw['virt.uuid'] = self.allhw['dmi.system.uuid']

        # For ppc64, virt uuid is in /proc/device-tree/vm,uuid
        # just the uuid in txt, one line

        # ie, ppc64/ppc64le
        if self.arch in self.devicetree_vm_uuid_arches:
            self.allhw.update(self._get_devicetree_vm_uuid())

        # potentially override DMI-determined UUID with
        # what is on the file system (xen para-virt)
        # Does this need root access?
        try:
            uuid_file = open('/sys/hypervisor/uuid', 'r')
            uuid = uuid_file.read()
            uuid_file.close()
            self.allhw['virt.uuid'] = uuid.rstrip("\r\n")
        except IOError:
            pass

    def _get_devicetree_vm_uuid(self):
        """Collect the virt.uuid fact from device-tree/vm,uuid

        For ppc64/ppc64le systems running KVM or PowerKVM, the
        virt uuid is found in /proc/device-tree/vm,uuid.

        (In contrast to use of DMI on x86_64)."""

        virt_dict = {}

        vm_uuid_path = "%s/proc/device-tree/vm,uuid" % self.prefix

        try:
            with open(vm_uuid_path) as fo:
                contents = fo.read()
                vm_uuid = contents.strip()
                virt_dict['virt.uuid'] = vm_uuid
        except IOError, e:
            log.warn("Tried to read %s but there was an error: %s", vm_uuid_path, e)

        return virt_dict
