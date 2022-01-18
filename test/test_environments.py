#
# Copyright (c) 2012 Red Hat, Inc.
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
from unittest.mock import patch, Mock

from subscription_manager.managercli import EnvironmentsCommand
from .stubs import StubUEP
from .fixture import SubManFixture, Capture


class CliEnvironmentTests(SubManFixture):

    def setUp(self):
        super(CliEnvironmentTests, self).setUp()
        get_supported_resources_patcher = patch('subscription_manager.managercli.get_supported_resources')
        self.mock_get_resources = get_supported_resources_patcher.start()
        self.mock_get_resources.return_value = ['environments']
        self.addCleanup(self.mock_get_resources.stop)

    def env_list(*args, **kwargs):
        return [{"id": "1234", "name": "somename"},
                {"id": "5678", "name": "othername"}]

    def test_update_environments(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_identity = self._inject_mock_valid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.supports_resource = Mock(return_value=True)
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            serial1 = '1234'
            cmd.main(['--set=somename', '--username', 'foo', '--password', 'bar'])
            cmd.cp.updateConsumer.assert_called_once_with(mock_identity.uuid, environments=serial1)

    def test_update_environments_multiple(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_identity = self._inject_mock_valid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.supports_resource = Mock(return_value=True)
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            serial1 = '1234,5678'
            cmd.main(['--set=somename,othername', '--username', 'foo', '--password', 'bar'])
            cmd.cp.updateConsumer.assert_called_once_with(mock_identity.uuid, environments=serial1)

    def test_update_environments_multiple_handles_spaces(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_identity = self._inject_mock_valid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.supports_resource = Mock(return_value=True)
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            serial1 = '1234,5678'
            cmd.main(['--set=somename, othername', '--username', 'foo', '--password', 'bar'])
            cmd.cp.updateConsumer.assert_called_once_with(mock_identity.uuid, environments=serial1)

    def test_update_environments_repeated(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self._inject_mock_valid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            with Capture(silent=True):
                with self.assertRaises(SystemExit):
                    cmd.main(['--set=somename,othername,somename', '--username', 'foo', '--password', 'bar'])

    def test_update_environments_not_valid(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self._inject_mock_valid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            with Capture(silent=True):
                with self.assertRaises(SystemExit):
                    cmd.main(['--set=somename,notagoodname', '--username', 'foo', '--password', 'bar'])

    def test_update_indentity_not_valid(self):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            self._inject_mock_invalid_consumer()
            mock_uep.getEnvironmentList = self.env_list
            mock_uep.has_capability = Mock(return_value=True)
            mock_uep.updateConsumer = Mock()
            self.stub_cp_provider.basic_auth_cp = mock_uep
            cmd = EnvironmentsCommand()

            with Capture(silent=True):
                with self.assertRaises(SystemExit):
                    cmd.main(['--set=somename', '--username', 'foo', '--password', 'bar'])
