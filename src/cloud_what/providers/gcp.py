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
This is module implementing detector and metadata collector of virtual machine running on Google Cloud Platform
"""

import logging
import time
import base64

from cloud_what._base_provider import BaseCloudProvider


log = logging.getLogger(__name__)


class GCPCloudProvider(BaseCloudProvider):
    """
    Class for GCP cloud provider

    Collector of Google Cloud Platform metadata. Verification of instance identity is described in this document:

    https://cloud.google.com/compute/docs/instances/verifying-instance-identity
    """

    CLOUD_PROVIDER_ID = "gcp"

    # The "audience" should be some unique URI agreed upon by both the instance and the system verifying
    # the instance's identity. For example, the audience could be a URL for the connection between the two systems.
    # In fact this string could be anything.
    # TODO: use some more generic URL here and move setting this RHSM specific URL to subscription-manager
    AUDIENCE = "https://subscription.rhsm.redhat.com:443/subscription"

    # Google uses little bit different approach. It provides everything in JSON Web Token (JWT)
    CLOUD_PROVIDER_METADATA_URL = None

    CLOUD_PROVIDER_METADATA_URL_TEMPLATE = "http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}&format=full&licenses=TRUE"

    # Token (metadata) expires within one hour. Thus it is save to cache the token.
    CLOUD_PROVIDER_METADATA_TTL = 3600

    CLOUD_PROVIDER_TOKEN_TTL = CLOUD_PROVIDER_METADATA_TTL

    CLOUD_PROVIDER_METADATA_TYPE = "text/html"

    CLOUD_PROVIDER_SIGNATURE_URL = None

    CLOUD_PROVIDER_SIGNATURE_TYPE = None

    HTTP_HEADERS = {
        'User-Agent': 'cloud-what/1.0',
        'Metadata-Flavor': 'Google'
    }

    # Metadata are provided in JWT token and this token is valid for one hour.
    # Thus it is save to cache this token (see CLOUD_PROVIDER_METADATA_TTL,
    # self._metadata_token_ctime and self._metadata_token)
    TOKEN_CACHE_FILE = "/var/cache/cloud-what/gcp_token.json"

    # Nothing to cache for this cloud provider
    SIGNATURE_CACHE_FILE = None

    def __init__(self, hw_info, audience_url=None):
        """
        Initialize instance of GCPCloudDetector
        """
        super(GCPCloudProvider, self).__init__(hw_info)

        # Metadata URL can have default or custom "audience"
        if audience_url is not None:
            self.CLOUD_PROVIDER_METADATA_URL = self.CLOUD_PROVIDER_METADATA_URL_TEMPLATE.format(
                audience=audience_url
            )
        else:
            self.CLOUD_PROVIDER_METADATA_URL = self.CLOUD_PROVIDER_METADATA_URL_TEMPLATE.format(
                audience=self.AUDIENCE
            )

    def is_running_on_cloud(self):
        """
        Try to guess if cloud provider is GCP using collected hardware information (output of dmidecode,
        virt-what, etc.)
        :return: True, when we detected sign of GCP in hardware information; Otherwise return False
        """

        # The system has to be VM
        if self.is_vm() is False:
            return False
        # This is valid for virtual machines running on Google Cloud Platform
        if 'dmi.bios.vendor' in self.hw_info and \
                'google' in self.hw_info['dmi.bios.vendor'].lower():
            return True
        # In other cases return False
        return False

    def is_likely_running_on_cloud(self):
        """
        Return non-zero value, when the machine is virtual machine and it is running on kvm and
        some google string can be found in output of dmidecode
        :return: Float value representing probability that vm is running on GPC
        """
        probability = 0.0

        # When the machine is not virtual machine, then there is probably zero chance that the machine
        # is running on GPC
        if self.is_vm() is False:
            return 0.0

        # We know that GCP uses only KVM at the end of 2020
        if 'virt.host_type' in self.hw_info and 'kvm' in self.hw_info['virt.host_type']:
            probability += 0.3

        # Try to find "Google" or "gcp" keywords in output of dmidecode
        found_google = False
        found_gcp = False
        for hw_item in self.hw_info.values():
            if type(hw_item) != str:
                continue
            if 'google' in hw_item.lower():
                found_google = True
            elif 'gcp' in hw_item.lower():
                found_gcp = True
        if found_google is True:
            probability += 0.3
        if found_gcp is True:
            probability += 0.1

        return probability

    def _get_metadata_from_cache(self):
        """
        Try to get metadata (JWT token) from the cache file
        :return: String with cached token or None
        """
        return super(GCPCloudProvider, self)._get_token_from_cache_file()

    def _get_data_from_server(self, data_type, url, headers=None):
        """
        Try to get data from metadata server
        """
        return super(GCPCloudProvider, self)._get_data_from_server(data_type, url, headers)

    def _get_metadata_from_server(self, headers=None):
        """
        GCP metadata server returns only one file called token
        :return: String with token or None
        """
        token = self._get_data_from_server(data_type="token", url=self.CLOUD_PROVIDER_METADATA_URL)
        if token is not None:
            self._token = token
            self._token_ctime = time.time()
            self._token_ttl = self.CLOUD_PROVIDER_TOKEN_TTL
            self._write_token_to_cache_file()
        return token

    def _get_signature_from_server(self):
        """
        Google returns everything in one file.
        """
        return None

    def _get_signature_from_cache_file(self):
        """
        Really no need to cache signature
        """
        return None

    def get_signature(self):
        """
        Google returns everything in one file. No need to try to get signature.
        :return Empty string
        """
        return ""

    def get_metadata(self):
        """
        Try to get metadata from in-memory cache, cache or cloud provider server
        :return: String with metadata or None
        """
        if self._is_in_memory_cached_token_valid() is True:
            return self._token
        return super(GCPCloudProvider, self).get_metadata()

    def set_audience(self, audience):
        """
        Set audience unique identifier (usually some URL). This ID is used in HTTP request
        to GCP IMDS server
        :param audience: unique identifier
        :return: None
        """
        self.AUDIENCE = audience

    @staticmethod
    def decode_jwt(jwt_token):
        """
        Try to decode metadata stored in JWT token described in this RFC: https://tools.ietf.org/html/rfc7519
        :param jwt_token: string representing JWT token
        :return: tuple with: string representing header, string representing metadata and base64 encoded signature
        """
        # Get the actual payload part: [0] is JOSE header, [1] is metadata and [2] is signature
        parts = jwt_token.split('.')
        if len(parts) >= 3:
            encoded_jose_header = parts[0]
            encoded_metadata = parts[1]
            encoded_signature = parts[2]
            # Add some extra padding, JWT tokens have padding trimmed - see https://stackoverflow.com/a/49459036
            encoded_jose_header += '==='
            encoded_metadata += '==='
            encoded_signature += '==='
            # Decode only header and metadata, not signature
            try:
                jose_header = base64.b64decode(encoded_jose_header).decode('utf-8')
            except UnicodeDecodeError as err:
                log.error('Unable to decode JWT JOSE header: {}'.format(err))
                jose_header = None
            try:
                metadata = base64.b64decode(encoded_metadata).decode('utf-8')
            except UnicodeDecodeError as err:
                log.error('Unable to decode JWT metadata: {}'.format(err))
                metadata = None
            return jose_header, metadata, encoded_signature
        else:
            log.warning('JWT token with wrong format')
            return None, None, None


# Note about GCP token
# --------------------
#
# It is possible to verify token, but is not easy to do it on RHEL, because it requires
# special Python packages that are not available on RHEL. It is recommended to create
# virtual environment:
#
# $ python3 -m venv env
#
# Activate virtual environment:
#
# $ source env/bin/activate
#
# Install required packages:
#
# $ pip install --upgrade google-auth
# $ pip install requests
#
# Run following Python script:
#
# ```python
# from cloud_what.providers.gcp import GCPCloudCollector
# # Import libraries for token verification
# import google.auth.transport.requests
# from google.oauth2 import id_token
# # Get token
# token = GCPCloudCollector().get_metadata()
# # Verify token signature and store the token payload
# request = google.auth.transport.requests.Request()
# payload = id_token.verify_token(token, request=request, audience=GCPCloudCollector.AUDIENCE)
# print(payload)
# ```


def _smoke_test():
    """
    Simple smoke tests of GCP detector and collector
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
    gcp_cloud_provider = GCPCloudProvider(facts)
    result = gcp_cloud_provider.is_running_on_cloud()
    probability = gcp_cloud_provider.is_likely_running_on_cloud()
    print('>>> debug <<< result: %s, %6.3f' % (result, probability))
    if result is True:
        # 1. using default audience
        token = gcp_cloud_provider.get_metadata()
        print('>>> debug <<< 1. token: {}'.format(token))
        jose, metadata, signature = gcp_cloud_provider.decode_jwt(token)
        print('>>> jose header: {jose}'.format(jose=jose))
        print('>>> metadata: {metadata}'.format(metadata=metadata))
        print('>>> signature: {signature}'.format(signature=signature))
        # 2. using some custom audience
        gcp_cloud_provider = GCPCloudProvider(facts, audience_url="https://localhost:8443/candlepin")
        token = gcp_cloud_provider.get_metadata()
        print('>>> debug <<< 2. token: {}'.format(token))


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python -m cloud_what.providers.gcp
if __name__ == '__main__':
    _smoke_test()
