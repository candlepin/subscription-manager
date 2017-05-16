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
#
import os

from contextlib import nested
from mock import Mock, NonCallableMock, patch

from .stubs import StubUEP

from subscription_manager.managercli import RegisterCommand
from subscription_manager import injection as inj
from subscription_manager import cache

from .fixture import SubManFixture, Capture


class CliRegistrationTests(SubManFixture):

    def stub_persist(self, consumer):
        self.persisted_consumer = consumer
        return self.persisted_consumer

    def test_register_persists_consumer_cert(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self.stub_cp_provider.basic_auth_cp = mock_uep

            cmd = RegisterCommand()
            self._inject_mock_invalid_consumer()
            cmd._persist_identity_cert = self.stub_persist

            cmd.main(['register', '--username=testuser1', '--password=password'])
            self.assertEqual('dummy-consumer-uuid', self.persisted_consumer["uuid"])

    def _inject_ipm(self):
        mock_ipm = NonCallableMock(spec=cache.InstalledProductsManager)
        mock_ipm.tags = None
        inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, mock_ipm)
        return mock_ipm

    def test_installed_products_cache_written(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self.stub_cp_provider.basic_auth_cp = mock_uep

            self._inject_mock_invalid_consumer()
            cmd = RegisterCommand()
            cmd._persist_identity_cert = self.stub_persist
            self._inject_ipm()

            cmd.main(['register', '--username=testuser1', '--password=password'])

            # FIXME: test something here...
            # self.assertTrue(mock_ipm_wc.call_count > 0)

    @patch('subscription_manager.managercli.EntCertActionInvoker')
    def test_activation_keys_updates_certs_and_repos(self, mock_entcertlib):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self.stub_cp_provider.basic_auth_cp = mock_uep

            self._inject_mock_invalid_consumer()
            cmd = RegisterCommand()
            cmd._persist_identity_cert = self.stub_persist
            mock_entcertlib_instance = mock_entcertlib.return_value
            self._inject_ipm()

            cmd.main(['register', '--activationkey=test_key', '--org=test_org'])
            self.assertTrue(mock_entcertlib_instance.update.called)

    @patch('subscription_manager.managercli.EntCertActionInvoker')
    def test_consumerid_updates_certs_and_repos(self, mock_entcertlib):
        def get_consumer(self, *args, **kwargs):
            pass

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getConsumer = get_consumer
            self.stub_cp_provider.basic_auth_cp = mock_uep

            self._inject_mock_invalid_consumer()
            cmd = RegisterCommand()
            cmd._persist_identity_cert = self.stub_persist
            mock_entcertlib_instance = mock_entcertlib.return_value
            mock_uep.getConsumer = Mock(return_value={'uuid': '123123', 'type': {'manifest': False}})
            self._inject_ipm()

            cmd.main(['register', '--consumerid=123456', '--username=testuser1', '--password=password', '--org=test_org'])
            self.assertTrue(mock_entcertlib_instance.update.called)
            # self.assertTrue(mock_ipm.write_cache.call_count > 0)

    def test_consumerid_with_distributor_id(self):
        def get_consumer(self, *args, **kwargs):
            pass

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getConsumer = get_consumer
            self.stub_cp_provider.basic_auth_cp = mock_uep

            self._inject_mock_invalid_consumer()
            cmd = RegisterCommand()
            mock_uep.getConsumer = Mock(return_value={'uuid': '123123', 'type': {'manifest': True}, 'idCert': {'key': ''}})
            self._inject_ipm()

            with nested(Capture(silent=True), self.assertRaises(SystemExit)) as e:
                cmd.main(['register', '--consumerid=TaylorSwift', '--username=testuser1', '--password=password', '--org=test_org'])
                self.assertEqual(e.code, os.EX_USAGE)

    def test_strip_username_and_password(self):
        username, password = RegisterCommand._get_username_and_password(" ", " ")
        self.assertEqual(username, "")
        self.assertEqual(password, "")

        username, password = RegisterCommand._get_username_and_password(" Jar Jar ", " Binks ")
        self.assertEqual(username, "Jar Jar")
        self.assertEqual(password, "Binks")

    def test_get_environment_id_none_available(self):
        def env_list(*args, **kwargs):
            return []

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getEnvironmentList = env_list
            mock_uep.supports_resource = Mock(return_value=True)
            self.stub_cp_provider.basic_auth_cp = mock_uep

            rc = RegisterCommand()
            rc.options = Mock()
            rc.options.activation_keys = None
            env_id = rc._get_environment_id(mock_uep, 'owner', None)

            expected = None
            self.assertEqual(expected, env_id)

    def test_get_environment_id_one_available(self):
        def env_list(*args, **kwargs):
            return [{"id": "1234", "name": "somename"}]

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getEnvironmentList = env_list
            mock_uep.supports_resource = Mock(return_value=True)
            self.stub_cp_provider.basic_auth_cp = mock_uep

            rc = RegisterCommand()
            rc.options = Mock()
            rc.options.activation_keys = None
            env_id = rc._get_environment_id(mock_uep, 'owner', None)

            expected = "1234"
            self.assertEqual(expected, env_id)

    def test_get_environment_id_multi_available(self):
        def env_list(*args, **kwargs):
            return [{"id": "1234", "name": "somename"},
                    {"id": "5678", "name": "othername"}]

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getEnvironmentList = env_list
            mock_uep.supports_resource = Mock(return_value=True)
            self.stub_cp_provider.basic_auth_cp = mock_uep

            rc = RegisterCommand()
            rc.options = Mock()
            rc.options.activation_keys = None
            rc._prompt_for_environment = Mock(return_value="othername")
            env_id = rc._get_environment_id(mock_uep, 'owner', None)

            expected = "5678"
            self.assertEqual(expected, env_id)

    def test_get_environment_id_multi_available_bad_name(self):
        def env_list(*args, **kwargs):
            return [{"id": "1234", "name": "somename"},
                    {"id": "5678", "name": "othername"}]

        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.getEnvironmentList = env_list
            mock_uep.supports_resource = Mock(return_value=True)
            self.stub_cp_provider.basic_auth_cp = mock_uep

            rc = RegisterCommand()
            rc.options = Mock()
            rc.options.activation_keys = None
            rc._prompt_for_environment = Mock(return_value="not_an_env")

            with nested(Capture(silent=True), self.assertRaises(SystemExit)):
                rc._get_environment_id(mock_uep, 'owner', None)
