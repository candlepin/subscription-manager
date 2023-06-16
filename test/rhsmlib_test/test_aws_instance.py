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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import socket
import mock

from rhsmlib.facts import cloud_facts
from rhsm.https import httplib
from mock import patch


from subscription_manager import injection as inj

AWS_INSTANCE_ID = "i-2d05f031d20c"
CLOUD_INSTANCE_ID = "i-1d06f031e20c"

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


class TestCloudFactsCollector(unittest.TestCase):
    def setUp(self):
        super(TestCloudFactsCollector, self).setUp()
        self.mock_facts = mock.Mock()
        inj.provide(inj.FACTS, self.mock_facts)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_aws_instance_id(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        MockConn.return_value.getresponse.return_value.read.return_value = \
            '{"privateIp": "10.158.112.84", \
            "version" : "2017-09-30", \
            "instanceId" : "' + AWS_INSTANCE_ID + '"}'
        facts = self.collector.get_all()
        self.assertIn("aws_instance_id", facts)
        self.assertEqual(facts["aws_instance_id"], AWS_INSTANCE_ID)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_aws_token(self, mock_conn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        mock_conn.return_value.getresponse.return_value.read.return_value = \
            b'AQAEAMKTcJXpYC7pycctJeXyXrqrog2fMk0_CDMgb_tslehR_hTDyA=='
        headers = {'X-aws-ec2-metadata-token-ttl-seconds': str(cloud_facts.AWS_INSTANCE_TOKEN_TTL)}
        token = self.collector.get_aws_token(
            ip_addr=cloud_facts.AWS_INSTANCE_IP,
            path=cloud_facts.AWS_INSTANCE_TOKEN_PATH,
            headers=headers
        )
        self.assertEqual(token, 'AQAEAMKTcJXpYC7pycctJeXyXrqrog2fMk0_CDMgb_tslehR_hTDyA==')

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_azure_instance_id(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77"
            }
        )
        MockConn.return_value.getresponse.return_value.read.return_value = AZURE_METADATA
        facts = self.collector.get_all()
        self.assertIn("azure_instance_id", facts)
        self.assertEqual(facts["azure_instance_id"], "12345678-1234-1234-1234-123456789abc")

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_gcp_facts(self, MockConn):
        """
        Test getting GCP instance ID from metadata provided by GCP cloud provider
        """
        MockConn.return_value.getresponse.return_value.read.return_value = GCP_JWT_TOKEN
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={"virt.is_guest": True, "dmi.bios.vendor": "google"}
        )
        MockConn.return_value.getresponse.return_value.read.return_value = GCP_JWT_TOKEN

        facts = self.collector.get_all()

        self.assertIn("gcp_instance_id", facts)
        self.assertEqual(facts["gcp_instance_id"], "2589221140676718026")
        self.assertIn("gcp_license_codes", facts)
        self.assertEqual(facts["gcp_license_codes"], "5731035067256925298")
        self.assertIn("gcp_project_id", facts)
        self.assertEqual(facts["gcp_project_id"], "fair-kingdom-308514")
        self.assertIn("gcp_project_number", facts)
        self.assertEqual(facts["gcp_project_number"], 161958465613)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_not_aws_instance(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "1.0.cloud"
            }
        )
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "{'privateIp' : '10.158.112.84', \
            'version' : '2017-09-30, \
            'instanceId' : '" + CLOUD_INSTANCE_ID + "'}"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_not_instance_id(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "{'privateIp' : '10.158.112.84', \
            'version' : '2017-09-30'}"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_bad_json(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        MockConn.return_value.getresponse.return_value.read.return_value = \
            "other text stuff"
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_timeout(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        MockConn.return_value.getresponse.side_effect = socket.timeout
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)

    # test ensures that exception is captured and does not impede
    @patch('rhsm.https.httplib.HTTPConnection')
    def test_get_http_error(self, MockConn):
        self.collector = cloud_facts.CloudFactsCollector(
            collected_hw_info={
                "dmi.bios.version": "4.2.amazon"
            }
        )
        MockConn.return_value.getresponse.side_effect = httplib.HTTPException(
            mock.Mock(return_value={'status': 500}), 'error'
        )
        facts = self.collector.get_all()
        self.assertNotIn("aws_instance_id", facts)
