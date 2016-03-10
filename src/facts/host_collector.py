from rhsm.facts import collector
from rhsm.facts import hwprobe
from rhsm.facts import cleanup
from rhsm.facts import virt
from rhsm.facts import firmware_info


class HostCollector(collector.CachedFactsCollector):
    """Collect facts for a host system.

    'host' in this case means approx something running
    a single kernel image. ie, regular x86_64 hardware, a KVM
    virt guest, a ppc64 lpar guest. And not a cluster, or
    a container, or an installroot/chroot/mock, or an application,
    or a data center, or a distributed computing framework, or
    a non-linux hypervisor, etc.

    This in turns runs hwprobe.Hardware() [regular hardware facts]
    and admin_facts.AdminFacts() [info that needs elevated perms to
    access, including virt.uuid].


    Facts collected include DMI info and virt status and virt.uuid."""

    def __init__(self, prefix=None, testing=None, collected_hw_info=None):
        super(HostCollector, self).__init__(prefix=prefix, testing=testing,
                                         collected_hw_info=collected_hw_info)

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
