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
from mock import Mock, patch

from stubs import StubUEP
import rhsm.connection as connection
from subscription_manager.managercli import RegisterCommand
from fixture import SubManFixture


class CliRegistrationTests(SubManFixture):

    def stub_persist(self, consumer):
        self.persisted_consumer = consumer
        return self.persisted_consumer

    @patch('subscription_manager.certlib.ConsumerIdentity.exists')
    def test_register_persists_consumer_cert(self, mock_exists):
        connection.UEPConnection = StubUEP

        # When
        cmd = RegisterCommand()

        mock_exists.return_value = False
        cmd._persist_identity_cert = self.stub_persist
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()
        cmd.installed_mgr.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        # Then
        self.assertEqual('dummy-consumer-uuid', self.persisted_consumer["uuid"])

    @patch('subscription_manager.certlib.ConsumerIdentity.exists')
    def test_installed_products_cache_written(self, mock_exists):
        connection.UEPConnection = StubUEP

        cmd = RegisterCommand()
        cmd._persist_identity_cert = self.stub_persist
        mock_exists.return_value = False

        # Mock out facts and installed products:
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()
        cmd.installed_mgr.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        self.assertEquals(1, cmd.installed_mgr.write_cache.call_count)
