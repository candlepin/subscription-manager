# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Red Hat, Inc.
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

"""
This is module implementing detector and metadata collector of virtual machine running on Azure
"""

from rhsmlib.cloud.detector import CloudDetector


class AzureCloudDetector(CloudDetector):
    """
    Detector of cloud machine
    """

    ID = 'azure'

    def __init__(self, hw_info):
        """
        Initialize instance of AzureCloudDetector
        """
        super(AzureCloudDetector, self).__init__(hw_info)

    def is_vm(self):
        """
        Is system running on virtual machine or not
        :return: True, when machine is running on VM; otherwise return False
        """
        return super(AzureCloudDetector, self).is_vm()

    def is_running_on_cloud(self):
        """
        Try to guess if cloud provider is Azure using collected hardware information (output of dmidecode,
        virt-what, etc.)
        :return: True, when we detected sign of Azure in hardware information; Otherwise return False
        """

        # The system has to be VM
        if self.is_vm() is False:
            return False
        # This is valid for virtual machines running on Azure
        if 'dmi.chassis.asset_tag' in self.hw_info and \
                self.hw_info['dmi.chassis.asset_tag'] == '7783-7084-3265-9085-8269-3286-77':
            return True
        # In other cases return False
        return False

    def is_likely_running_on_cloud(self):
        """
        Return non-zero value, when the machine is virtual machine and it is running on Hyper-V and
        some Microsoft string can be found in output of dmidecode
        :return: Float value representing probability that vm is running on Azure
        """
        probability = 0.0

        # When the machine is not virtual machine, then there is probably zero chance that the machine
        # is running on Azure
        if self.is_vm() is False:
            return 0.0

        # We know that Azure uses only HyperV
        if 'virt.host_type' in self.hw_info:
            if 'hyperv' in self.hw_info['virt.host_type']:
                probability += 0.3

        # Try to find "Azure" or "Microsoft" keywords in output of dmidecode
        found_microsoft = False
        found_azure = False
        for hw_item in self.hw_info.values():
            if type(hw_item) != str:
                continue
            if 'microsoft' in hw_item.lower():
                found_microsoft = True
            elif 'azure' in hw_item.lower():
                found_azure = True
        if found_microsoft is True:
            probability += 0.3
        if found_azure is True:
            probability += 0.1

        return probability


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src:./syspurse/src python3 -m rhsmlib.cloud.providers.azure
if __name__ == '__main__':
    # Gather only information about hardware and virtualization
    from rhsmlib.facts.host_collector import HostCollector
    from rhsmlib.facts.hwprobe import HardwareCollector
    _facts = {}
    _facts.update(HostCollector().get_all())
    _facts.update(HardwareCollector().get_all())
    _azure_cloud_detector = AzureCloudDetector(_facts)
    _result = _azure_cloud_detector.is_running_on_cloud()
    _probability = _azure_cloud_detector.is_likely_running_on_cloud()
    print('>>> debug <<< result: %s, %6.3f' % (_result, _probability))
