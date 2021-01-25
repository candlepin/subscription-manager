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

# TODO: test Python3 syntax using flake8
# flake8: noqa

"""
This is module implementing detector and metadata collector of virtual machine running on Azure
"""

import logging

from typing import Union

from rhsmlib.cloud.detector import CloudDetector
from rhsmlib.cloud.collector import CloudCollector


log = logging.getLogger(__name__)


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


class AzureCloudCollector(CloudCollector):
    """
    Collector of Azure metadata
    """

    # Microsoft adds new API versions very often, but old versions are supported
    # for very long time. It would be good to update the version from time to time,
    # because old versions (three years) are deprecated. It would be good to update
    # the API version with every minor version of RHEL
    API_VERSION = "2020-09-01"

    CLOUD_PROVIDER_METADATA_URL = "http://169.254.169.254/metadata/instance?api-version=" + API_VERSION

    CLOUD_PROVIDER_METADATA_TYPE = "application/json"

    CLOUD_PROVIDER_SIGNATURE_URL = "http://169.254.169.254/metadata/attested/document?api-version=" + API_VERSION

    CLOUD_PROVIDER_SIGNATURE_TYPE = "application/json"

    METADATA_CACHE_FILE = None

    SIGNATURE_CACHE_FILE = None

    # HTTP header "Metadata" has to be equal to "true" to be able to get metadata
    HTTP_HEADERS = {
        'user-agent': 'RHSM/1.0',
        "Metadata": "true"
    }

    def __init__(self):
        """
        Initialization of azure cloud collector
        """
        super(AzureCloudCollector, self).__init__()

    def _get_metadata_from_cache(self) -> Union[str, None]:
        """
        It is not safe to use cache of metadata for Azure cloud provider
        :return: None
        """
        return None

    def _get_data_from_server(self, data_type, url):
        """
        This method tries to get data from server using GET method
        :param data_type: string representation of data type used in log messages (e.g. "metadata", "signature")
        :param url: URL of GET request
        :return: String of body, when request was successful; otherwise return None
        """
        return super(AzureCloudCollector, self)._get_data_from_server(data_type, url)

    def _get_metadata_from_server(self) -> Union[str, None]:
        """
        Try to get metadata from server
        :return: String with metadata or None
        """
        return super(AzureCloudCollector, self)._get_metadata_from_server()

    def _get_signature_from_cache_file(self) -> Union[str, None]:
        """
        It is not safe to use cache of signature for Azure cloud provider
        :return: None
        """
        return None

    def _get_signature_from_server(self) -> Union[str, None]:
        """
        Method for gathering signature of metadata from server
        :return: String containing signature or None
        """
        return super(AzureCloudCollector, self)._get_signature_from_server()

    def get_signature(self) -> Union[str, None]:
        """
        Public method for getting signature (cache file or server)
        :return: String containing signature or None
        """
        return super(AzureCloudCollector, self).get_signature()

    def get_metadata(self) -> Union[str, None]:
        """
        Public method for getting metadata (cache file or server)
        :return: String containing metadata or None
        """
        return super(AzureCloudCollector, self).get_metadata()


def _smoke_tests():
    """
    Simple smoke test of azure detector and collector
    :return: None
    """
    # Gather only information about hardware and virtualization
    from rhsmlib.facts.host_collector import HostCollector
    from rhsmlib.facts.hwprobe import HardwareCollector

    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    facts = {}
    facts.update(HostCollector().get_all())
    facts.update(HardwareCollector().get_all())
    azure_cloud_detector = AzureCloudDetector(facts)
    result = azure_cloud_detector.is_running_on_cloud()
    probability = azure_cloud_detector.is_likely_running_on_cloud()
    print('>>> debug <<< result: %s, %6.3f' % (result, probability))

    if result is True:
        azure_cloud_collector = AzureCloudCollector()
        metadata = azure_cloud_collector.get_metadata()
        signature = azure_cloud_collector.get_signature()
        print(f'>>> debug <<< metadata: {metadata}')
        print(f'>>> debug <<< signature: {signature}')


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src:./syspurpose/src python3 -m rhsmlib.cloud.providers.azure
if __name__ == '__main__':
    _smoke_tests()
