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
#
import os

from mock import Mock, NonCallableMock, patch, MagicMock

from .stubs import StubUEP

from subscription_manager.managercli import RegisterCommand
from subscription_manager import injection as inj
from subscription_manager import cache
from subscription_manager.identity import ConsumerIdentity

from .fixture import SubManFixture, Capture, set_up_mock_sp_store

from rhsmlib.services.register import RegisterService
from rhsmlib.services import exceptions


class CliRegistrationTests(SubManFixture):
    def setUp(self):
        super(CliRegistrationTests, self).setUp()
        register_patcher = patch('subscription_manager.managercli.register.RegisterService',
            spec=RegisterService)
        self.mock_register = register_patcher.start().return_value
        self.mock_register.register.return_value = MagicMock(name="MockConsumer")
        self.addCleanup(register_patcher.stop)

        identity_patcher = patch('subscription_manager.managercli.identity.ConsumerIdentity',
            spec=ConsumerIdentity)
        self.mock_consumer_identity = identity_patcher.start().return_value
        self.addCleanup(identity_patcher.stop)

        from subscription_manager import syspurposelib

        self.syspurposelib = syspurposelib
        self.syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

        syspurpose_patch = patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def _inject_ipm(self):
        mock_ipm = NonCallableMock(spec=cache.InstalledProductsManager)
        mock_ipm.tags = None
        inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, mock_ipm)
        return mock_ipm

    @patch('subscription_manager.managercli.EntCertActionInvoker')
    def test_activation_keys_updates_certs_and_repos(self, mock_entcertlib):
        self.stub_cp_provider.basic_auth_cp = Mock('rhsm.connection.UEPConnection', new_callable=StubUEP)
        self._inject_mock_invalid_consumer()

        cmd = RegisterCommand()
        mock_entcertlib = mock_entcertlib.return_value
        self._inject_ipm()

        cmd.main(['register', '--activationkey=test_key', '--org=test_org'])
        self.mock_register.register.assert_called_once()
        mock_entcertlib.update.assert_called_once()

    @patch('subscription_manager.managercli.EntCertActionInvoker')
    def test_consumerid_updates_certs_and_repos(self, mock_entcertlib):
        self.stub_cp_provider.basic_auth_cp = Mock('rhsm.connection.UEPConnection', new_callable=StubUEP)
        self._inject_mock_invalid_consumer()

        cmd = RegisterCommand()
        mock_entcertlib = mock_entcertlib.return_value
        self._inject_ipm()

        cmd.main(['register', '--consumerid=123456', '--username=testuser1', '--password=password', '--org=test_org'])
        self.mock_register.register.assert_called_once_with(None, consumerid='123456')
        mock_entcertlib.update.assert_called_once()

    def test_consumerid_with_distributor_id(self):
        self.stub_cp_provider.basic_auth_cp = Mock('rhsm.connection.UEPConnection', new_callable=StubUEP)

        self._inject_mock_invalid_consumer()
        cmd = RegisterCommand()
        self._inject_ipm()
        self.mock_register.register.side_effect = exceptions.ServiceError()

        with Capture(silent=True):
            with self.assertRaises(SystemExit) as e:
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

            with Capture(silent=True):
                with self.assertRaises(SystemExit):
                    rc._get_environment_id(mock_uep, 'owner', None)

    def test_deprecate_consumer_type(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self.stub_cp_provider.basic_auth_cp = mock_uep

            cmd = RegisterCommand()
            self._inject_mock_invalid_consumer()

            with Capture(silent=True):
                with self.assertRaises(SystemExit) as e:
                    cmd.main(['register', '--type=candlepin'])
                    self.assertEqual(e.code, os.EX_USAGE)
