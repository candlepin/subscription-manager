from __future__ import print_function, division, absolute_import

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

import locale
import logging

from rhsmlib.facts import cleanup
from rhsmlib.facts import virt
from rhsmlib.facts import firmware_info
from rhsmlib.facts import collector

log = logging.getLogger(__name__)


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

    def get_all(self):
        host_facts = {}

        firmware_collector = firmware_info.FirmwareCollector(
            prefix=self.prefix,
            testing=self.testing,
        )
        firmware_info_dict = firmware_collector.get_all()

        virt_collector = virt.VirtCollector(
            prefix=self.prefix,
            testing=self.testing,
            collected_hw_info=firmware_info_dict
        )
        virt_collector_info = virt_collector.get_all()

        host_facts.update(virt_collector_info)
        host_facts.update(firmware_info_dict)

        locale_info = {}
        effective_locale = 'Unknown'
        # When there is no locale set (system variable LANG is unset),
        # then this is value returned by locale.getdefaultlocale()
        # Tuple contains: (language[_territory], encoding identifier)
        default_locale = (None, None)
        try:
            default_locale = locale.getdefaultlocale()
        except ValueError as err:
            log.warning("Unable to get default locale (bad environment variable?): %s" % err)
        if default_locale[0] is not None:
            effective_locale = ".".join([_f for _f in default_locale if _f])
        locale_info['system.default_locale'] = effective_locale
        host_facts.update(locale_info)

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
