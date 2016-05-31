
import os

import rhsm.config

from rhsmlib.facts import hwprobe
from rhsmlib.facts import cleanup
from rhsmlib.facts import custom
from rhsmlib.facts import virt
from rhsmlib.facts import firmware_info


from rhsmlib.dbus.facts import cached_collector


class HostCollector(cached_collector.CachedFactsCollector):
    """Collect facts for a host system.

    'host' in this case means approx something running
    a single kernel image. ie, regular x86_64 hardware, a KVM
    virt guest, a ppc64 lpar guest. And not a cluster, or
    a container, or an installroot/chroot/mock, or an application,
    or a data center, or a distributed computing framework, or
    a non-linux hypervisor, etc.

    This in turns runs:
        hwprobe.Hardware()      [regular hardware facts]
        virt.VirtCollector()    [virt facts, results from virt-what etc]
        firmware_info.FirmwareCollector()  [dmiinfo, devicetree, etc]
        cleanup.CleanupCollector()  [Collapse redundant facts, alter any
                                     facts that depend on output of other facts, etc]


    Facts collected include DMI info and virt status and virt.uuid."""

    facts_sub_dir = 'facts'
    facts_glob = '*.facts'

    def get_all(self):
        host_facts = {}
        hardware_collector = hwprobe.Hardware(prefix=self.prefix,
                                              testing=self.testing,
                                              collected_hw_info=self._collected_hw_info)
        hardware_info = hardware_collector.get_all()

        virt_collector = virt.VirtCollector(prefix=self.prefix, testing=self.testing,
                                            collected_hw_info=self._collected_hw_info)

        virt_collector_info = virt_collector.get_all()

        # AdminFacts includes VirtCollector and firmware facts collection
        firmware_collector = firmware_info.FirmwareCollector(prefix=self.prefix,
                                                         testing=self.testing,
                                                         collected_hw_info=virt_collector_info)

        # rename firmware.py
        firmware_info_dict = firmware_collector.get_all()

        host_facts.update(hardware_info)
        host_facts.update(virt_collector_info)
        host_facts.update(firmware_info_dict)

        default_rhsm_dir = rhsm.config.DEFAULT_CONFIG_DIR.rstrip('/')
        custom_facts_dir = os.path.join(default_rhsm_dir, self.facts_sub_dir)
        path_and_globs = [(custom_facts_dir, self.facts_glob)]

        custom_facts = custom.CustomFactsCollector(prefix=self.prefix,
                                                   testing=self.testing,
                                                   collected_hw_info=self._collected_hw_info,
                                                   path_and_globs=path_and_globs)
        custom_facts_dict = custom_facts.get_all()
        host_facts.update(custom_facts_dict)

        # Now, munging, kluges, special cases, etc
        # NOTE: we are passing the facts we've already collected into
        # cleanup_collector.
        # FIXME: remove having to pass these args around
        cleanup_collector = cleanup.CleanupCollector(prefix=self.prefix,
                                                     testing=self.testing,
                                                     collected_hw_info=host_facts)
        cleanup_info = cleanup_collector.get_all()

        host_facts.update(cleanup_info)
        return host_facts
