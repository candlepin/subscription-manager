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
Module for testing Python all modules from Python package rhsmlib.cloud
"""

import unittest
from mock import patch, Mock
import tempfile
import time
import base64
import json

from rhsmlib.cloud.providers import aws, azure, gcp
from rhsmlib.cloud.provider import detect_cloud_provider, collect_cloud_info, get_cloud_provider


def get_only_imds_v2_is_supported(url, headers, *args, **kwargs):
    """
    Mock result, when we try to get metadata using GET method against
    AWS metadata provider. This mock is for the case, when only IMDSv2
    is supported by instance.
    :param url: URL
    :param headers: HTTP headers
    :param args: other position argument
    :param kwargs: other keyed argument
    :return: Mock with result
    """
    if 'X-aws-ec2-metadata-token' in headers.keys():
        if headers['X-aws-ec2-metadata-token'] == AWS_TOKEN:
            if url == aws.AWSCloudProvider.CLOUD_PROVIDER_METADATA_URL:
                mock_result = Mock()
                mock_result.status_code = 200
                mock_result.text = AWS_METADATA
            elif url == aws.AWSCloudProvider.CLOUD_PROVIDER_SIGNATURE_URL:
                mock_result = Mock()
                mock_result.status_code = 200
                mock_result.text = AWS_SIGNATURE
            else:
                mock_result = Mock()
                mock_result.status_code = 400
                mock_result.text = 'Error: Invalid URL'
        else:
            mock_result = Mock()
            mock_result.status_code = 400
            mock_result.text = 'Error: Invalid metadata token provided'
    else:
        mock_result = Mock()
        mock_result.status_code = 400
        mock_result.text = 'Error: IMDSv1 is not supported on this instance'
    return mock_result


def put_imds_v2_token(url, headers, *args, **kwargs):
    """
    Mock getting metadata token using PUT method against AWS metadata provider
    :param url: URL
    :param headers: HTTP header
    :param args: other position arguments
    :param kwargs: other keyed arguments
    :return: Mock with response
    """
    if url == aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_URL:
        if 'X-aws-ec2-metadata-token-ttl-seconds' in headers:
            mock_result = Mock()
            mock_result.status_code = 200
            mock_result.text = AWS_TOKEN
        else:
            mock_result = Mock()
            mock_result.status_code = 400
            mock_result.text = 'Error: TTL for token not specified'
    else:
        mock_result = Mock()
        mock_result.status_code = 400
        mock_result.text = 'Error: Invalid URL'
    return mock_result


AWS_METADATA = """
{
  "accountId" : "012345678900",
  "architecture" : "x86_64",
  "availabilityZone" : "eu-central-1b",
  "billingProducts" : [ "bp-0124abcd", "bp-63a5400a" ],
  "devpayProductCodes" : null,
  "marketplaceProductCodes" : null,
  "imageId" : "ami-0123456789abcdeff",
  "instanceId" : "i-abcdef01234567890",
  "instanceType" : "m5.large",
  "kernelId" : null,
  "pendingTime" : "2020-02-02T02:02:02Z",
  "privateIp" : "12.34.56.78",
  "ramdiskId" : null,
  "region" : "eu-central-1",
  "version" : "2017-09-30"
}
"""

AWS_SIGNATURE = """ABCDEFGHIJKLMNOPQRSTVWXYZabcdefghijklmnopqrstvwxyz01234567899w0BBwGggCSABIIB
73sKICAiYWNjb3VudElkIiA6ICI1NjcwMTQ3ODY4OTAiLAogICJhcmNoaXRlY3R1cmUiIDogIng4
Nl82NCIsCiAgImF2YWlsYWJpbGl0eVpvbmUiIDogImV1LWNlbnRyYWwtMWIiLAogICJiaWxsaW5n
UHJvZHVjdHMiIDogWyAiYnAtNmZhNTQwMDYiIF0sCiAgImRldnBheVByb2R1Y3RDb2RlcyIgOiBu
73sKICAiYWNjb3VudElkIiA6ICI1NjcwMTQ3ODY4OTAiLAogICJhcmNoaXRlY3R1cmUiIDogIng4
bWktMDgxNmFkNzYyOTc2YzM1ZGIiLAogICJpbnN0YW5jZUlkIiA6ICJpLTBkNTU0YzRmM2JhNWVl
YTczIiwKICAiaW5zdGFuY2VUeXBlIiA6ICJtNS5sYXJnZSIsCiAgImtlcm5lbElkIiA6IG51bGws
CiAgInBlbmRpbmdUaW1lIiA6ICIyMDIwLTA0LTI0VDE0OjU3OjQzWiIsCiAgInByaXZhdGVJcCIg
OiAiMTcyLjMxLjExLjc4IiwKICAicmFtZGlza0lkIiA6IG51bGwsCiAgInJlZ2lvbiIgOiAiZXUt
Y2VudHJhbC0xIiwKICAidmVyc2lvbiIgOiAiMjAxNy0wOS0zMCIKfQAAAAAAADGCAf8wggH7AgEB
CiAgInBlbmRpbmdUaW1lIiA6ICIyMDIwLTA0LTI0VDE0OjU3OjQzWiIsCiAgInByaXZhdGVJcCIg
YXR0bGUxIDAeBgNVBAoTF0FtYXpvbiBXZWIgU2VydmljZXMgTExDAgkAoP6/ot5H9aswDQYJYIZI
AWUDBAIBBQCgaTAYBgkqhkiG9w0BCQMxCwYJKoZIhvcNAQcBMBwGCSqGSIb3DQEJBTEPFw0yMDA5
MDExNTMyNDhaMC8GCSqGSIb3DQEJBDEiBCCmizT0hDlJmxHtDBaEjql5ZPFaoKy6OSk7qBFREVRk
iTANBgkqhkiG9w0BAQEFAASCAQAh//5+AaFAcgw/5SoglQ27kQKuThcJYa+QhC2aw4n1GvkvCmyi
helVMxH33tB9tUei/mapSF3v8jUseRLEbcDVRHf6n6h14Qj2MxtgYanzUCDF8qECYbZ2uSy3JLEP
iNsndm8nt7XcJC7NRoWJWAsly1VeXVIauA/l7uXmUarDQs5BhFYl7REX4htxg9mCibR6xqU5i8/D
iTANBgkqhkiG9w0BAQEFAASCAQAh//5+AaFAcgw/5SoglQ27kQKuThcJYa+QhC2aw4n1GvkvCmyi
tGbafapTj+6KnJAfP0sW7ZbzKclaCPHXQ37z9mc8vtCxEQmCbGL6sj2wtpi4rmRlAAAAAAAA"""

AWS_TOKEN = "ABCDEFGHIJKLMNOPQRSTVWXYZabcdefghijklmnopqrstvwxyz0123=="


class TestAWSCloudProvider(unittest.TestCase):
    """
    Class used for testing of AWS cloud provider
    """

    def setUp(self):
        """
        Patch communication with metadata provider
        """
        requests_patcher = patch('rhsmlib.cloud.providers.aws.requests')
        self.requests_mock = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

    def test_aws_cloud_provider_id(self):
        """
        Test of CLOUD_PROVIDER_ID
        """
        self.assertEqual(aws.AWSCloudProvider.CLOUD_PROVIDER_ID, "aws")
        aws_provider = aws.AWSCloudProvider({})
        self.assertEqual(aws_provider.CLOUD_PROVIDER_ID, "aws")

    def test_aws_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertFalse(is_vm)

    def test_aws_vm_using_xen(self):
        """
        Test for the case, when the vm is running on AWS Xen
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'xen',
            'dmi.bios.version': 'amazon'
        }
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_xen_vm = aws_detector.is_running_on_cloud()
        self.assertTrue(is_aws_xen_vm)

    def test_aws_vm_using_kvm(self):
        """
        Test for the case, when the vm is running on AWS KVM
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Amazon EC2'
        }
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_kvm_vm = aws_detector.is_running_on_cloud()
        self.assertTrue(is_aws_kvm_vm)

    def test_vm_not_on_aws_cloud(self):
        """
        Test for the case, when the vm is not running on AWS
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Foo'
        }
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        is_aws_vm = aws_detector.is_running_on_cloud()
        self.assertFalse(is_aws_vm)

    def test_vm_without_dmi_bios_info(self):
        """
        Test for the case, when SM BIOS does not provide any useful information for our code
        """
        # We will mock facts using simple dictionary
        facts = {}
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertFalse(is_vm)
        is_aws_vm = aws_detector.is_running_on_cloud()
        self.assertFalse(is_aws_vm)

    def test_vm_system_uuid_starts_with_ec2(self):
        """
        Test for the case, when system UUID starts with EC2 string as it is described here:
        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'dmi.system.uuid': 'EC2263F8-15F3-4A34-B186-FAD8AB963431'
        }
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        probability = aws_detector.is_likely_running_on_cloud()
        self.assertEqual(probability, 0.1)

    def test_get_metadata_from_server_imds_v1(self):
        """
        Test the case, when metadata are obtained from server using IMDSv1
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AWS_METADATA
        self.requests_mock.get = Mock(return_value=mock_result)
        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_metadata_from_cache = Mock(return_value=None)
        metadata = aws_collector.get_metadata()
        self.assertEqual(metadata, AWS_METADATA)

    def test_get_signature_from_server_imds_v1(self):
        """
        Test the case, when metadata are obtained from server using IMDSv1
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AWS_SIGNATURE
        self.requests_mock.get = Mock(return_value=mock_result)
        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_signature_from_cache = Mock(return_value=None)
        test_signature = aws_collector.get_signature()
        signature = '-----BEGIN PKCS7-----\n' + AWS_SIGNATURE + '\n-----END PKCS7-----'
        self.assertEqual(signature, test_signature)

    def test_get_metadata_from_server_imds2(self):
        """
        Test the case, when metadata are obtained from server using IMDSv2
        """
        self.requests_mock.get = get_only_imds_v2_is_supported
        self.requests_mock.put = put_imds_v2_token

        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_metadata_from_cache = Mock(return_value=None)
        # Mock that no token cache exists
        aws_collector._get_token_from_cache_file = Mock(return_value=None)
        # Mock writing token to cache file
        aws_collector._write_token_to_cache_file = Mock()

        metadata = aws_collector.get_metadata()
        self.assertEqual(metadata, AWS_METADATA)

    def test_get_signature_from_server_imds2(self):
        """
        Test the case, when signature is obtained from server using IMDSv2
        """
        self.requests_mock.get = get_only_imds_v2_is_supported
        self.requests_mock.put = put_imds_v2_token

        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_metadata_from_cache = Mock(return_value=None)
        # Mock that no token cache exists
        aws_collector._get_token_from_cache_file = Mock(return_value=None)
        # Mock writing token to cache file
        aws_collector._write_token_to_cache_file = Mock()

        test_signature = aws_collector.get_signature()
        signature = '-----BEGIN PKCS7-----\n' + AWS_SIGNATURE + '\n-----END PKCS7-----'
        self.assertEqual(signature, test_signature)

    def test_reading_valid_cached_token(self):
        """
        Test reading of valid cached token from file
        """
        c_time = str(time.time())
        ttl = str(aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL)
        token = 'ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=='
        valid_token = '{\
  "ctime": "' + c_time + '",\
  "ttl": "' + ttl + '",\
  "token": "' + token + '"\
}'
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding='utf-8'))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(token, test_token)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file

    def test_reading_invalid_cached_token_corrupted_json_file(self):
        """
        Test reading of corrupted cached token from file
        """
        c_time = str(time.time())
        ttl = str(aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL)
        token = 'ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=='
        valid_token = '{[\
  "ctime": "' + c_time + '",\
  "ttl": "' + ttl + '",\
  "token": "' + token + '"\
}]'
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding='utf-8'))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(test_token, None)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file

    def test_reading_invalid_cached_token_wrong_ctime_format(self):
        """
        Test reading of cached token from file with invalid time format
        """
        ttl = str(aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL)
        token = 'ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=='
        # ctime has to be float (unix epoch)
        valid_token = '{[\
  "ctime": "Wed Dec 16 16:31:36 CET 2020",\
  "ttl": "' + ttl + '",\
  "token": "' + token + '"\
}]'
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding='utf-8'))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(test_token, None)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file

    def test_reading_invalid_cached_token_missing_key(self):
        """
        Test reading of invalid cached token from file
        """
        valid_token = '{\
  "token": "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="\
}'
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding='utf-8'))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(test_token, None)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file

    def test_reading_timed_out_cached_token(self):
        """
        Test reading of cached token from file that is timed out
        """
        c_time = str(time.time() - aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL - 10)
        ttl = str(aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL)
        valid_token = '{\
  "ctime": "' + c_time + '",\
  "ttl": "' + ttl + '",\
  "token": "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="\
}'
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding='utf-8'))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(test_token, None)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file


AZURE_METADATA = """
{
    "compute": {
        "azEnvironment": "AzurePublicCloud",
        "customData": "",
        "location": "westeurope",
        "name": "foo-bar",
        "offer": "RHEL",
        "osType": "Linux",
        "placementGroupId": "",
        "plan": {
            "name": "",
            "product": "",
            "publisher": ""
        },
        "platformFaultDomain": "0",
        "platformUpdateDomain": "0",
        "provider": "Microsoft.Compute",
        "publicKeys": [
            {
                "keyData": "ssh-rsa SOMEpublicSSHkey user@localhost.localdomain",
                "path": "/home/user/.ssh/authorized_keys"
            }
        ],
        "publisher": "RedHat",
        "resourceGroupName": "foo-bar",
        "resourceId": "/subscriptions/01234567-0123-0123-0123-012345679abc/resourceGroups/foo-bar/providers/Microsoft.Compute/virtualMachines/foo",
        "sku": "8.1-ci",
        "storageProfile": {
            "dataDisks": [],
            "imageReference": {
                "id": "",
                "offer": "RHEL",
                "publisher": "RedHat",
                "sku": "8.1-ci",
                "version": "latest"
            },
            "osDisk": {
                "caching": "ReadWrite",
                "createOption": "FromImage",
                "diskSizeGB": "64",
                "encryptionSettings": {
                    "enabled": "false"
                },
                "image": {
                    "uri": ""
                },
                "managedDisk": {
                    "id": "/subscriptions/01234567-0123-0123-0123-012345679abc/resourceGroups/FOO-BAR/providers/Microsoft.Compute/disks/foo_OsDisk_1_b21768daf38e48c6a0db7cff1f054b03",
                    "storageAccountType": ""
                },
                "name": "FOO_OsDisk_1_b21768daf38e48c6a0db7cff1f054b03",
                "osType": "Linux",
                "vhd": {
                    "uri": ""
                },
                "writeAcceleratorEnabled": "false"
            }
        },
        "subscriptionId": "01234567-0123-0123-0123-012345679abc",
        "tags": "",
        "version": "8.1.2020042511",
        "vmId": "12345678-1234-1234-1234-123456789abc",
        "vmScaleSetName": "",
        "vmSize": "Standard_D2s_v3",
        "zone": ""
    },
    "network": {
        "interface": [
            {
                "ipv4": {
                    "ipAddress": [
                        {
                            "privateIpAddress": "172.16.2.5",
                            "publicIpAddress": "1.2.3.4"
                        }
                    ],
                    "subnet": [
                        {
                            "address": "172.16.2.0",
                            "prefix": "24"
                        }
                    ]
                },
                "ipv6": {
                    "ipAddress": []
                },
                "macAddress": "000D3A123456"
            }
        ]
    }
}
"""


AZURE_SIGNATURE = """
{"encoding":"pkcs7","signature":"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"}
"""


class TestAzureCloudProvider(unittest.TestCase):
    """
    Class used for testing of Azure cloud provider
    """

    def setUp(self):
        """
        Patch communication with metadata provider
        """
        requests_patcher = patch('rhsmlib.cloud._base_provider.requests')
        self.requests_mock = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

    def test_azure_cloud_provider_id(self):
        """
        Test of CLOUD_PROVIDER_ID
        """
        self.assertEqual(azure.AzureCloudProvider.CLOUD_PROVIDER_ID, "azure")
        azure_detector = azure.AzureCloudProvider({})
        self.assertEqual(azure_detector.CLOUD_PROVIDER_ID, "azure")

    def test_azure_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        azure_detector = azure.AzureCloudProvider(facts)
        is_vm = azure_detector.is_vm()
        self.assertFalse(is_vm)

    def test_azure_vm(self):
        """
        Test for the case, when the vm is running on Azure
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
            'dmi.bios.version': '090008',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77'
        }
        azure_detector = azure.AzureCloudProvider(facts)
        is_vm = azure_detector.is_vm()
        self.assertTrue(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertTrue(is_azure_vm)

    def test_vm_not_on_azure_cloud(self):
        """
        Test for the case, when the vm is not running on AWS
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
            'dmi.bios.version': '090008',
            'dmi.bios.vendor': 'Foo'
        }
        azure_detector = azure.AzureCloudProvider(facts)
        is_vm = azure_detector.is_vm()
        self.assertTrue(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertFalse(is_azure_vm)

    def test_vm_without_dmi_bios_info(self):
        """
        Test for the case, when MS BIOS does not provide any useful information for our code
        """
        # We will mock facts using simple dictionary
        facts = {}
        azure_detector = azure.AzureCloudProvider(facts)
        is_vm = azure_detector.is_vm()
        self.assertFalse(is_vm)
        is_azure_vm = azure_detector.is_running_on_cloud()
        self.assertFalse(is_azure_vm)

    def test_get_metadata_from_server(self):
        """
        Test getting metadata from server, when there is no cache
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AZURE_METADATA
        self.requests_mock.get = Mock(return_value=mock_result)
        azure_collector = azure.AzureCloudProvider({})
        metadata = azure_collector.get_metadata()
        self.requests_mock.get.assert_called_once_with(
            "http://169.254.169.254/metadata/instance?api-version=2020-09-01",
            headers={
                'user-agent': 'RHSM/1.0',
                "Metadata": "true"
            }
        )
        self.assertEqual(metadata, AZURE_METADATA)

    def test_get_signature_from_server(self):
        """
        Test getting signature from server, when there is no cache file
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AZURE_SIGNATURE
        self.requests_mock.get = Mock(return_value=mock_result)
        azure_collector = azure.AzureCloudProvider({})
        signature = azure_collector.get_signature()
        self.requests_mock.get.assert_called_once_with(
            "http://169.254.169.254/metadata/attested/document?api-version=2020-09-01",
            headers={
                'user-agent': 'RHSM/1.0',
                "Metadata": "true"
            }
        )
        self.assertEqual(signature, AZURE_SIGNATURE)


GCP_JWT_TOKEN = """eyJhbGciOiJSUzI1NiIsImtpZCI6IjZhOGJhNTY1MmE3MDQ0MTIxZDRmZWRhYzhmMTRkMTRjNTRlNDg5NWIiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJodHRwczovL3N1YnNjcmlwdGlvbi5yaHNtLnJlZGhhdC5jb206NDQzL3N1YnNjcmlwdGlvbiIsImF6cCI6IjEwNDA3MDk1NTY4MjI5ODczNjE0OSIsImVtYWlsIjoiMTYxOTU4NDY1NjEzLWNvbXB1dGVAZGV2ZWxvcGVyLmdzZXJ2aWNlYWNjb3VudC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZXhwIjoxNjE2NTk5ODIzLCJnb29nbGUiOnsiY29tcHV0ZV9lbmdpbmUiOnsiaW5zdGFuY2VfY3JlYXRpb25fdGltZXN0YW1wIjoxNjE2NTk1ODQ3LCJpbnN0YW5jZV9pZCI6IjI1ODkyMjExNDA2NzY3MTgwMjYiLCJpbnN0YW5jZV9uYW1lIjoiaW5zdGFuY2UtMSIsImxpY2Vuc2VfaWQiOlsiNTczMTAzNTA2NzI1NjkyNTI5OCJdLCJwcm9qZWN0X2lkIjoiZmFpci1raW5nZG9tLTMwODUxNCIsInByb2plY3RfbnVtYmVyIjoxNjE5NTg0NjU2MTMsInpvbmUiOiJ1cy1lYXN0MS1iIn19LCJpYXQiOjE2MTY1OTYyMjMsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsInN1YiI6IjEwNDA3MDk1NTY4MjI5ODczNjE0OSJ9.XQKeqMAvsH2T2wsdN97jlm52DzLfix3DTMCu9QCuhSKLEk1xHYOYtvh5Yzn7j-tbZtV-siyPAfpGZO3Id87573OVGgohN3q7Exlf9CEIHa1-X7zLyiyIlyrnfQJ1aGHeH6y7gb_tWxHFLJRzhulfkfJxSDn5fEBSgBqbjzCr9unQgMkuzQ3uui2BbIbALmOpY6D-IT71mgMDZ_zm4G6q-Mh0nIMkDWhmQ8pa3RAVqqBMBYJninKLdCD8eQzIlDhtIzwmYGLrsJMktFF3pJFCqEFv1rKZy_OUyV4JOkOLtXbKnwxqmFTq-2SP0KtUWjDy1-U8GnVDptISjOf2O9FaLA
"""

GCP_JOSE_HEADER = '{"alg":"RS256","kid":"6a8ba5652a7044121d4fedac8f14d14c54e4895b","typ":"JWT"}'

GCP_METADATA = '{"aud":"https://subscription.rhsm.redhat.com:443/subscription","azp":"104070955682298736149","email":"161958465613-compute@developer.gserviceaccount.com","email_verified":true,"exp":1616599823,"google":{"compute_engine":{"instance_creation_timestamp":1616595847,"instance_id":"2589221140676718026","instance_name":"instance-1","license_id":["5731035067256925298"],"project_id":"fair-kingdom-308514","project_number":161958465613,"zone":"us-east1-b"}},"iat":1616596223,"iss":"https://accounts.google.com","sub":"104070955682298736149"}'

GCP_SIGNATURE = """XQKeqMAvsH2T2wsdN97jlm52DzLfix3DTMCu9QCuhSKLEk1xHYOYtvh5Yzn7j-tbZtV-siyPAfpGZO3Id87573OVGgohN3q7Exlf9CEIHa1-X7zLyiyIlyrnfQJ1aGHeH6y7gb_tWxHFLJRzhulfkfJxSDn5fEBSgBqbjzCr9unQgMkuzQ3uui2BbIbALmOpY6D-IT71mgMDZ_zm4G6q-Mh0nIMkDWhmQ8pa3RAVqqBMBYJninKLdCD8eQzIlDhtIzwmYGLrsJMktFF3pJFCqEFv1rKZy_OUyV4JOkOLtXbKnwxqmFTq-2SP0KtUWjDy1-U8GnVDptISjOf2O9FaLA
==="""


class TestGCPCloudProvider(unittest.TestCase):
    """
    Class used for testing detector of GCP
    """

    def setUp(self):
        """
        Patch communication with metadata provider
        """
        requests_patcher = patch('rhsmlib.cloud._base_provider.requests')
        self.requests_mock = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

    def test_gcp_cloud_provider_id(self):
        """
        Test of CLOUD_PROVIDER_ID
        """
        self.assertEqual(gcp.GCPCloudProvider.CLOUD_PROVIDER_ID, "gcp")
        gcp_detector = gcp.GCPCloudProvider({})
        self.assertEqual(gcp_detector.CLOUD_PROVIDER_ID, "gcp")

    def test_gcp_not_vm(self):
        """
        Test for the case, when the machine is host (not virtual machine)
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': False,
            'dmi.bios.version': 'cool hardware company'
        }
        gcp_detector = gcp.GCPCloudProvider(facts)
        is_vm = gcp_detector.is_vm()
        self.assertFalse(is_vm)

    def test_gcp_vm(self):
        """
        Test for the case, when the vm is running on GCP
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': 'Google',
            'dmi.bios.vendor': 'Google'
        }
        gcp_detector = gcp.GCPCloudProvider(facts)
        is_vm = gcp_detector.is_vm()
        self.assertTrue(is_vm)
        is_gcp_vm = gcp_detector.is_running_on_cloud()
        self.assertTrue(is_gcp_vm)

    def test_vm_not_on_gcp_cloud(self):
        """
        Test for the case, when the vm is not running on GCP
        """
        # We will mock facts using simple dictionary
        facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
            'dmi.bios.version': '1.0',
            'dmi.bios.vendor': 'Foo'
        }
        gcp_detector = gcp.GCPCloudProvider(facts)
        is_vm = gcp_detector.is_vm()
        self.assertTrue(is_vm)
        is_gcp_vm = gcp_detector.is_running_on_cloud()
        self.assertFalse(is_gcp_vm)

    def test_get_token(self):
        """
        Test getting GCP token, when default audience URL is used
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = GCP_JWT_TOKEN
        self.requests_mock.get = Mock(return_value=mock_result)
        gcp_collector = gcp.GCPCloudProvider({})
        gcp_collector._get_token_from_cache_file = Mock(return_value=None)
        gcp_collector._write_token_to_cache_file = Mock(return_value=None)
        token = gcp_collector.get_metadata()
        self.requests_mock.get.assert_called_once_with(
            'http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience=https://subscription.rhsm.redhat.com:443/subscription&format=full',
            headers={
                'user-agent': 'RHSM/1.0',
                'Metadata-Flavor': 'Google'
            }
        )
        self.assertEqual(token, GCP_JWT_TOKEN)

    def test_get_token_custom_audience(self):
        """
        Test getting GCP token, when custom audience URL is used (e.g. Satellite or stage is used)
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = GCP_JWT_TOKEN
        self.requests_mock.get = Mock(return_value=mock_result)
        gcp_collector = gcp.GCPCloudProvider({}, audience_url="https://example.com:8443/rhsm")
        gcp_collector._get_token_from_cache_file = Mock(return_value=None)
        gcp_collector._write_token_to_cache_file = Mock(return_value=None)
        token = gcp_collector.get_metadata()
        self.requests_mock.get.assert_called_once_with(
            'http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience=https://example.com:8443/rhsm&format=full',
            headers={
                'user-agent': 'RHSM/1.0',
                'Metadata-Flavor': 'Google'
            }
        )
        self.assertEqual(token, GCP_JWT_TOKEN)

    def test_decode_jwt(self):
        """
        Test decoding of JWT token
        """

        gcp_collector = gcp.GCPCloudProvider({}, audience_url="https://subscription.rhsm.redhat.com:443/subscription")
        jose_header_str, metadata_str, encoded_signature = gcp_collector.decode_jwt(GCP_JWT_TOKEN)

        self.assertIsNotNone(jose_header_str)
        self.assertIsNotNone(metadata_str)
        self.assertIsNotNone(encoded_signature)

        self.assertEqual(jose_header_str, GCP_JOSE_HEADER)
        self.assertEqual(metadata_str, GCP_METADATA)
        self.assertEqual(encoded_signature, GCP_SIGNATURE)

        jose_header = json.loads(jose_header_str)
        self.assertIn("typ", jose_header)
        self.assertEqual(jose_header["typ"], "JWT")

        metadata = json.loads(metadata_str)
        self.assertIn("google", metadata)
        self.assertIn("compute_engine", metadata["google"])
        self.assertIn("instance_id", metadata["google"]["compute_engine"])
        self.assertEqual("2589221140676718026", metadata["google"]["compute_engine"]["instance_id"])

    def test_decoding_corrupted_jwt(self):
        """
        Test decoding of JWT token with wrong UTF-encoding
        """

        jwt_token = 'foobar.foobar.foobar'
        gcp_collector = gcp.GCPCloudProvider({})

        jose_header_str, metadata_str, encoded_signature = gcp_collector.decode_jwt(jwt_token)

        self.assertIsNone(jose_header_str)
        self.assertIsNone(metadata_str)

    def test_decoding_jwt_wrong_section_number(self):
        """
        Test decoding of JWT token with wrong number of sections
        """
        # There are only two sections
        jwt_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTYyMzkwMjJ9'
        gcp_collector = gcp.GCPCloudProvider({})

        jose_header_str, metadata_str, encoded_signature = gcp_collector.decode_jwt(jwt_token)

        self.assertIsNone(jose_header_str)
        self.assertIsNone(metadata_str)


class TestCloudProvider(unittest.TestCase):
    """
    Class for testing rhsmlib.cloud.utils module
    """
    def setUp(self):
        """
        Set up two mocks that are used in all tests
        """
        host_collector_patcher = patch('rhsmlib.cloud.provider.HostCollector')
        self.host_collector_mock = host_collector_patcher.start()
        self.host_fact_collector_instance = Mock()
        self.host_collector_mock.return_value = self.host_fact_collector_instance
        self.addCleanup(host_collector_patcher.stop)

        hardware_collector_patcher = patch('rhsmlib.cloud.provider.HardwareCollector')
        self.hardware_collector_mock = hardware_collector_patcher.start()
        self.hw_fact_collector_instance = Mock()
        self.hardware_collector_mock.return_value = self.hw_fact_collector_instance
        self.addCleanup(hardware_collector_patcher.stop)

        aws_requests_patcher = patch('rhsmlib.cloud.providers.aws.requests')
        self.aws_requests_mock = aws_requests_patcher.start()
        self.addCleanup(aws_requests_patcher.stop)
        write_cache_patcher = patch('rhsmlib.cloud.providers.aws.AWSCloudProvider._write_token_to_cache_file')
        self.write_cache_mock = write_cache_patcher.start()
        self.addCleanup(write_cache_patcher.stop)

        azure_requests_patcher = patch('rhsmlib.cloud._base_provider.requests')
        self.azure_requests_mock = azure_requests_patcher.start()
        self.addCleanup(azure_requests_patcher.stop)

    def test_detect_cloud_provider_aws(self):
        """
        Test the case, when detecting of aws works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Amazon EC2'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['aws'])

    def test_detect_cloud_provider_aws_heuristics(self):
        """
        Test the case, when detecting of aws does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'AWS',
            'dmi.bios.version': '1.0',
            'dmi.system.manufacturer': 'Amazon'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['aws'])

    def test_detect_cloud_provider_gcp(self):
        """
        Test the case, when detecting of gcp works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Google',
            'dmi.bios.version': 'Google'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['gcp'])

    def test_detect_cloud_provider_gcp_heuristics(self):
        """
        Test the case, when detecting of gcp does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm'
        }
        hw_facts = {
            'dmi.bios.vendor': 'Foo Company',
            'dmi.bios.version': '1.0',
            'dmi.chassis.asset_tag': 'Google Cloud',
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['gcp'])

    def test_detect_cloud_provider_azure(self):
        """
        Test the case, when detecting of azure works as expected
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Foo company',
            'dmi.bios.version': '1.0',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['azure'])

    def test_detect_cloud_provider_azure_heuristics(self):
        """
        Test the case, when detecting of azure does not work using strong signs, but it is necessary
        to use heuristics method
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Microsoft',
            'dmi.bios.version': '1.0',
            'dmi.system.manufacturer': 'Google',
            'dmi.chassis.manufacturer': 'Amazon'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        self.assertEqual(detected_clouds, ['azure'])

    def test_conclict_in_strong_signs(self):
        """
        Test the case, when cloud providers change strong signs and there is conflict (two providers
        are detected using strong signs). In such case result using strong signs should be dropped
        and heuristics should be used, because strong signs do not work with probability and original
        order is influenced by the order of classes in 'constant' CLOUD_DETECTORS.
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Google',
            'dmi.bios.version': 'Amazon EC2',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77',
            'dmi.chassis.manufacturer': 'Microsoft'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        detected_clouds.sort()
        self.assertEqual(detected_clouds, ['aws', 'azure', 'gcp'])

    def test_conclict_in_heuristics_detection(self):
        """
        Test the case, when cloud providers two cloud providers were
        detected using heuristics with same probability.
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'kvm',
        }
        hw_facts = {
            'dmi.system.manufacturer': 'Google',
            'dmi.chassis.manufacturer': 'Amazon EC2',
        }
        facts = {**host_facts, **hw_facts}

        aws_cloud_provider = aws.AWSCloudProvider(facts)
        azure_cloud_provider = azure.AzureCloudProvider(facts)
        gcp_cloud_provider = gcp.GCPCloudProvider(facts)

        probability_aws = aws_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_aws, 0.6)
        probability_azure = azure_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_azure, 0.0)
        probability_gcp = gcp_cloud_provider.is_likely_running_on_cloud()
        self.assertEqual(probability_gcp, 0.6)

        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        detected_clouds = detect_cloud_provider()
        detected_clouds.sort()
        self.assertEqual(detected_clouds, ['aws', 'gcp'])

    def test_collect_cloud_info_one_cloud_provider_detected(self):
        """
        Test the case, when we try to collect cloud info only for
        one detected cloud provider
        """
        self.aws_requests_mock.get = get_only_imds_v2_is_supported
        self.aws_requests_mock.put = put_imds_v2_token

        cloud_list = ['aws']
        cloud_info = collect_cloud_info(cloud_list)

        self.assertIsNotNone(cloud_info)
        self.assertTrue(len(cloud_info) > 0)
        self.assertTrue('cloud_id' in cloud_info)
        self.assertEqual(cloud_info['cloud_id'], 'aws')
        # Test metadata
        self.assertTrue('metadata' in cloud_info)
        b64_metadata = cloud_info['metadata']
        metadata = base64.b64decode(b64_metadata).decode('utf-8')
        self.assertEqual(metadata, AWS_METADATA)
        # Test signature
        self.assertTrue('signature' in cloud_info)
        b64_signature = cloud_info['signature']
        signature = base64.b64decode(b64_signature).decode('utf-8')
        self.assertEqual(
            signature,
            '-----BEGIN PKCS7-----\n' + AWS_SIGNATURE + '\n-----END PKCS7-----'
        )

    def test_collect_cloud_info_more_cloud_providers_detected(self):
        """
        Test the case, when we try to collect cloud info only for
        more than one cloud providers, because more than one cloud
        providers were detected
        """
        mock_result = Mock()
        mock_result.status_code = 400
        mock_result.text = 'Not Found 400'
        self.azure_requests_mock.get = Mock(return_value=mock_result)

        self.aws_requests_mock.get = get_only_imds_v2_is_supported
        self.aws_requests_mock.put = put_imds_v2_token

        cloud_list = ['azure', 'aws']
        cloud_info = collect_cloud_info(cloud_list)

        self.assertIsNotNone(cloud_info)
        self.assertTrue(len(cloud_info) > 0)
        self.assertTrue('cloud_id' in cloud_info)
        self.assertEqual(cloud_info['cloud_id'], 'aws')
        # Test metadata
        self.assertTrue('metadata' in cloud_info)
        b64_metadata = cloud_info['metadata']
        metadata = base64.b64decode(b64_metadata).decode('utf-8')
        self.assertEqual(metadata, AWS_METADATA)
        # Test signature
        self.assertTrue('signature' in cloud_info)
        b64_signature = cloud_info['signature']
        signature = base64.b64decode(b64_signature).decode('utf-8')
        self.assertEqual(
            signature,
            '-----BEGIN PKCS7-----\n' + AWS_SIGNATURE + '\n-----END PKCS7-----'
        )

    def test_get_cloud_provider(self):
        """
        Test getting instance of cloud provider
        """
        host_facts = {
            'virt.is_guest': True,
            'virt.host_type': 'hyperv',
        }
        hw_facts = {
            'dmi.bios.vendor': 'Microsoft',
            'dmi.bios.version': '1.0',
            'dmi.chassis.asset_tag': '7783-7084-3265-9085-8269-3286-77'
        }
        self.host_fact_collector_instance.get_all.return_value = host_facts
        self.hw_fact_collector_instance.get_all.return_value = hw_facts
        cloud_provider = get_cloud_provider()
        self.assertIsInstance(cloud_provider, azure.AzureCloudProvider)
