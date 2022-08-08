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
Module for testing GCP part of Python package cloud_what
"""

import unittest
from mock import patch, Mock
import json

from cloud_what.providers import gcp


GCP_JWT_TOKEN = """eyJhbGciOiJSUzI1NiIsImtpZCI6IjZhOGJhNTY1MmE3MDQ0MTIxZDRmZWR\
hYzhmMTRkMTRjNTRlNDg5NWIiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJodHRwczovL3N1YnNjcmlwdG\
lvbi5yaHNtLnJlZGhhdC5jb206NDQzL3N1YnNjcmlwdGlvbiIsImF6cCI6IjEwNDA3MDk1NTY4MjI5\
ODczNjE0OSIsImVtYWlsIjoiMTYxOTU4NDY1NjEzLWNvbXB1dGVAZGV2ZWxvcGVyLmdzZXJ2aWNlYW\
Njb3VudC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZXhwIjoxNjE2NTk5ODIzLCJnb29nbGUi\
OnsiY29tcHV0ZV9lbmdpbmUiOnsiaW5zdGFuY2VfY3JlYXRpb25fdGltZXN0YW1wIjoxNjE2NTk1OD\
Q3LCJpbnN0YW5jZV9pZCI6IjI1ODkyMjExNDA2NzY3MTgwMjYiLCJpbnN0YW5jZV9uYW1lIjoiaW5z\
dGFuY2UtMSIsImxpY2Vuc2VfaWQiOlsiNTczMTAzNTA2NzI1NjkyNTI5OCJdLCJwcm9qZWN0X2lkIj\
oiZmFpci1raW5nZG9tLTMwODUxNCIsInByb2plY3RfbnVtYmVyIjoxNjE5NTg0NjU2MTMsInpvbmUi\
OiJ1cy1lYXN0MS1iIn19LCJpYXQiOjE2MTY1OTYyMjMsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ2\
9vZ2xlLmNvbSIsInN1YiI6IjEwNDA3MDk1NTY4MjI5ODczNjE0OSJ9.XQKeqMAvsH2T2wsdN97jlm5\
2DzLfix3DTMCu9QCuhSKLEk1xHYOYtvh5Yzn7j-tbZtV-siyPAfpGZO3Id87573OVGgohN3q7Exlf9\
CEIHa1-X7zLyiyIlyrnfQJ1aGHeH6y7gb_tWxHFLJRzhulfkfJxSDn5fEBSgBqbjzCr9unQgMkuzQ3\
uui2BbIbALmOpY6D-IT71mgMDZ_zm4G6q-Mh0nIMkDWhmQ8pa3RAVqqBMBYJninKLdCD8eQzIlDhtI\
zwmYGLrsJMktFF3pJFCqEFv1rKZy_OUyV4JOkOLtXbKnwxqmFTq-2SP0KtUWjDy1-U8GnVDptISjOf\
2O9FaLA
"""

GCP_JOSE_HEADER = '{"alg":"RS256","kid":"6a8ba5652a7044121d4fedac8f14d14c54e4895b","typ":"JWT"}'

GCP_METADATA = (
    '{"aud":"https://subscription.rhsm.redhat.com:443/subscription",'
    '"azp":"104070955682298736149","email":"161958465613-compute@developer.gserviceaccount.com",'
    '"email_verified":true,"exp":1616599823,"google":{"compute_engine":{'
    '"instance_creation_timestamp":1616595847,"instance_id":"2589221140676718026",'
    '"instance_name":"instance-1","license_id":["5731035067256925298"],'
    '"project_id":"fair-kingdom-308514","project_number":161958465613,"zone":"us-east1-b"}},'
    '"iat":1616596223,"iss":"https://accounts.google.com","sub":"104070955682298736149"}'
)

GCP_SIGNATURE = """XQKeqMAvsH2T2wsdN97jlm52DzLfix3DTMCu9QCuhSKLEk1xHYOYtvh5Yzn\
7j-tbZtV-siyPAfpGZO3Id87573OVGgohN3q7Exlf9CEIHa1-X7zLyiyIlyrnfQJ1aGHeH6y7gb_tW\
xHFLJRzhulfkfJxSDn5fEBSgBqbjzCr9unQgMkuzQ3uui2BbIbALmOpY6D-IT71mgMDZ_zm4G6q-Mh\
0nIMkDWhmQ8pa3RAVqqBMBYJninKLdCD8eQzIlDhtIzwmYGLrsJMktFF3pJFCqEFv1rKZy_OUyV4JO\
kOLtXbKnwxqmFTq-2SP0KtUWjDy1-U8GnVDptISjOf2O9FaLA
==="""


class TestGCPCloudProvider(unittest.TestCase):
    """
    Class used for testing detector of GCP
    """

    def setUp(self):
        """
        Patch communication with metadata provider
        """
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False
        requests_patcher = patch("cloud_what._base_provider.requests")
        self.requests_mock = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

    def tearDown(self):
        """
        Clean after each unit test
        """
        gcp.GCPCloudProvider._instance = None
        gcp.GCPCloudProvider._initialized = False

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
        facts = {"virt.is_guest": False, "dmi.bios.version": "cool hardware company"}
        gcp_detector = gcp.GCPCloudProvider(facts)
        is_vm = gcp_detector.is_vm()
        self.assertFalse(is_vm)

    def test_gcp_vm(self):
        """
        Test for the case, when the vm is running on GCP
        """
        # We will mock facts using simple dictionary
        facts = {
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.version": "Google",
            "dmi.bios.vendor": "Google",
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
            "virt.is_guest": True,
            "virt.host_type": "kvm",
            "dmi.bios.version": "1.0",
            "dmi.bios.vendor": "Foo",
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
        self.requests_mock.Request = Mock()
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = GCP_JWT_TOKEN
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)

        gcp_collector = gcp.GCPCloudProvider({})
        gcp_collector._get_token_from_cache_file = Mock(return_value=None)
        gcp_collector._write_token_to_cache_file = Mock(return_value=None)
        token = gcp_collector.get_metadata()
        self.requests_mock.Request.assert_called_once_with(
            method="GET",
            url="http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?"
            "audience=https://subscription.rhsm.redhat.com:443/subscription&format=full&licenses=TRUE",
            headers={"User-Agent": "cloud-what/1.0", "Metadata-Flavor": "Google"},
        )
        self.assertEqual(token, GCP_JWT_TOKEN)

    def test_get_token_custom_audience(self):
        """
        Test getting GCP token, when custom audience URL is used (e.g. Satellite or stage is used)
        """
        self.requests_mock.Request = Mock()
        mock_result = Mock()
        mock_result.status_code = 200
        mock_result.text = GCP_JWT_TOKEN
        mock_session = Mock()
        mock_session.send = Mock(return_value=mock_result)
        mock_session.prepare_request = Mock()
        mock_session.hooks = {"response": []}
        self.requests_mock.Session = Mock(return_value=mock_session)
        gcp_collector = gcp.GCPCloudProvider({}, audience_url="https://example.com:8443/rhsm")
        gcp_collector._get_token_from_cache_file = Mock(return_value=None)
        gcp_collector._write_token_to_cache_file = Mock(return_value=None)
        token = gcp_collector.get_metadata()
        self.requests_mock.Request.assert_called_once_with(
            method="GET",
            url="http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?"
            "audience=https://example.com:8443/rhsm&format=full&licenses=TRUE",
            headers={"User-Agent": "cloud-what/1.0", "Metadata-Flavor": "Google"},
        )
        mock_session.send.assert_called_once()
        self.assertEqual(token, GCP_JWT_TOKEN)

    def test_decode_jwt(self):
        """
        Test decoding of JWT token
        """

        gcp_collector = gcp.GCPCloudProvider(
            {}, audience_url="https://subscription.rhsm.redhat.com:443/subscription"
        )
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

        jwt_token = "foobar.foobar.foobar"
        gcp_collector = gcp.GCPCloudProvider({})

        jose_header_str, metadata_str, encoded_signature = gcp_collector.decode_jwt(jwt_token)

        self.assertIsNone(jose_header_str)
        self.assertIsNone(metadata_str)

    def test_decoding_jwt_wrong_section_number(self):
        """
        Test decoding of JWT token with wrong number of sections
        """
        # There are only two sections
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE1MTYyMzkwMjJ9"
        gcp_collector = gcp.GCPCloudProvider({})

        jose_header_str, metadata_str, encoded_signature = gcp_collector.decode_jwt(jwt_token)

        self.assertIsNone(jose_header_str)
        self.assertIsNone(metadata_str)
