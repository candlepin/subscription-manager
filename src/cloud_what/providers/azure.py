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

import logging
import json

from cloud_what._base_provider import BaseCloudProvider


log = logging.getLogger(__name__)


class AzureCloudProvider(BaseCloudProvider):
    """
    Base class for Azure cloud provider
    """

    CLOUD_PROVIDER_ID = "azure"

    # Microsoft adds new API versions very often, but old versions are supported
    # for very long time. It would be good to update the version from time to time,
    # because old versions (three years) are deprecated. It would be good to update
    # the API version with every minor version of RHEL
    API_VERSION = "2021-02-01"

    BASE_CLOUD_PROVIDER_METADATA_URL = "http://169.254.169.254/metadata/instance?api-version="

    CLOUD_PROVIDER_METADATA_URL = BASE_CLOUD_PROVIDER_METADATA_URL + API_VERSION

    CLOUD_PROVIDER_METADATA_TYPE = "application/json"

    BASE_CLOUD_PROVIDER_SIGNATURE_URL = "http://169.254.169.254/metadata/attested/document?api-version="

    CLOUD_PROVIDER_SIGNATURE_URL = BASE_CLOUD_PROVIDER_SIGNATURE_URL + API_VERSION

    CLOUD_PROVIDER_SIGNATURE_TYPE = "application/json"

    AZURE_API_VERSIONS_URL = "http://169.254.169.254/metadata/versions"

    METADATA_CACHE_FILE = None

    SIGNATURE_CACHE_FILE = None

    # HTTP header "Metadata" has to be equal to "true" to be able to get metadata
    HTTP_HEADERS = {
        'User-Agent': 'cloud-what/1.0',
        "Metadata": "true"
    }

    # Increased timeout for Azure, because response can have long delay, when wrong
    # or too old API_VERSION is used.
    TIMEOUT = 10.0

    def __init__(self, hw_info):
        """
        Initialize instance of AzureCloudDetector
        """
        super(AzureCloudProvider, self).__init__(hw_info)

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

        if 'dmi.chassis.asset_tag' in self.hw_info and \
                self.hw_info['dmi.chassis.asset_tag'] == '7783-7084-3265-9085-8269-3286-77':
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

    def get_api_versions(self):
        """
        This method tries to get list of API versions currently supported by Azure cloud provider
        :return: list of API versions or None
        """
        api_versions_str = self._get_data_from_server("api_versions", self.AZURE_API_VERSIONS_URL)
        api_versions = None
        try:
            api_versions_dict = json.loads(api_versions_str)
        except TypeError as err:
            log.error('Unable to decode Azure API versions: {}'.format(err))
        else:
            if 'apiVersions' in api_versions_dict:
                api_versions = api_versions_dict['apiVersions']
        return api_versions

    def _fix_supported_api_version(self):
        """
        Try to get list of supported API versions and set the oldest
        :return:
        """
        api_versions = self.get_api_versions()
        if api_versions is not None and len(api_versions) > 0:
            if self.API_VERSION not in api_versions:
                log.warning(
                    'Current Azure IMDS API version {} not included in the list of '
                    'supported API versions: {}'.format(self.API_VERSION, api_versions)
                )
            else:
                log.warning('Current Azure IMDS API version {} not fully supported'.format(self.API_VERSION))
            # Get newest version
            api_version = api_versions[-1]
            log.warning('Changing Azure IMDS API version to: {}'.format(api_version))
            self.API_VERSION = api_version
            # Fix URL for gathering metadata and signature
            self.CLOUD_PROVIDER_METADATA_URL = self.BASE_CLOUD_PROVIDER_METADATA_URL + api_version
            self.CLOUD_PROVIDER_SIGNATURE_URL = self.BASE_CLOUD_PROVIDER_SIGNATURE_URL + api_version
            return api_version
        return None

    def _get_metadata_from_cache(self):
        """
        It is not safe to use cache of metadata for Azure cloud provider
        :return: None
        """
        return None

    def _get_data_from_server(self, data_type, url, headers=None):
        """
        This method tries to get data from server using GET method
        :param data_type: string representation of data type used in log messages (e.g. "metadata", "signature")
        :param url: URL of GET request
        :return: String of body, when request was successful; otherwise return None
        """
        return super(AzureCloudProvider, self)._get_data_from_server(data_type, url, headers)

    def _get_metadata_from_server(self, headers=None):
        """
        Try to get metadata from server
        :return: String with metadata or None
        """
        metadata = super(AzureCloudProvider, self)._get_metadata_from_server(headers)
        # When it wasn't possible to get metadata with current API version, then try to get list of
        # supported API versions and select the newest version and try to get metadata once again
        if metadata is None:
            api_version = self._fix_supported_api_version()
            if api_version is not None:
                metadata = super(AzureCloudProvider, self)._get_metadata_from_server(headers)
        return metadata

    def _get_signature_from_cache_file(self):
        """
        It is not safe to use cache of signature for Azure cloud provider
        :return: None
        """
        return None

    def _get_signature_from_server(self):
        """
        Method for gathering signature of metadata from server
        :return: String containing signature or None
        """
        signature = super(AzureCloudProvider, self)._get_signature_from_server()
        if signature is None:
            api_version = self._fix_supported_api_version()
            if api_version is not None:
                signature = super(AzureCloudProvider, self)._get_signature_from_server()
        return signature

    def get_signature(self):
        """
        Public method for getting signature (cache file or server)
        :return: String containing signature or None
        """
        return super(AzureCloudProvider, self).get_signature()

    def get_metadata(self):
        """
        Public method for getting metadata (cache file or server)
        :return: String containing metadata or None
        """
        return super(AzureCloudProvider, self).get_metadata()


def _smoke_tests():
    """
    Simple smoke test of azure detector and collector
    :return: None
    """
    # Gather only information about hardware and virtualization
    from rhsmlib.facts.host_collector import HostCollector

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
    azure_cloud_provider = AzureCloudProvider(facts)
    result = azure_cloud_provider.is_running_on_cloud()
    probability = azure_cloud_provider.is_likely_running_on_cloud()
    print('>>> debug <<< result: %s, %6.3f' % (result, probability))

    if result is True:
        metadata = azure_cloud_provider.get_metadata()
        signature = azure_cloud_provider.get_signature()
        print('>>> debug <<< metadata: {}'.format(metadata))
        print('>>> debug <<< signature: {}'.format(signature))
        api_versions = azure_cloud_provider.get_api_versions()
        print('>>> debug <<< api_versions: {}'.format(api_versions))

        # Test getting metadata and signature with too old API version
        AzureCloudProvider.API_VERSION = '2011-01-01'
        AzureCloudProvider.CLOUD_PROVIDER_METADATA_URL = \
            "http://169.254.169.254/metadata/instance?api-version=2011-01-01"
        AzureCloudProvider.CLOUD_PROVIDER_SIGNATURE_URL = \
            "http://169.254.169.254/metadata/attested/document?api-version=2011-01-01"
        azure_cloud_provider = AzureCloudProvider({})
        azure_cloud_provider._cached_metadata = None
        azure_cloud_provider._cached_signature = None
        metadata = azure_cloud_provider.get_metadata()
        print('>>> debug <<< metadata: {}'.format(metadata))
        signature = azure_cloud_provider.get_signature()
        print('>>> debug <<< signature: {}'.format(signature))


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python3 -m cloud_what.providers.azure
if __name__ == '__main__':
    _smoke_tests()
