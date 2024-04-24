from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
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

import unittest
import mock
from mock import patch, Mock

import socket
import requests

from rhsmlib.facts import cloud_facts

from cloud_what.providers import aws, azure, gcp

from subscription_manager import injection as inj

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

GCP_JWT_TOKEN = """eyJhbGciOiJSUzI1NiIsImtpZCI6IjZhOGJhNTY1MmE3MDQ0MTIxZDRmZWRhYzhmMTRkMTRjNTRlNDg5NWIiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJodHRwczovL3N1YnNjcmlwdGlvbi5yaHNtLnJlZGhhdC5jb206NDQzL3N1YnNjcmlwdGlvbiIsImF6cCI6IjEwNDA3MDk1NTY4MjI5ODczNjE0OSIsImVtYWlsIjoiMTYxOTU4NDY1NjEzLWNvbXB1dGVAZGV2ZWxvcGVyLmdzZXJ2aWNlYWNjb3VudC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZXhwIjoxNjE2NTk5ODIzLCJnb29nbGUiOnsiY29tcHV0ZV9lbmdpbmUiOnsiaW5zdGFuY2VfY3JlYXRpb25fdGltZXN0YW1wIjoxNjE2NTk1ODQ3LCJpbnN0YW5jZV9pZCI6IjI1ODkyMjExNDA2NzY3MTgwMjYiLCJpbnN0YW5jZV9uYW1lIjoiaW5zdGFuY2UtMSIsImxpY2Vuc2VfaWQiOlsiNTczMTAzNTA2NzI1NjkyNTI5OCJdLCJwcm9qZWN0X2lkIjoiZmFpci1raW5nZG9tLTMwODUxNCIsInByb2plY3RfbnVtYmVyIjoxNjE5NTg0NjU2MTMsInpvbmUiOiJ1cy1lYXN0MS1iIn19LCJpYXQiOjE2MTY1OTYyMjMsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsInN1YiI6IjEwNDA3MDk1NTY4MjI5ODczNjE0OSJ9.XQKeqMAvsH2T2wsdN97jlm52DzLfix3DTMCu9QCuhSKLEk1xHYOYtvh5Yzn7j-tbZtV-siyPAfpGZO3Id87573OVGgohN3q7Exlf9CEIHa1-X7zLyiyIlyrnfQJ1aGHeH6y7gb_tWxHFLJRzhulfkfJxSDn5fEBSgBqbjzCr9unQgMkuzQ3uui2BbIbALmOpY6D-IT71mgMDZ_zm4G6q-Mh0nIMkDWhmQ8pa3RAVqqBMBYJninKLdCD8eQzIlDhtIzwmYGLrsJMktFF3pJFCqEFv1rKZy_OUyV4JOkOLtXbKnwxqmFTq-2SP0KtUWjDy1-U8GnVDptISjOf2O9FaLA
"""

# The AWS instance ID has to be the same as "instance_id" in AWS_METADATA
AWS_INSTANCE_ID = "i-abcdef01234567890"
AWS_ACCOUNT_ID = "012345678900"
AWS_BILLING_PRODUCTS = "bp-0124abcd bp-63a5400a"
# The Azure instance ID has to be the same as "vmId" in AZURE_METADATA
# values for "sku" an "offer" has to be same as in AZURE_METADATA
AZURE_INSTANCE_ID = "12345678-1234-1234-1234-123456789abc"
AZURE_SKU = "8.1-ci"
AZURE_OFFER = "RHEL"
AZURE_SUBSCRIPTION_ID = "01234567-0123-0123-0123-012345679abc"
AZURE_LOCATION = "westeurope"


def mock_prepare_request(request):
    return request


class TestCloudCollector(unittest.TestCase):
    def setUp(self):
        super(TestCloudCollector, self).setUp()
        self.mock_facts = mock.Mock()
        inj.provide(inj.FACTS, self.mock_facts)
        # Azure and GCP
        self.requests_patcher = patch('cloud_what._base_provider.requests')
        self.requests_mock = self.requests_patcher.start()
        self.addCleanup(self.requests_patcher.stop)

    def tearDown(self) -> None:
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

    @patch('cloud_what.providers.aws.requests.Session', name='test_get_aws_facts.mock_session_class')
    def test_get_aws_facts(self, mock_session_class):
        """
        Test getting AWS facts (instance ID, accountID and billingProducts)
        """
        mock_result = Mock(name="_test_get_aws_facts.mock_result")
        mock_result.status_code = 200
        mock_result.text = AWS_METADATA
        mock_session = Mock(name="_test_get_aws_facts.mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="_test_get_aws_facts.mock_session.send"
        )
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session

        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )

        facts = self.collector.get_all()

        self.assertIn("aws_instance_id", facts)
        self.assertEqual(facts["aws_instance_id"], AWS_INSTANCE_ID)
        self.assertIn("aws_account_id", facts)
        self.assertEqual(facts["aws_account_id"], AWS_ACCOUNT_ID)
        self.assertIn("aws_billing_products", facts)
        self.assertEqual(facts["aws_billing_products"], AWS_BILLING_PRODUCTS)
        self.assertIn("aws_marketplace_product_codes", facts)
        self.assertEqual(facts["aws_marketplace_product_codes"], None)

    @patch('cloud_what.providers.aws.requests.Session', name='mock_session_class')
    def test_get_aws_facts_with_null_billing_products(self, mock_session_class):
        """
        Billing products could be null in some cases (not RHEL)
        """
        mock_result = Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = """
{
  "accountId" : "012345678900",
  "architecture" : "x86_64",
  "availabilityZone" : "eu-central-1b",
  "billingProducts" : null,
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
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="mock_session.send"
        )
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session

        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        facts = self.collector.get_all()

        self.assertIn("aws_instance_id", facts)
        self.assertEqual(facts["aws_instance_id"], AWS_INSTANCE_ID)
        self.assertIn("aws_account_id", facts)
        self.assertEqual(facts["aws_account_id"], AWS_ACCOUNT_ID)
        self.assertIn("aws_billing_products", facts)
        self.assertEqual(facts["aws_billing_products"], None)
        self.assertIn("aws_marketplace_product_codes", facts)
        self.assertEqual(facts["aws_marketplace_product_codes"], None)

    def test_get_azure_facts(self):
        """
        Test getting Azure facts instance ID (vmId) from metadata provided by Azure cloud provider
        """
        self.requests_mock.Request = Mock(name="mock_Request")
        mock_result = Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = AZURE_METADATA
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(return_value=mock_result, name="mock_send")
        mock_session.prepare_request = Mock(name="mock_prepare_request")
        mock_session.hooks = {'response': []}
        self.requests_mock.Session = Mock(return_value=mock_session, name="mock_Session")

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77"
            }
        )
        facts = self.collector.get_all()

        # azure_instance_id should be included in the facts
        self.assertIn("azure_instance_id", facts)
        self.assertEqual(facts["azure_instance_id"], AZURE_INSTANCE_ID)
        # some other azure facts should be included in facts too
        self.assertIn("azure_sku", facts)
        self.assertEqual(facts["azure_sku"], AZURE_SKU)
        self.assertIn("azure_offer", facts)
        self.assertEqual(facts["azure_offer"], AZURE_OFFER)
        self.assertIn("azure_subscription_id", facts)
        self.assertEqual(facts["azure_subscription_id"], AZURE_SUBSCRIPTION_ID)
        self.assertIn("azure_location", facts)
        self.assertEqual(facts["azure_location"], AZURE_LOCATION)

    @patch('cloud_what.providers.gcp.GCPCloudProvider._write_token_to_cache_file')
    @patch('cloud_what.providers.gcp.GCPCloudProvider._get_metadata_from_cache')
    def test_get_gcp_facts(self, mock_get_metadata_from_cache, mock_write_token_to_cache_file):
        """
        Test getting GCP instance ID from metadata provided by GCP cloud provider
        """
        self.requests_mock.Request = Mock(name="mock_Request")
        mock_result = Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = GCP_JWT_TOKEN
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(return_value=mock_result, name="mock_send")
        mock_session.prepare_request = Mock(name="mock_prepare_request")
        mock_session.hooks = {'response': []}
        self.requests_mock.Session = Mock(return_value=mock_session, name="mock_Session")

        mock_get_metadata_from_cache.return_value = None
        mock_write_token_to_cache_file.return_value = None

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.vendor": "google"
            }
        )
        facts = self.collector.get_all()

        self.assertIn("gcp_instance_id", facts)
        self.assertEqual(facts["gcp_instance_id"], "2589221140676718026")
        self.assertIn("gcp_license_codes", facts)
        self.assertEqual(facts["gcp_license_codes"], "5731035067256925298")
        self.assertIn("gcp_project_id", facts)
        self.assertEqual(facts["gcp_project_id"], "fair-kingdom-308514")
        self.assertIn("gcp_project_number", facts)
        self.assertEqual(facts["gcp_project_number"], 161958465613)

    @patch('cloud_what.providers.aws.requests.Session', name='mock_session_class')
    def test_get_not_aws_instance(self, mock_session_class):
        """
        Test that AWS instance ID is not included in facts, when VM is not running on the AWS public cloud
        """
        mock_result = mock.Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = '{"foo": "bar"}'
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="mock_session.send"
        )
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session
        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "Foo"
            }
        )
        facts = self.collector.get_all()

        self.assertNotIn("aws_instance_id", facts)

    @patch('cloud_what.providers.aws.requests.Session', name='mock_session_class')
    def test_get_bad_json(self, mock_session_class):
        """
        Test parsing some string that is not Json document
        """
        mock_result = mock.Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = "not json document"
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="mock_session.send"
        )
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session
        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        facts = self.collector.get_all()

        self.assertNotIn("aws_instance_id", facts)

    @patch('cloud_what.providers.aws.requests.Session', name='mock_session_class')
    def test_get_timeout(self, mock_session_class):
        """
        Test ensures that exception is captured and does not impede
        """
        mock_result = mock.Mock(name="mock_result")
        mock_result.status_code = 200
        mock_result.text = AWS_METADATA
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="mock_session.send"
        )
        mock_session.send.side_effect = socket.timeout
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session
        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        facts = self.collector.get_all()

        self.assertNotIn("aws_instance_id", facts)

    @patch('cloud_what.providers.aws.requests.Session', name='mock_session_class')
    def test_get_http_error(self, mock_session_class):
        """
        test ensures that exception is captured and does not impede
        """
        mock_result = mock.Mock(name="mock_result")
        mock_result.status_code = 500
        mock_result.text = "error"
        mock_session = Mock(name="mock_session")
        mock_session.send = Mock(
            return_value=mock_result,
            name="mock_session.send"
        )
        mock_session.side_effect = requests.exceptions.HTTPError()
        mock_session.prepare_request = mock_prepare_request
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session
        # We need to patch only Session in this case
        self.requests_patcher.stop()

        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "virt.is_guest": True,
                "dmi.bios.version": "4.2.amazon"
            }
        )
        facts = self.collector.get_all()

        self.assertNotIn("aws_instance_id", facts)
