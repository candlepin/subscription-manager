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
Module for testing automatic registration on public cloud
"""

import unittest
import base64
from unittest.mock import Mock

from subscription_manager.scripts.rhsmcertd_worker import _collect_cloud_info
from .rhsmlib_test.test_cloud_facts import AWS_METADATA
from cloud_what.providers import aws, azure, gcp

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


def send__aws_imdsv2_only(request, *args, **kwargs):
    """
    Mock result for metadata request on AWS where only IMDSv2 is supported.
    This function should be used to replace function `requests.Session.send()`.

    :param request: HTTP request
    :return: Mocked server result.
    """
    result = Mock()

    if request.method == "PUT":
        if request.url != aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_URL:
            result.status_code = 400
            result.text = "Error: Invalid URL"
            return result

        if "X-aws-ec2-metadata-token-ttl-seconds" not in request.headers:
            result.status_code = 400
            result.text = "Error: TTL for token not specified"
            return result

        result.status_code = 200
        result.text = AWS_TOKEN
        return result

    if request.method == "GET":
        if "X-aws-ec2-metadata-token" not in request.headers.keys():
            result.status_code = 400
            result.text = "Error: IMDSv1 is not supported on this instance"
            return result

        if request.headers["X-aws-ec2-metadata-token"] != AWS_TOKEN:
            result.status_code = 400
            result.text = "Error: Invalid metadata token provided"
            return result

        if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_METADATA_URL:
            result.status_code = 200
            result.text = AWS_METADATA
            return result

        if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_SIGNATURE_URL:
            result.status_code = 200
            result.text = AWS_SIGNATURE
            return result

        result.status_code = 400
        result.text = "Error: Invalid URL"
        return result

    result.status_code = 400
    result.text = "Error: not supported request method"
    return result


class TestAutomaticRegistration(unittest.TestCase):
    def setUp(self):
        _ = aws.AWSCloudProvider({})
        aws.AWSCloudProvider._instance._get_metadata_from_cache = Mock(return_value=None)
        aws.AWSCloudProvider._instance._get_token_from_cache_file = Mock(return_value=None)
        aws.AWSCloudProvider._instance._write_token_to_cache_file = Mock()

        _ = azure.AzureCloudProvider({})
        azure.AzureCloudProvider._instance._get_metadata_from_cache = Mock(return_value=None)
        azure.AzureCloudProvider._instance.get_api_versions = Mock(return_value="")

    def tearDown(self):
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

    def test_collect_cloud_info_one_cloud_provider_detected(self):
        """
        Test the case, when we try to collect cloud info only for
        one detected cloud provider
        """
        mock_session = Mock()
        mock_session.send = send__aws_imdsv2_only
        mock_session.prepare_request = Mock(side_effect=lambda request: request)
        mock_session.hooks = {"response": []}
        aws.AWSCloudProvider._instance._session = mock_session

        cloud_list = ['aws']
        cloud_info = _collect_cloud_info(cloud_list)

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
        self.assertTrue("signature" in cloud_info)
        b64_signature = cloud_info["signature"]
        signature = base64.b64decode(b64_signature).decode("utf-8")
        self.assertEqual(signature, "-----BEGIN PKCS7-----\n" + AWS_SIGNATURE + "\n-----END PKCS7-----")

    def test_collect_cloud_info_more_cloud_providers_detected(self):
        """
        Test the case, when we try to collect cloud info only for
        more than one cloud providers, because more than one cloud
        providers were detected
        """
        mock_session = Mock()
        mock_session.send = send__aws_imdsv2_only
        mock_session.prepare_request = Mock(side_effect=lambda request: request)
        mock_session.hooks = {"response": []}
        aws.AWSCloudProvider._instance._session = mock_session
        azure.AzureCloudProvider._instance._session = Mock()

        # More cloud providers detected
        cloud_list = ['azure', 'aws']

        cloud_info = _collect_cloud_info(cloud_list)

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
