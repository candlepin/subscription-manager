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
Module for testing AWS part of Python package cloud_what
"""

import unittest
from unittest.mock import patch, Mock
import tempfile
import time

from cloud_what.providers import aws


def send_only_imds_v2_is_supported(request, *args, **kwargs):
    """
    Mock result, when we try to get metadata using GET method against
    AWS metadata provider. This mock is for the case, when only IMDSv2
    is supported by instance.
    :param request: HTTP request
    :return: Mock with result
    """
    mock_result = Mock()

    if request.method == "PUT":
        if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_URL:
            if "X-aws-ec2-metadata-token-ttl-seconds" in request.headers:
                mock_result.status_code = 200
                mock_result.text = AWS_TOKEN
            else:
                mock_result.status_code = 400
                mock_result.text = "Error: TTL for token not specified"
        else:
            mock_result.status_code = 400
            mock_result.text = "Error: Invalid URL"
    elif request.method == "GET":
        if "X-aws-ec2-metadata-token" in request.headers.keys():
            if request.headers["X-aws-ec2-metadata-token"] == AWS_TOKEN:
                if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_METADATA_URL:
                    mock_result.status_code = 200
                    mock_result.text = AWS_METADATA
                elif request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_SIGNATURE_URL:
                    mock_result.status_code = 200
                    mock_result.text = AWS_SIGNATURE
                else:
                    mock_result.status_code = 400
                    mock_result.text = "Error: Invalid URL"
            else:
                mock_result.status_code = 400
                mock_result.text = "Error: Invalid metadata token provided"
        else:
            mock_result.status_code = 400
            mock_result.text = "Error: IMDSv1 is not supported on this instance"
    else:
        mock_result.status_code = 400
        mock_result.text = "Error: not supported request method"

    return mock_result


def mock_prepare_request(request):
    return request


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

    def setUp(self) -> None:
        """
        Destroy instance of singleton and set instance not initialized
        """
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False

    def tearDown(self) -> None:
        """
        Clean after each unit test
        """
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False

    def test_aws_instance_is_singleton(self):
        """
        Any subclass of BaseCloudProvider should behave as singleton
        """
        aws_cloud_provider_01 = aws.AWSCloudProvider({})
        self.assertEqual(aws_cloud_provider_01._initialized, True)
        aws_cloud_provider_02 = aws.AWSCloudProvider({})
        self.assertEqual(id(aws_cloud_provider_01), id(aws_cloud_provider_02))

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
        facts = {"virt.is_guest": False, "dmi.bios.version": "cool hardware company"}
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertFalse(is_vm)

    def test_aws_vm_using_xen(self):
        """
        Test for the case, when the vm is running on AWS Xen
        """
        # We will mock facts using simple dictionary
        facts = {"virt.is_guest": True, "virt.host_type": "xen", "dmi.bios.version": "amazon"}
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
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.version": "1.0",
            "dmi.bios.vendor": "Amazon EC2",
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
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.version": "1.0",
            "dmi.bios.vendor": "Foo",
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
        facts = {"virt.is_guest": True, "dmi.system.uuid": "EC2263F8-15F3-4A34-B186-FAD8AB963431"}
        aws_detector = aws.AWSCloudProvider(facts)
        is_vm = aws_detector.is_vm()
        self.assertTrue(is_vm)
        probability = aws_detector.is_likely_running_on_cloud()
        self.assertEqual(probability, 0.1)

    @patch("cloud_what._base_provider.requests.Session")
    def test_get_metadata_from_server_imds_v1(self, mock_session_class):
        """
        Test the case, when metadata are obtained from server using IMDSv1
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AWS_METADATA
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        mock_session_class.return_value = mock_session
        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_metadata_from_cache = Mock(return_value=None)
        metadata = aws_collector.get_metadata()
        self.assertEqual(metadata, AWS_METADATA)

    @patch("cloud_what._base_provider.requests.Session")
    def test_get_signature_from_server_imds_v1(self, mock_session_class):
        """
        Test the case, when metadata are obtained from server using IMDSv1
        """
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = AWS_SIGNATURE
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        mock_session_class.return_value = mock_session

        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_signature_from_cache = Mock(return_value=None)
        test_signature = aws_collector.get_signature()
        signature = "-----BEGIN PKCS7-----\n" + AWS_SIGNATURE + "\n-----END PKCS7-----"
        self.assertEqual(signature, test_signature)

    @patch("cloud_what._base_provider.requests.Session")
    def test_get_metadata_from_server_imds_v2(self, mock_session_class):
        """
        Test the case, when metadata are obtained from server using IMDSv2
        """
        mock_session = Mock()
        mock_session.send = send_only_imds_v2_is_supported
        mock_session.prepare_request = Mock(side_effect=mock_prepare_request)
        mock_session.hooks = {"response": []}
        mock_session_class.return_value = mock_session

        aws_provider = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_provider._get_metadata_from_cache = Mock(return_value=None)
        # Mock that no token cache exists
        aws_provider._get_token_from_cache_file = Mock(return_value=None)
        # Mock writing token to cache file
        aws_provider._write_token_to_cache_file = Mock()
        # Mock getting metadata using IMDSv1 is disabled by user
        aws_provider._get_metadata_from_server_imds_v1 = Mock(return_value=None)

        metadata = aws_provider.get_metadata()
        self.assertEqual(metadata, AWS_METADATA)

    @patch("cloud_what._base_provider.requests.Session")
    def test_get_signature_from_server_imds_v2(self, mock_session_class):
        """
        Test the case, when signature is obtained from server using IMDSv2
        """
        mock_session = Mock()
        mock_session.send = send_only_imds_v2_is_supported
        mock_session.prepare_request = Mock(side_effect=mock_prepare_request)
        mock_session.hooks = {"response": []}
        mock_session_class.return_value = mock_session

        aws_collector = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_collector._get_metadata_from_cache = Mock(return_value=None)
        # Mock that no token cache exists
        aws_collector._get_token_from_cache_file = Mock(return_value=None)
        # Mock writing token to cache file
        aws_collector._write_token_to_cache_file = Mock()

        test_signature = aws_collector.get_signature()
        signature = "-----BEGIN PKCS7-----\n" + AWS_SIGNATURE + "\n-----END PKCS7-----"
        self.assertEqual(signature, test_signature)

    @patch("cloud_what._base_provider.requests.Session")
    def test_metadata_in_memory_cache(self, mock_session_class):
        """
        Test that metadata is read from in-memory cache
        """
        # First mock reading metadata from server
        mock_session = Mock()
        mock_session.send = Mock(side_effect=send_only_imds_v2_is_supported)
        mock_session.prepare_request = Mock(side_effect=mock_prepare_request)
        mock_session.hooks = {"response": []}
        mock_session_class.return_value = mock_session

        aws_provider = aws.AWSCloudProvider({})
        # Mock that no metadata cache exists
        aws_provider._get_metadata_from_cache = Mock(return_value=None)
        # Mock that no token cache exists
        aws_provider._get_token_from_cache_file = Mock(return_value=None)
        # Mock writing token to cache file
        aws_provider._write_token_to_cache_file = Mock()
        # Mock getting metadata using IMDSv1 is disabled by user
        aws_provider._get_metadata_from_server_imds_v1 = Mock(return_value=None)

        # Try to get metadata from server
        metadata = aws_provider.get_metadata()

        self.assertEqual(metadata, AWS_METADATA)
        # There should be two calls to IMDS server (put and get)
        self.assertEqual(mock_session.send.call_count, 2)

        # Test that metadata are stored in in-memory cache
        self.assertEqual(metadata, aws_provider._cached_metadata)

        # Try to get metadata once again
        new_metadata = aws_provider.get_metadata()

        # Metadata have to be still the same
        self.assertEqual(new_metadata, AWS_METADATA)
        # There should not be more calls to IMDS server
        # (still only two calls from previous communication)
        self.assertEqual(mock_session.send.call_count, 2)

    def test_reading_valid_cached_token(self):
        """
        Test reading of valid cached token from file
        """
        c_time = str(time.time())
        ttl = str(aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_TTL)
        token = "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="
        valid_token = (
            '{\
  "ctime": "'
            + c_time
            + '",\
  "ttl": "'
            + ttl
            + '",\
  "token": "'
            + token
            + '"\
}'
        )
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding="utf-8"))
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
        token = "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="
        valid_token = (
            '{[\
  "ctime": "'
            + c_time
            + '",\
  "ttl": "'
            + ttl
            + '",\
  "token": "'
            + token
            + '"\
}]'
        )
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding="utf-8"))
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
        token = "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="
        # ctime has to be float (unix epoch)
        valid_token = (
            '{[\
  "ctime": "Wed Dec 16 16:31:36 CET 2020",\
  "ttl": "'
            + ttl
            + '",\
  "token": "'
            + token
            + '"\
}]'
        )
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding="utf-8"))
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
            tmp_token_file.write(bytes(valid_token, encoding="utf-8"))
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
        valid_token = (
            '{\
  "ctime": "'
            + c_time
            + '",\
  "ttl": "'
            + ttl
            + '",\
  "token": "ABCDEFGHy0hY_y8D7e95IIx7aP2bmnzddz0tIV56yZY9oK00F8GUPQ=="\
}'
        )
        aws_collector = aws.AWSCloudProvider({})
        # Create mock of cached toke file
        with tempfile.NamedTemporaryFile() as tmp_token_file:
            # Create valid token file
            tmp_token_file.write(bytes(valid_token, encoding="utf-8"))
            tmp_token_file.flush()
            old_token_cache_file = aws_collector.TOKEN_CACHE_FILE
            aws_collector.TOKEN_CACHE_FILE = tmp_token_file.name
            test_token = aws_collector._get_token_from_cache_file()
            self.assertEqual(test_token, None)
            aws_collector.TOKEN_CACHE_FILE = old_token_cache_file
