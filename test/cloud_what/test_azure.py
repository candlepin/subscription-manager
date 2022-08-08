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
Module for testing Azure part of Python package cloud_what
"""

import unittest
from mock import patch, Mock, call
import json
import requests

from cloud_what.providers import azure

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
"""  # noqa: E501

AZURE_SIGNATURE = """
{"encoding":"pkcs7","signature":"MIIKWQYJKoZIhvcNAQcCoIIKSjCCCkYCAQExDzANBgkqh\
kiG9w0BAQsFADCB4wYJKoZIhvcNAQcBoIHVBIHSeyJub25jZSI6IjIwMjEwMTA0LTE5NTUzNCIsInB\
sYW4iOnsibmFtZSI6IiIsInByb2R1Y3QiOiIiLCJwdWJsaXNoZXIiOiIifSwidGltZVN0YW1wIjp7I\
mNyZWF0ZWRPbiI6IjAxLzA0LzIxIDEzOjU1OjM0IC0wMDAwIiwiZXhwaXJlc09uIjoiMDEvMDQvMjE\
gMTk6NTU6MzQgLTAwMDAifSwidm1JZCI6ImY5MDRlY2U4LWM2YzEtNGI1Yy04ODFmLTMwOWI1MGYyN\
WU1NiJ9oIIHszCCB68wggWXoAMCAQICE2sAA9CNXTZWgCfFbjAAAAAD0I0wDQYJKoZIhvcNAQELBQA\
wTzELMAkGA1UEBhMCVVMxHjAcBgNVBAoTFU1pY3Jvc29mdCBDb3Jwb3JhdGlvbjEgMB4GA1UEAxMXT\
Wljcm9zb2Z0IFJTQSBUTFMgQ0EgMDEwHhcNMjAxMjAzMDExNDQ2WhcNMjExMjAzMDExNDQ2WjAdMRs\
wGQYDVQQDExJtZXRhZGF0YS5henVyZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBA\
QDTmv9qqV0VheHfrysxg99qC9VxpnE9x4pbjsqLNVVssp8pdr3zcfbBPbvOOgvIRv8/JCTrN4ffweJ\
6eiwYTwKhnxyDhfTOfkRbMOwLn100rNryEkYOC/NymNF1aqNIvRT6X/nplygcLWg2kCZxIXHnNosG2\
wLrIBlzLhqrMtAzUCz2jmOKGDMu1JxLiT3YAmIRPYbYvJlMTMHhZqe4InhBZxdX/J5XXgzXbL1KzlA\
Qj7aOsh72OPu/cX6ETTzuXCIZibDL3sknZSpZeuNz0pnSC0/B70bGGTxuUZcxNy0dgW1t37pK8EGnW\
8kxBOO1vWTnR/ca4w+QakXXfcMbAWLtAgMBAAGjggO0MIIDsDCCAQMGCisGAQQB1nkCBAIEgfQEgfE\
A7wB1AH0+8viP/4hVaCTCwMqeUol5K8UOeAl/LmqXaJl+IvDXAAABdiYztGsAAAQDAEYwRAIgWpDU+\
ZDd8qLC2OAUWKVqK3DHJ8nd3TiXachxppHeRzQCIEgMrIGHcvT6ue+LCmzDb0MPDwAcYTaG+82aK8k\
jNgs7AHYAVYHUwhaQNgFK6gubVzxT8MDkOHhwJQgXL6OqHQcT0wwAAAF2JjO1bwAABAMARzBFAiEAm\
nAnhcGJIERiGZiBG6yoW9vu2zPGH9LDYSe9Tsf3e7ECIHSm4fZ+zKeIFCOSwGlSN8/gELMBJ6DPWMN\
MQ8TpEyo7MCcGCSsGAQQBgjcVCgQaMBgwCgYIKwYBBQUHAwEwCgYIKwYBBQUHAwIwPgYJKwYBBAGCN\
xUHBDEwLwYnKwYBBAGCNxUIh9qGdYPu2QGCyYUbgbWeYYX062CBXYWGjkGHwphQAgFkAgElMIGHBgg\
rBgEFBQcBAQR7MHkwUwYIKwYBBQUHMAKGR2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2kvbXNjb\
3JwL01pY3Jvc29mdCUyMFJTQSUyMFRMUyUyMENBJTIwMDEuY3J0MCIGCCsGAQUFBzABhhZodHRwOi8\
vb2NzcC5tc29jc3AuY29tMB0GA1UdDgQWBBRt8786ehWZoL09LrwjfrXi0ypzFzALBgNVHQ8EBAMCB\
LAwPAYDVR0RBDUwM4Idd2VzdGV1cm9wZS5tZXRhZGF0YS5henVyZS5jb22CEm1ldGFkYXRhLmF6dXJ\
lLmNvbTCBsAYDVR0fBIGoMIGlMIGioIGfoIGchk1odHRwOi8vbXNjcmwubWljcm9zb2Z0LmNvbS9wa\
2kvbXNjb3JwL2NybC9NaWNyb3NvZnQlMjBSU0ElMjBUTFMlMjBDQSUyMDAxLmNybIZLaHR0cDovL2N\
ybC5taWNyb3NvZnQuY29tL3BraS9tc2NvcnAvY3JsL01pY3Jvc29mdCUyMFJTQSUyMFRMUyUyMENBJ\
TIwMDEuY3JsMFcGA1UdIARQME4wQgYJKwYBBAGCNyoBMDUwMwYIKwYBBQUHAgEWJ2h0dHA6Ly93d3c\
ubWljcm9zb2Z0LmNvbS9wa2kvbXNjb3JwL2NwczAIBgZngQwBAgEwHwYDVR0jBBgwFoAUtXYMMBHOx\
5JCTUzHXCzIqQzoC2QwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMCMA0GCSqGSIb3DQEBCwU\
AA4ICAQCKueIzSjIwc30ZoGMJpEKmYIDK/3Jg5wp7oom9HcECgIL8Ou1s2g3pSXf7NyLQP1ST19bvx\
QSzPbXBvBcz6phKdtHH7bH2c3uMhy74zSbxQybL0pjse1tT0lyTCWcitPk/8U/E/atQpTshKsnwIdB\
hkR3LAUQnIXDBAVpV2Njj3rUfI7OpT2tODcRPuGQW631teQULJNbR+Aprmp6/Y42hLFHfmyi2TmR0R\
/b94anLIie1MIcU8ikYf8/gVniOosKQFfNtmpnuPcnl0tqliQP44rN7ijFudvXz4CIOKocIGF14IsN\
ZypLR2WQB9jo+nOa+XEV4T6BK9W2skxIws7/TT8Ks8PescvV1DYOamgRB2KyTUDsEGFgtNbh3L0h8x\
KyzAGIU1XbGyWSvtaRGdbH3PU5ERRDMfqOP0twjmxn20leeYKnS+DfiAMakWuguygRhQ50u3ZJKbls\
RF4zs5r8dE65eIOUl6GIjEvZCy1OCKIb6U/15hmbEiQLtqNqhowLdaoxW2Xpkd/H0icm5FA7YmeoHs\
sJJiE/1kT5r/dtSH9elMaQ8SQ4MfVo/FSKPTIOQK3UzeEyT6QvzQUxQiUZvZA/Cxta8z9R8RSAUtxA\
MQ7ATYVGJsVxssP6Hk79XlgloevHWS2srVAkFD07tBhhNAAFC6DVz9T0unxhJMDe6kjGCAZEwggGNA\
gEBMGYwTzELMAkGA1UEBhMCVVMxHjAcBgNVBAoTFU1pY3Jvc29mdCBDb3Jwb3JhdGlvbjEgMB4GA1U\
EAxMXTWljcm9zb2Z0IFJTQSBUTFMgQ0EgMDECE2sAA9CNXTZWgCfFbjAAAAAD0I0wDQYJKoZIhvcNA\
QELBQAwDQYJKoZIhvcNAQEBBQAEggEAbyBz+8VYrETncYr9W1FGKD47mNVmvd2NA7RaWaduz/MDDSc\
BgZr1UFxGMnxqBoRsrVD8rRxYTkLo8VLV1UrGWoLlYrbtuKyeoWxj2tFcdQLjDs16/jydY8rINLmMm\
ZGxOnhpPjewCB3epn2pmMTPr1kwJSpD23Jko41MBoYjTnUnYtqZgKDmPFgtcMnIP9cBX5rnBdNfaUg\
19aJvCZkw4mQkIam9F6xXE9qkqenapywTmNIiczpXOFrzGoCaq0N4yKxZYTvwndefiPPihH4D6TIGL\
ZbKQD0kK/MIvrs+JobW43kTKUKyzyGNhQHmBRDXNDy/bWMOUyjbDpZLYEm9tg=="}
"""

# Use something from far future
SUPPORTED_AZURE_VERSIONS = ["2141-06-01", "2141-09-01", "2142-03-01"]

# Real list is much longer (about 15 items)
AZURE_API_VERSIONS = json.dumps({"apiVersions": SUPPORTED_AZURE_VERSIONS})


class TestAzureCloudProvider(unittest.TestCase):
    """
    Class used for testing of Azure cloud provider
    """

    def setUp(self):
        """
        Patch communication with metadata provider
        """
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        requests_patcher = patch("cloud_what._base_provider.requests")
        self.requests_mock = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

    def tearDown(self):
        """
        Clean after each unit test
        """
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False

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
        facts = {"virt.is_guest": False, "dmi.bios.version": "cool hardware company"}
        azure_detector = azure.AzureCloudProvider(facts)
        is_vm = azure_detector.is_vm()
        self.assertFalse(is_vm)

    def test_azure_vm(self):
        """
        Test for the case, when the vm is running on Azure
        """
        # We will mock facts using simple dictionary
        facts = {
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.version": "090008",
            "dmi.chassis.asset_tag": "7783-7084-3265-9085-8269-3286-77",
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
            "virt.is_guest": True,
            "virt.host_type": "hyperv",
            "dmi.bios.version": "090008",
            "dmi.bios.vendor": "Foo",
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
        self.requests_mock.Request = Mock()
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AZURE_METADATA
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)
        azure_collector = azure.AzureCloudProvider({})
        metadata = azure_collector.get_metadata()
        self.requests_mock.Request.assert_called_once_with(
            method="GET",
            url="http://169.254.169.254/metadata/instance?api-version="
            + azure.AzureCloudProvider.API_VERSION,
            headers={"User-Agent": "cloud-what/1.0", "Metadata": "true"},
        )
        mock_session.send.assert_called_once()
        self.assertEqual(metadata, AZURE_METADATA)

    def test_get_api_versions(self):
        """
        Test getting API versions
        """
        self.requests_mock.Request = Mock()
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AZURE_API_VERSIONS
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)
        azure_provider = azure.AzureCloudProvider({})
        api_versions = azure_provider.get_api_versions()
        self.requests_mock.Request.assert_called_once_with(
            method="GET",
            url="http://169.254.169.254/metadata/versions",
            headers={"User-Agent": "cloud-what/1.0", "Metadata": "true"},
        )
        mock_session.send.assert_called_once()
        self.assertEqual(api_versions, SUPPORTED_AZURE_VERSIONS)

    def test_get_signature_from_server(self):
        """
        Test getting signature from server, when there is no cache file
        """
        self.requests_mock.Request = Mock()
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AZURE_SIGNATURE
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)
        azure_collector = azure.AzureCloudProvider({})
        signature = azure_collector.get_signature()
        self.requests_mock.Request.assert_called_once_with(
            method="GET",
            url="http://169.254.169.254/metadata/attested/document?api-version="
            + azure.AzureCloudProvider.API_VERSION,
            headers={"User-Agent": "cloud-what/1.0", "Metadata": "true"},
        )
        mock_session.send.assert_called_once()
        self.assertEqual(signature, AZURE_SIGNATURE)

    @staticmethod
    def mock_send_azure_IMDS(request, *args, **kwargs):
        """
        Mock Azure IMDS supporting only few API versions
        """
        supported_api_version = False
        for api_version in SUPPORTED_AZURE_VERSIONS:
            if request.url.endswith(api_version):
                supported_api_version = True

        mock_result = Mock()
        if supported_api_version is False:
            mock_result.status_code = 400
            mock_result.text = (
                '{ "error": "Bad request. api-version is invalid or was not specified in the request." }'
            )
        else:
            mock_result.status_code = 200
            if "/metadata/instance" in request.url:
                mock_result.text = AZURE_SIGNATURE
            elif "/metadata/attested/document" in request.url:
                mock_result.text = AZURE_SIGNATURE
            else:
                mock_result.text = ""

        return mock_result

    @patch("cloud_what.providers.azure.AzureCloudProvider.get_api_versions")
    def test_get_metadata_from_server_outdated_api_version(self, mock_get_api_versions):
        """
        Test getting metadata from server using outdated API version that is not supported
        """

        def _mock_prepare_request(mock_request, *args, **kwargs):
            mock_prepared_request = Mock(spec=["method", "url", "headers"])
            mock_prepared_request.method = mock_request.method
            mock_prepared_request.url = mock_request.url
            mock_prepared_request.headers = mock_request.headers
            return mock_prepared_request

        self.requests_mock.Request = Mock(wraps=requests.Request)
        # We simple mock getting api versions, because this method is tested in another test method
        mock_get_api_versions.return_value = SUPPORTED_AZURE_VERSIONS
        mock_session = Mock()
        mock_session.send = Mock(side_effect=self.mock_send_azure_IMDS)
        mock_session.prepare_request = _mock_prepare_request
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)

        azure_collector = azure.AzureCloudProvider({})
        metadata = azure_collector.get_metadata()

        request_calls = [
            call(
                method="GET",
                headers={"User-Agent": "cloud-what/1.0", "Metadata": "true"},
                url="http://169.254.169.254/metadata/instance?api-version="
                + azure.AzureCloudProvider.API_VERSION,
            ),
            call(
                method="GET",
                headers={"User-Agent": "cloud-what/1.0", "Metadata": "true"},
                url=f"http://169.254.169.254/metadata/instance?api-version={SUPPORTED_AZURE_VERSIONS[-1]}",
            ),
        ]
        self.requests_mock.Request.assert_has_calls(calls=request_calls)
        self.assertEqual(mock_session.send.call_count, 2)
        self.assertIsNotNone(metadata)
