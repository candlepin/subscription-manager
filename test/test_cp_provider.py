from __future__ import print_function, division, absolute_import

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
#

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import patch

from subscription_manager.cp_provider import CPProvider


class CPProviderTests(unittest.TestCase):
    """
    Test case used for testing method in CPProvider (provider of connection to Candlepin server)
    """

    def setUp(self):
        """
        Initialization before each test
        """
        self.cp_provider = CPProvider()

    def test_create_cp_provider(self):
        """
        Simple test of creating instance
        """
        self.assertIsNotNone(self.cp_provider)

    def test_cert_file_is_not_none(self):
        """
        Test that cp_provider is not created without default cert file
        """
        self.assertEqual(self.cp_provider.cert_file, '/etc/pki/consumer/cert.pem')

    def test_key_file_is_not_none(self):
        """
        Test that cp_provider is not created without default key file
        """
        self.assertEqual(self.cp_provider.key_file, '/etc/pki/consumer/key.pem')

    def test_get_consumer_auth_cp(self):
        """
        Test of getting connection to candlepin server using consumer certificate
        """
        connection = self.cp_provider.get_consumer_auth_cp()
        self.assertIsNotNone(connection)

    @patch('subscription_manager.cp_provider.utils.get_client_versions')
    def test_consumer_auth_setting_user_agent_version(self, mock_client_version):
        mock_client_version.return_value = {
            'subscription-manager': '1.23.45'
        }
        connection = self.cp_provider.get_consumer_auth_cp()
        self.assertTrue('subscription-manager/1.23.45' in connection.conn.user_agent)

    def test_get_basic_auth_cp(self):
        """
        Test of getting connection to candlepin server using username/password
        """
        self.cp_provider.set_user_pass(username='admin', password='admin')
        connection = self.cp_provider.get_basic_auth_cp()
        self.assertIsNotNone(connection)

    @patch('subscription_manager.cp_provider.utils.get_client_versions')
    def test_basic_auth_setting_user_agent_version(self, mock_client_version):
        mock_client_version.return_value = {
            'subscription-manager': '1.23.45'
        }
        self.cp_provider.set_user_pass(username='admin', password='admin')
        connection = self.cp_provider.get_basic_auth_cp()
        self.assertTrue('subscription-manager/1.23.45' in connection.conn.user_agent)

    def test_get_no_auth_cp(self):
        """
        Test of getting connection to candlepin server not using authentication
        """
        connection = self.cp_provider.get_no_auth_cp()
        self.assertIsNotNone(connection)

    @patch('subscription_manager.cp_provider.utils.get_client_versions')
    def test_no_auth_setting_user_agent_version(self, mock_client_version):
        mock_client_version.return_value = {
            'subscription-manager': '1.23.45'
        }
        connection = self.cp_provider.get_no_auth_cp()
        self.assertTrue('subscription-manager/1.23.45' in connection.conn.user_agent)

    def test_get_content_conn(self):
        """
        Test of getting connection to content server (yum repository)
        """
        self.cp_provider.set_content_connection_info(cdn_hostname=None, cdn_port=None)
        connection = self.cp_provider.get_content_connection()
        self.assertIsNotNone(connection)

    @patch('subscription_manager.cp_provider.utils.get_client_versions')
    def test_content_conn_setting_user_agent_version(self, mock_client_version):
        mock_client_version.return_value = {
            'subscription-manager': '1.23.45'
        }
        self.cp_provider.set_content_connection_info(cdn_hostname=None, cdn_port=None)
        connection = self.cp_provider.get_content_connection()
        self.assertTrue('subscription-manager/1.23.45' in connection.conn.user_agent)
