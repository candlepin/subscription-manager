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
This is module implementing detector and metadata collector of virtual machine running on AWS
"""

import requests
import logging
import time
import os

from typing import Union

from rhsmlib.cloud.detector import CloudDetector
from rhsmlib.cloud.collector import CloudCollector


log = logging.getLogger(__name__)


class AWSCloudDetector(CloudDetector):
    """
    Detector of cloud machine
    """

    ID = 'aws'

    def __init__(self, hw_info):
        """
        Initialize instance of AWSCloudDetector
        """
        super(AWSCloudDetector, self).__init__(hw_info)

    def is_vm(self):
        """
        Is system running on virtual machine or not
        :return: True, when machine is running on VM; otherwise return False
        """
        return super(AWSCloudDetector, self).is_vm()

    def is_running_on_cloud(self):
        """
        Try to guess if cloud provider is AWS using collected hardware information (output of dmidecode,
        virt-what, etc.)
        :return: True, when we detected sign of AWS in hardware information; Otherwise return False
        """

        # The system has to be VM
        if self.is_vm() is False:
            return False
        # This is valid for AWS systems using Xen
        if 'dmi.bios.version' in self.hw_info and 'amazon' in self.hw_info['dmi.bios.version']:
            return True
        # This is valid for AWS systems using KVM
        if 'dmi.bios.vendor' in self.hw_info and 'Amazon EC2' in self.hw_info['dmi.bios.vendor']:
            return True
        # Try to get output from virt-what
        if 'virt.host_type' in self.hw_info and 'aws' in self.hw_info['virt.host_type']:
            return True
        # In other cases return False
        return False

    def is_likely_running_on_cloud(self):
        """
        Return non-zero value, when the machine is virtual machine and it is running on kvm/xen and
        some Amazon string can be found in output of dmidecode
        :return: Float value representing probability that vm is running on AWS
        """
        probability = 0.0

        # When the machine is not virtual machine, then there is probably zero chance that the machine
        # is running on AWS
        if self.is_vm() is False:
            return 0.0

        # We know that AWS uses mostly KVM and it uses Xen in some cases
        if 'virt.host_type' in self.hw_info:
            # It seems that KVM is used more often
            if 'kvm' in self.hw_info['virt.host_type']:
                probability += 0.3
            elif 'xen' in self.hw_info['virt.host_type']:
                probability += 0.2

        # Every system UUID of VM running on AWS EC2 starts with EC2 string. Not strong sign, but
        # it can increase probability a little
        if 'dmi.system.uuid' in self.hw_info and self.hw_info['dmi.system.uuid'].lower().startswith('ec2'):
            probability += 0.1

        # Try to find "Amazon EC2", "Amazon" or "AWS" keywords in output of dmidecode
        found_amazon = False
        found_amazon_ec2 = False
        found_aws = False
        for hw_item in self.hw_info.values():
            if type(hw_item) != str:
                continue
            if 'amazon ec2' in hw_item.lower():
                found_amazon_ec2 = True
            elif 'amazon' in hw_item.lower():
                found_amazon = True
            elif 'aws' in hw_item.lower():
                found_aws = True
        if found_amazon_ec2 is True:
            probability += 0.3
        if found_amazon is True:
            probability += 0.2
        if found_aws is True:
            probability += 0.1

        return probability


class AWSCloudCollector(CloudCollector):
    """
    Class implementing collecting metadata from AWS cloud provider
    """

    CLOUD_PROVIDER_ID = "aws"

    CLOUD_PROVIDER_METADATA_URL = "http://169.254.169.254/latest/dynamic/instance-identity/document"

    CLOUD_PROVIDER_METADATA_TYPE = "application/json"

    CLOUD_PROVIDER_TOKEN_URL = "http://169.254.169.254/latest/api/token"

    CLOUD_PROVIDER_TOKEN_TTL = 3600  # the value is in seconds

    CLOUD_PROVIDER_SIGNATURE_URL = "http://169.254.169.254/latest/dynamic/instance-identity/rsa2048"

    CLOUD_PROVIDER_SIGNATURE_TYPE = "text/plain"

    COLLECTOR_CONF_FILE = "/etc/rhsm/cloud/providers/aws.conf"

    TOKEN_CACHE_FILE = "/var/lib/rhsm/cache/aws_token.json"

    HTTP_HEADERS = {
        'user-agent': 'RHSM/1.0'
    }

    def __init__(self):
        """
        Initialize instance of AWSCloudCollector
        """
        super(AWSCloudCollector, self).__init__()

    def _get_metadata_from_cache(self) -> None:
        """
        This cloud collector does not use cache for metadata
        :return: None
        """
        return None

    def _get_token_from_server(self) -> Union[str, None]:
        """
        Try to get token from server as it is described in this document:

        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html

        When a token is received from server, then the token is also written
        to the cache file.

        :return: String of token or None, when it wasn't possible to get the token
        """
        log.debug(f'Requesting AWS token from {self.CLOUD_PROVIDER_TOKEN_URL}')

        headers = {
            'X-aws-ec2-metadata-token-ttl-seconds': str(self.CLOUD_PROVIDER_TOKEN_TTL),
            **self.HTTP_HEADERS
        }
        try:
            response = requests.put(self.CLOUD_PROVIDER_TOKEN_URL, headers=headers)
        except requests.ConnectionError as err:
            log.error(f'Unable to receive token from AWS: {err}')
        else:
            if response.status_code == 200:
                self._token = response.text
                self._token_ctime = time.time()
                self._token_ttl = self.CLOUD_PROVIDER_TOKEN_TTL
                self._write_token_to_cache_file()
                return response.text
            else:
                log.error(f'Unable to receive token from AWS; status code: {response.status_code}')
        return None

    def _token_exists(self) -> bool:
        """
        Check if security token exists and IMDSv2 should be used?
        :return: True, when token exists; otherwise return False.
        """
        if os.path.exists(self.TOKEN_CACHE_FILE):
            return True
        else:
            return False

    def _get_token(self) -> Union[str, None]:
        """
        Try to get the token from in-memory cache. When in-memory cache is not valid, then
        try to get the token from cache file and when cache file is not valid, then finally
        try to get the token from AWS server
        :return: String with the token or None
        """
        if self._is_in_memory_cached_token_valid() is True:
            token = self._token
        else:
            token = self._get_token_from_cache_file()
            if token is None:
                token = self._get_token_from_server()
        return token

    def _get_metadata_from_server_imds_v1(self) -> Union[str, None]:
        """
        Try to get metadata from server using IMDSv1
        :return: String with metadata or None
        """
        log.debug(f'Trying to get metadata from {self.CLOUD_PROVIDER_METADATA_URL} using IMDSv1')

        try:
            response = requests.get(self.CLOUD_PROVIDER_METADATA_URL, headers=self.HTTP_HEADERS)
        except requests.ConnectionError as err:
            log.debug(f'Unable to get AWS metadata using IMDSv1: {err}')
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.debug(f'Unable to get AWS metadata using IMDSv1: {response.status_code}')

    def _get_metadata_from_server_imds_v2(self) -> Union[str, None]:
        """
        Try to get metadata from server using IMDSv2
        :return: String with metadata or None
        """
        log.debug(f'Trying to get metadata from {self.CLOUD_PROVIDER_METADATA_URL} using IMDSv2')

        token = self._get_token()
        if token is None:
            return None

        headers = {
            'X-aws-ec2-metadata-token': token,
            **self.HTTP_HEADERS
        }
        try:
            response = requests.get(self.CLOUD_PROVIDER_METADATA_URL, headers=headers)
        except requests.ConnectionError as err:
            log.error(f'Unable to get AWS metadata using IMDSv2: {err}')
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.error(f'Unable to get AWS metadata using IMDSv2; status code: {response.status_code}')
        return None

    def _get_metadata_from_server(self) -> Union[str, None]:
        """
        Try to get metadata from server as is described in this document:

        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html

        It is possible to use two versions. We will try to use version IMDSv1 first (this version requires
        only one HTTP request), when the usage of IMDSv1 is forbidden, then we will try to use IMDSv2 version.
        The version requires two requests (get session TOKEN and then get own metadata using token)
        :return: String with metadata or None
        """

        if self._token_exists() is False:
            # First try to get metadata using IMDSv1
            metadata = self._get_metadata_from_server_imds_v1()

            if metadata is not None:
                return metadata

        # When it wasn't possible to get metadata using IMDSv1, then try to get metadata using IMDSv2
        return self._get_metadata_from_server_imds_v2()

    def _get_signature_from_cache_file(self) -> None:
        """
        This cloud collector does not use cache for metadata
        :return: None
        """
        return None

    def _get_signature_from_server_imds_v1(self) -> Union[str, None]:
        """
        Try to get signature using IMDSv1
        :return: String of signature or None, when it wasn't possible to get signature from server
        """
        log.debug(f'Trying to get signature from {self.CLOUD_PROVIDER_SIGNATURE_URL} using IMDSv1')

        try:
            response = requests.get(self.CLOUD_PROVIDER_SIGNATURE_URL, headers=self.HTTP_HEADERS)
        except requests.ConnectionError as err:
            log.debug(f'Unable to get AWS signature using IMDSv1: {err}')
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.debug(f'Unable to get AWS signature using IMDSv1: {response.status_code}')

    def _get_signature_from_server_imds_v2(self) -> Union[str, None]:
        """
        Try to get signature using IMDSv2
        :return: String of signature or None, when it wasn't possible to get signature from server
        """
        log.debug(f'Trying to get signature from {self.CLOUD_PROVIDER_SIGNATURE_URL} using IMDSv2')

        token = self._get_token()
        if token is None:
            return None

        headers = {
            'X-aws-ec2-metadata-token': token,
            **self.HTTP_HEADERS
        }
        try:
            response = requests.get(self.CLOUD_PROVIDER_SIGNATURE_URL, headers=headers)
        except requests.ConnectionError as err:
            log.error(f'Unable to get AWS signature using IMDSv2: {err}')
        else:
            if response.status_code == 200:
                return response.text
            else:
                log.error(f'Unable to get AWS signature using IMDSv2; status code: {response.status_code}')
        return None

    def _get_signature_from_server(self) -> Union[str, None]:
        """
        Try to get signature from server as is described in this document:

        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/verify-signature.html

        AWS provides several versions signatures (PKCS7, base64-encoded and RSA-2048). We will use
        the base64-encoded one, because it is easier to send it as part of JSON document. It is
        possible to get signature using IMDSv1 and IMDSv2. We use same approach of obtaining
        signature as we use, when we try to obtain metadata. We try use IMDSv1 first, when not
        possible then we try to use IMDSv2.
        :return: String with signature or None
        """
        signature = None
        if self._token_exists() is False:
            signature = self._get_signature_from_server_imds_v1()

        if signature is None:
            signature = self._get_signature_from_server_imds_v2()

        if signature is not None:
            signature = f'-----BEGIN PKCS7-----\n{signature}\n-----END PKCS7-----'

        return signature

    def get_metadata(self) -> Union[str, None]:
        """
        Try to get metadata from the cache file first. When the cache file is not available, then try to
        get metadata from server.
        :return: String with metadata or None
        """
        return super(AWSCloudCollector, self).get_metadata()

    def get_signature(self) -> Union[str, None]:
        """
        Try to get signature from the cache file first. When the cache file is not available, then try to
        get signature from server.
        :return: String with metadata or None
        """
        return super(AWSCloudCollector, self).get_signature()


def _smoke_tests():
    """
    Simple smoke tests of AWS detector and collector
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
    aws_cloud_detector = AWSCloudDetector(facts)
    result = aws_cloud_detector.is_running_on_cloud()
    probability = aws_cloud_detector.is_likely_running_on_cloud()
    print(f'>>> debug <<< cloud provider: {result}, probability: {probability}')

    if result is True:
        metadata_collector = AWSCloudCollector()
        metadata = metadata_collector.get_metadata()
        print(f'>>> debug <<< cloud metadata: {metadata}')
        signature = metadata_collector.get_signature()
        print(f'>>> debug <<< metadata signature: {signature}')

        metadata_v2 = metadata_collector._get_metadata_from_server_imds_v2()
        print(f'>>> debug <<< cloud metadata: {metadata_v2}')
        signature_v2 = metadata_collector._get_signature_from_server_imds_v2()
        print(f'>>> debug <<< cloud signature: {signature_v2}')


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src:./syspurpose/src python3 -m rhsmlib.cloud.providers.aws
if __name__ == '__main__':
    _smoke_tests()
