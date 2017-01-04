# Copyright (c) 2016 Red Hat, Inc.
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

import rhsm.config

from rhsmlib.facts import hwprobe
from rhsmlib.facts import cleanup
from rhsmlib.facts import custom
from rhsmlib.facts import virt
from rhsmlib.facts import firmware_info


from rhsmlib.facts import collector


class HostCollector(collector.FactsCollector):
    """Collect facts for a host system.

    'host' in this case means approx something running
    a single kernel image. ie, regular x86_64 hardware, a KVM
    virt guest, a ppc64 lpar guest. And not a cluster, or
    a container, or an installroot/chroot/mock, or an application,
    or a data center, or a distributed computing framework, or
    a non-linux hypervisor, etc.

    This in turns runs:
        hwprobe.HardwareCollector()      [regular hardware facts]
        virt.VirtCollector()    [virt facts, results from virt-what etc]
        firmware_info.FirmwareCollector()  [dmiinfo, devicetree, etc]
        cleanup.CleanupCollector()  [Collapse redundant facts, alter any
                                     facts that depend on output of other facts, etc]


    Facts collected include DMI info and virt status and virt.uuid."""

    facts_sub_dir = 'facts'
    facts_glob = '*.facts'

    def get_all(self):
        host_facts = {}
        hardware_collector = hwprobe.HardwareCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=self._collected_hw_info
        )
        hardware_info = hardware_collector.get_all()

        virt_collector = virt.VirtCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=self._collected_hw_info
        )

        virt_collector_info = virt_collector.get_all()

        firmware_collector = firmware_info.FirmwareCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=virt_collector_info
        )

        # rename firmware.py
        firmware_info_dict = firmware_collector.get_all()

        host_facts.update(hardware_info)
        host_facts.update(virt_collector_info)
        host_facts.update(firmware_info_dict)

        default_rhsm_dir = rhsm.config.DEFAULT_CONFIG_DIR.rstrip('/')
        custom_facts_dir = os.path.join(default_rhsm_dir, self.facts_sub_dir)
        path_and_globs = [(custom_facts_dir, self.facts_glob)]

        custom_facts = custom.CustomFactsCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=self._collected_hw_info,
            path_and_globs=path_and_globs
        )
        custom_facts_dict = custom_facts.get_all()
        host_facts.update(custom_facts_dict)

        # Now, munging, kluges, special cases, etc
        # NOTE: we are passing the facts we've already collected into
        # cleanup_collector.
        cleanup_collector = cleanup.CleanupCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=host_facts
        )
        cleanup_info = cleanup_collector.get_all()

        host_facts.update(cleanup_info)
        return host_facts
