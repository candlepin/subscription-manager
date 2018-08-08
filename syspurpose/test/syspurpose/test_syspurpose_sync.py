# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
#
# Copyright (c) 2018 Red Hat, Inc.
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

from mock import Mock, patch
import io
import os
from .base import SyspurposeTestBase
from syspurpose import sync, utils, files


class SyspurposeStoreTests(SyspurposeTestBase):

    def test_not_created_sync_object_without_rhsm(self):
        """Test that SyncpurposeSync() will raise exception, when rhsm module is not available"""
        with patch("syspurpose.sync.rhsm", None) as mock_rhsm:
            self.assertRaises(ImportError, sync.SyspurposeSync)

    @patch("syspurpose.sync.rhsm")
    def test_create_sync_object_with_all_proxy_settings(self, mock_rhsm):
        """Test creating SyspurposeSync with all arguments"""
        mock_rhsm.config = Mock
        mock_rhsm.config.DEFAULT_PROXY_PORT = "3128"
        mock_rhsm.config.initConfig = Mock()
        syspurpose_sync = sync.SyspurposeSync("proxy.example.com", "1234", "user", "secret")
        self.assertEqual(syspurpose_sync.proxy_server, "proxy.example.com")
        self.assertEqual(syspurpose_sync.proxy_port, "1234")
        self.assertEqual(syspurpose_sync.proxy_user, "user")
        self.assertEqual(syspurpose_sync.proxy_pass, "secret")

    @patch("syspurpose.sync.rhsm")
    def test_create_sync_object_with_rhsm_only_proxy_server(self, mock_rhsm):
        mock_rhsm.config = Mock()
        mock_rhsm.config.DEFAULT_PROXY_PORT = "3128"
        mock_rhsm.config.initConfig = Mock()
        syspurpose_sync = sync.SyspurposeSync("proxy.example.com")
        self.assertEqual(syspurpose_sync.proxy_port, "3128")

    @patch("syspurpose.sync.rhsm")
    def test_create_sync_object_with_rhsm_no_args(self, mock_rhsm):
        mock_rhsm.config.initConfig = Mock()
        mock_rhsm.config.initConfig.return_value = Mock()
        mock_config = mock_rhsm.config.initConfig.return_value

        def rhsm_config_get(section, key):
            config_proxy_settings = {
                "proxy_hostname": "proxy.example.com",
                "proxy_port": "1234",
                "proxy_user": "user",
                "proxy_password": "secret"
            }
            return config_proxy_settings[key]

        mock_config.get = rhsm_config_get
        syspurpose_sync = sync.SyspurposeSync()
        self.assertEqual(syspurpose_sync.proxy_server, "proxy.example.com")
        self.assertEqual(syspurpose_sync.proxy_port, "1234")
        self.assertEqual(syspurpose_sync.proxy_user, "user")
        self.assertEqual(syspurpose_sync.proxy_pass, "secret")

    @patch("syspurpose.sync.rhsm")
    def test_sync_object_update_consumer_set_data(self, mock_rhsm):
        # Mocking of rhsm.config
        mock_rhsm.config = Mock()
        mock_rhsm.config.DEFAULT_PROXY_PORT = "3128"
        mock_rhsm.config.initConfig = Mock()
        instance_config = mock_rhsm.config.initConfig.return_value
        instance_config.get = Mock(return_value="/path/to/cert")
        # Mocking of rhsm.connection
        mock_rhsm.connection = Mock()
        mock_rhsm.connection.UEPConnection = Mock()
        instance_uep_connection = mock_rhsm.connection.UEPConnection.return_value
        instance_uep_connection.updateConsumer = Mock()
        # Mocking of rhsm.certificate
        mock_rhsm.certificate = Mock()
        mock_rhsm.certificate.create_from_file = Mock()
        instance_certificate = mock_rhsm.certificate.create_from_file.return_value
        instance_certificate.subject = Mock()
        instance_certificate.subject.get = Mock(return_value="9d4778ae-80fe-4eed-a631-6be35fded7fe")

        syspurpose_sync = sync.SyspurposeSync("proxy.example.com", "1234", "user", "secret")

        temp_file = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {
            "role": "foo-role",
            "service_level_agreement": "foo-sla",
            "addons": ["foo-addon", "bar-addon"],
            "usage": "foo-usage"
        }
        with io.open(temp_file, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = files.SyspurposeStore(temp_file)
        syspurpose_store.contents = dict(**test_data)

        syspurpose_sync.send_syspurpose_to_candlepin(syspurpose_store)

        instance_uep_connection.updateConsumer.assert_called_once_with(
            uuid="9d4778ae-80fe-4eed-a631-6be35fded7fe",
            role="foo-role",
            service_level="foo-sla",
            addons=["foo-addon", "bar-addon"],
            usage="foo-usage"
        )

    @patch("syspurpose.sync.rhsm")
    def test_sync_object_update_consumer_unset_data(self, mock_rhsm):
        # Mocking of rhsm.config
        mock_rhsm.config = Mock()
        mock_rhsm.config.DEFAULT_PROXY_PORT = "3128"
        mock_rhsm.config.initConfig = Mock()
        instance_config = mock_rhsm.config.initConfig.return_value
        instance_config.get = Mock(return_value="/path/to/cert")
        # Mocking of rhsm.connection
        mock_rhsm.connection = Mock()
        mock_rhsm.connection.UEPConnection = Mock()
        instance_uep_connection = mock_rhsm.connection.UEPConnection.return_value
        instance_uep_connection.updateConsumer = Mock()
        # Mocking of rhsm.certificate
        mock_rhsm.certificate = Mock()
        mock_rhsm.certificate.create_from_file = Mock()
        instance_certificate = mock_rhsm.certificate.create_from_file.return_value
        instance_certificate.subject = Mock()
        instance_certificate.subject.get = Mock(return_value="9d4778ae-80fe-4eed-a631-6be35fded7fe")

        syspurpose_sync = sync.SyspurposeSync("proxy.example.com", "1234", "user", "secret")

        temp_file = os.path.join(self._mktmp(), 'syspurpose_file.json')
        test_data = {}
        with io.open(temp_file, 'w', encoding='utf-8') as f:
            utils.write_to_file_utf8(f, test_data)

        syspurpose_store = files.SyspurposeStore(temp_file)
        syspurpose_store.contents = dict(**test_data)

        syspurpose_sync.send_syspurpose_to_candlepin(syspurpose_store)

        instance_uep_connection.updateConsumer.assert_called_once_with(
            uuid="9d4778ae-80fe-4eed-a631-6be35fded7fe",
            role="",
            service_level="",
            addons=[""],
            usage=""
        )