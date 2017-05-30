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
import logging

from rhsmlib.facts import collector

log = logging.getLogger(__name__)


class CleanupCollector(collector.FactsCollector):
    no_uuid_platforms = ['powervm_lx86', 'xen-dom0', 'ibm_systemz']

    def get_all(self):
        cleanup_facts = {}
        dmi_socket_info = self.replace_socket_count_with_dmi()
        cleanup_facts.update(dmi_socket_info)
        return cleanup_facts

    def explain_lack_of_virt_uuid(self):
        # No virt.uuid equiv is available for guests on these hypervisors
        #virt_is_guest = self._collected_hw_info['virt.is_guest']
        if not self._is_a_virt_host_type_with_virt_uuids():
            log.debug("we don't sell virt uuids here")

    def _is_a_virt_host_type_with_virt_uuids(self):
        virt_host_type = self._collected_hw_info['virt.host_type']
        for no_uuid_platform in self.no_uuid_platforms:
            if virt_host_type.find(no_uuid_platform) > -1:
                return False
        return True

    def replace_socket_count_with_dmi(self):
        cleanup_info = {}
        # cpu topology reporting on xen dom0 machines is wrong. So
        # if we are a xen dom0, and we found socket info in dmiinfo,
        # replace our normal cpu socket calculation with the dmiinfo one
        # we have to do it after the virt data and cpu data collection
        if 'virt.host_type' not in self._collected_hw_info:
            return cleanup_info

        if not self._host_is_xen_dom0():
            return cleanup_info

        if 'dmi.meta.cpu_socket_count' not in self._collected_hw_info:
            return cleanup_info

        # Alright, lets munge up cpu socket info based on the dmi info.
        socket_count = int(self._collected_hw_info['dmi.meta.cpu_socket_count'])
        cleanup_info['cpu.cpu_socket(s)'] = socket_count

        if 'cpu.cpu(s)' not in self._collected_hw_info:
            return cleanup_info

        # And the cores per socket count as well
        dmi_cpu_cores_per_cpu = int(self._collected_hw_info['cpu.cpu(s)']) // socket_count
        cleanup_info['cpu.core(s)_per_socket'] = dmi_cpu_cores_per_cpu

        return cleanup_info

    def _host_is_xen_dom0(self):
        return self._collected_hw_info['virt.host_type'].find('dom0') > -1
