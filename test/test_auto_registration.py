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
from mock import patch, Mock

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


def send_only_imds_v2_is_supported(request, *args, **kwargs):
    """
    Mock result, when we try to get metadata using GET method against
    AWS metadata provider. This mock is for the case, when only IMDSv2
    is supported by instance.
    :param request: HTTP request
    :return: Mock with result
    """
    mock_result = Mock()

    if request.method == 'PUT':
        if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_TOKEN_URL:
            if 'X-aws-ec2-metadata-token-ttl-seconds' in request.headers:
                mock_result.status_code = 200
                mock_result.text = AWS_TOKEN
            else:
                mock_result.status_code = 400
                mock_result.text = 'Error: TTL for token not specified'
        else:
            mock_result.status_code = 400
            mock_result.text = 'Error: Invalid URL'
    elif request.method == 'GET':
        if 'X-aws-ec2-metadata-token' in request.headers.keys():
            if request.headers['X-aws-ec2-metadata-token'] == AWS_TOKEN:
                if request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_METADATA_URL:
                    mock_result.status_code = 200
                    mock_result.text = AWS_METADATA
                elif request.url == aws.AWSCloudProvider.CLOUD_PROVIDER_SIGNATURE_URL:
                    mock_result.status_code = 200
                    mock_result.text = AWS_SIGNATURE
                else:
                    mock_result.status_code = 400
                    mock_result.text = 'Error: Invalid URL'
            else:
                mock_result.status_code = 400
                mock_result.text = 'Error: Invalid metadata token provided'
        else:
            mock_result.status_code = 400
            mock_result.text = 'Error: IMDSv1 is not supported on this instance'
    else:
        mock_result.status_code = 400
        mock_result.text = 'Error: not supported request method'

    return mock_result


def mock_prepare_request(request):
    return request


class TestAutomaticRegistration(unittest.TestCase):

    def setUp(self):
        aws.AWSCloudProvider._instance = None
        aws.AWSCloudProvider._initialized = False
        azure.AzureCloudProvider._instance = None
        azure.AzureCloudProvider._initialized = False
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

    @patch('cloud_what.providers.aws.requests.Session')
    def test_collect_cloud_info_one_cloud_provider_detected(self, mock_session_class):
        """
        Test the case, when we try to collect cloud info only for
        one detected cloud provider
        """
        mock_session = Mock()
        mock_session.send = send_only_imds_v2_is_supported
        mock_session.prepare_request = Mock(side_effect=mock_prepare_request)
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session

        cloud_list = ['aws']
        cloud_info = _collect_cloud_info(cloud_list, Mock())

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

    @patch('cloud_what.providers.aws.requests.Session')
    def test_collect_cloud_info_more_cloud_providers_detected(self, mock_session_class):
        """
        Test the case, when we try to collect cloud info only for
        more than one cloud providers, because more than one cloud
        providers were detected
        """
        mock_session = Mock()
        mock_session.send = send_only_imds_v2_is_supported
        mock_session.prepare_request = Mock(side_effect=mock_prepare_request)
        mock_session.hooks = {'response': []}
        mock_session_class.return_value = mock_session

        # More cloud providers detected
        cloud_list = ['azure', 'aws']

        cloud_info = _collect_cloud_info(cloud_list, Mock())

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
