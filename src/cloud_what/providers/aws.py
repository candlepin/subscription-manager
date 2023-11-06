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
This is module implementing detector and metadata collector of virtual machine running on AWS
"""

import requests
import logging
import time
import os

from typing import Union, Any

from cloud_what._base_provider import BaseCloudProvider


log = logging.getLogger(__name__)

# Instance from one region will be redirected to another region's CDS for content
REDIRECT_MAP = {
    "us-gov-west-1": "us-west-2",
    "us-gov-east-1": "us-east-2",
}


class AWSCloudProvider(BaseCloudProvider):
    """
    Base class for AWS cloud provider
    """

    CLOUD_PROVIDER_ID = "aws"

    CLOUD_PROVIDER_METADATA_URL = "http://169.254.169.254/latest/dynamic/instance-identity/document"

    CLOUD_PROVIDER_METADATA_TYPE = "application/json"

    CLOUD_PROVIDER_TOKEN_URL = "http://169.254.169.254/latest/api/token"

    CLOUD_PROVIDER_TOKEN_TTL = 3600  # the value is in seconds

    CLOUD_PROVIDER_SIGNATURE_URL = "http://169.254.169.254/latest/dynamic/instance-identity/rsa2048"

    CLOUD_PROVIDER_SIGNATURE_TYPE = "text/plain"

    TOKEN_CACHE_FILE = "/var/cache/cloud-what/aws_token.json"

    HTTP_HEADERS = {
        "User-Agent": "cloud-what/1.0",
    }

    def __init__(self, hw_info):
        """
        Initialize instance of AWSCloudDetector
        """
        super(AWSCloudProvider, self).__init__(hw_info)

    def is_running_on_cloud(self) -> bool:
        """
        Try to guess if cloud provider is AWS using collected hardware information (output of dmidecode,
        virt-what, etc.)
        :return: True, when we detected sign of AWS in hardware information; Otherwise return False
        """

        # The system has to be VM
        if self.is_vm() is False:
            return False
        # This is valid for AWS systems using Xen
        if "dmi.bios.version" in self.hw_info and "amazon" in self.hw_info["dmi.bios.version"]:
            return True
        # This is valid for AWS systems using KVM
        if "dmi.bios.vendor" in self.hw_info and "Amazon EC2" in self.hw_info["dmi.bios.vendor"]:
            return True
        # Try to get output from virt-what
        if "virt.host_type" in self.hw_info and "aws" in self.hw_info["virt.host_type"]:
            return True
        # In other cases return False
        return False

    def is_likely_running_on_cloud(self) -> float:
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
        if "virt.host_type" in self.hw_info:
            # It seems that KVM is used more often
            if "kvm" in self.hw_info["virt.host_type"]:
                probability += 0.3
            elif "xen" in self.hw_info["virt.host_type"]:
                probability += 0.2

        # Every system UUID of VM running on AWS EC2 starts with EC2 string. Not strong sign, but
        # it can increase probability a little
        if "dmi.system.uuid" in self.hw_info and self.hw_info["dmi.system.uuid"].lower().startswith("ec2"):
            probability += 0.1

        # Try to find "Amazon EC2", "Amazon" or "AWS" keywords in output of dmidecode
        found_amazon = False
        found_amazon_ec2 = False
        found_aws = False
        for hw_item in self.hw_info.values():
            if not (type(hw_item) is str):
                continue
            if "amazon ec2" in hw_item.lower():
                found_amazon_ec2 = True
            elif "amazon" in hw_item.lower():
                found_amazon = True
            elif "aws" in hw_item.lower():
                found_aws = True
        if found_amazon_ec2 is True:
            probability += 0.3
        if found_amazon is True:
            probability += 0.2
        if found_aws is True:
            probability += 0.1

        return probability

    @staticmethod
    def fix_rhui_url_template(repo: Any, region: str) -> None:
        """
        Try to fix URL of RHUI repository on AWS
        :param repo: DNF object of repository
        :param region: string representing region
        :return: None
        """
        if region in REDIRECT_MAP:
            region = REDIRECT_MAP[region]

        if repo.baseurl:
            repo.baseurl = tuple(url.replace("REGION", region, 1) for url in repo.baseurl)
        elif repo.mirrorlist:
            repo.mirrorlist = repo.mirrorlist.replace("REGION", region, 1)
        else:
            raise ValueError(f"RHUI repository {repo.name} does not have any url")

    @staticmethod
    def rhui_repos(base: Any) -> Any:
        """
        Generator of RHUI repositories. Could be used e.g. in for loop
        :param base: DNF base
        :return: Yields RHUI repositories
        """
        for repo_name, repo in base.repos.items():
            # TODO: we need more reliable mechanism for detection of RHUI repository, because
            # CDN provides some repositories containing 'rhui-' in the repository name too.
            if "rhui-" in repo_name:
                yield repo

    def _get_metadata_from_cache(self) -> None:
        """
        This cloud collector does not allow to use cache for metadata
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
        log.debug(f"Requesting AWS token from {self.CLOUD_PROVIDER_TOKEN_URL}")

        headers = {
            "X-aws-ec2-metadata-token-ttl-seconds": str(self.CLOUD_PROVIDER_TOKEN_TTL),
            **self.HTTP_HEADERS,
        }

        http_req = requests.Request(method="PUT", url=self.CLOUD_PROVIDER_TOKEN_URL, headers=headers)
        prepared_http_req = self._session.prepare_request(http_req)
        if os.environ.get("SUBMAN_DEBUG_PRINT_REQUEST", ""):
            self._debug_print_http_request(prepared_http_req)

        try:
            response = self._session.send(prepared_http_req, timeout=self.TIMEOUT)
        except requests.ConnectionError as err:
            log.error(f"Unable to receive token from AWS: {err}")
        else:
            if response.status_code == 200:
                self._token = response.text
                self._token_ctime = time.time()
                self._token_ttl = self.CLOUD_PROVIDER_TOKEN_TTL
                self._write_token_to_cache_file()
                return response.text
            else:
                log.error(f"Unable to receive token from AWS; status code: {response.status_code}")
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
        log.debug(f"Trying to get AWS metadata from {self.CLOUD_PROVIDER_METADATA_URL} using IMDSv1")

        self._cached_metadata = self._get_data_from_server(
            data_type="metadata",
            url=self.CLOUD_PROVIDER_METADATA_URL,
        )
        if self._cached_metadata is not None:
            self._cached_metadata_ctime = time.time()
        return self._cached_metadata

    def _get_metadata_from_server_imds_v2(self) -> Union[str, None]:
        """
        Try to get metadata from server using IMDSv2
        :return: String with metadata or None
        """
        log.debug(f"Trying to get AWS metadata from {self.CLOUD_PROVIDER_METADATA_URL} using IMDSv2")

        token = self._get_token()
        if token is None:
            return None

        headers = {
            "X-aws-ec2-metadata-token": token,
            **self.HTTP_HEADERS,
        }

        self._cached_metadata = self._get_data_from_server(
            data_type="metadata",
            url=self.CLOUD_PROVIDER_METADATA_URL,
            headers=headers,
        )

        if self._cached_metadata is not None:
            self._cached_metadata_ctime = time.time()
        return self._cached_metadata

    def _get_metadata_from_server(self) -> Union[str, None]:
        """
        Try to get metadata from server as described in these documents:
        - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
        - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-v2-how-it-works.html

        IMDSv2 requires two HTTP requests (first requests a token, second obtains the metadata).
        If that fails, try to fall back to IDMSv1 (which is older and can be disabled in the AWS console).

        :return: String with metadata or None
        """
        metadata = self._get_metadata_from_server_imds_v2()
        if metadata is not None:
            return metadata

        return self._get_metadata_from_server_imds_v1()

    def _get_signature_from_cache_file(self) -> None:
        """
        This cloud collector does not allow to use cache for signature
        :return: None
        """
        return None

    def _get_signature_from_server_imds_v1(self) -> Union[str, None]:
        """
        Try to get signature using IMDSv1
        :return: String of signature or None, when it wasn't possible to get signature from server
        """
        log.debug(f"Trying to get AWS signature from {self.CLOUD_PROVIDER_SIGNATURE_URL} using IMDSv1")

        return self._get_data_from_server(data_type="signature", url=self.CLOUD_PROVIDER_SIGNATURE_URL)

    def _get_signature_from_server_imds_v2(self) -> Union[str, None]:
        """
        Try to get signature using IMDSv2
        :return: String of signature or None, when it wasn't possible to get signature from server
        """
        log.debug(f"Trying to get AWS signature from {self.CLOUD_PROVIDER_SIGNATURE_URL} using IMDSv2")

        token = self._get_token()
        if token is None:
            return None

        headers = {"X-aws-ec2-metadata-token": token, **self.HTTP_HEADERS}

        return self._get_data_from_server(
            data_type="signature", url=self.CLOUD_PROVIDER_SIGNATURE_URL, headers=headers
        )

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
            signature = f"-----BEGIN PKCS7-----\n{signature}\n-----END PKCS7-----"

        # Save signature in in-memory cache
        if signature is not None:
            self._cached_signature = signature
            self._cached_signature_ctime = time.time()

        return signature

    def get_metadata(self) -> Union[str, None]:
        """
        Try to get metadata from the in-memory cache first. When the in-memory
        cache is not valid, then try to get metadata from server.
        :return: String with metadata or None
        """
        return super(AWSCloudProvider, self).get_metadata()

    def get_signature(self) -> Union[str, None]:
        """
        Try to get signature from the in-memory cache first. When the in-memory
        cache is not valid, then try to get signature from server.
        :return: String with metadata or None
        """
        return super(AWSCloudProvider, self).get_signature()


def _smoke_tests():
    """
    Simple smoke tests of AWS detector and collector
    :return: None
    """
    # Gather only information about hardware and virtualization
    from rhsmlib.facts.host_collector import HostCollector
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    facts = {}
    facts.update(HostCollector().get_all())
    aws_cloud_provider = AWSCloudProvider(facts)
    result = aws_cloud_provider.is_running_on_cloud()
    probability = aws_cloud_provider.is_likely_running_on_cloud()
    print(f">>> debug <<< cloud provider: {result}, probability: {probability}")

    if result is True:
        metadata = aws_cloud_provider.get_metadata()
        print(f">>> debug <<< cloud metadata: {metadata}")
        signature = aws_cloud_provider.get_signature()
        print(f">>> debug <<< metadata signature: {signature}")

        metadata_v2 = aws_cloud_provider._get_metadata_from_server_imds_v2()
        print(f">>> debug <<< cloud metadata: {metadata_v2}")
        signature_v2 = aws_cloud_provider._get_signature_from_server_imds_v2()
        print(f">>> debug <<< cloud signature: {signature_v2}")


# Some temporary smoke testing code. You can test this module using:
# sudo PYTHONPATH=./src python3 -m cloud_what.providers.aws
if __name__ == "__main__":
    _smoke_tests()
