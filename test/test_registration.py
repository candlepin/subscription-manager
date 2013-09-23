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
from mock import Mock, NonCallableMock, patch

from stubs import StubUEP, StubProductCertificate, StubProduct
from stubs import StubUEP

import rhsm.connection as connection

from subscription_manager.managercli import RegisterCommand
from subscription_manager import injection as inj
from subscription_manager import cache

from fixture import SubManFixture

import subscription_manager.injection as inj


class CliRegistrationTests(SubManFixture):

    def stub_persist(self, consumer):
        self.persisted_consumer = consumer
        return self.persisted_consumer

    def test_register_persists_consumer_cert(self):
        connection.UEPConnection = StubUEP

        # When
        cmd = RegisterCommand()

        self._inject_mock_invalid_consumer()

        cmd._persist_identity_cert = self.stub_persist
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        # Then
        self.assertEqual('dummy-consumer-uuid', self.persisted_consumer["uuid"])

    def _inject_ipm(self):
        #stub_ipm = stubs.StubInstalledProductsManager()
        mock_ipm = NonCallableMock(spec=cache.InstalledProductsManager)
        inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, mock_ipm)
        return mock_ipm

    def test_installed_products_cache_written(self):
        connection.UEPConnection = StubUEP

        self._inject_mock_invalid_consumer()
        cmd = RegisterCommand()
        cmd._persist_identity_cert = self.stub_persist
        mock_ipm_wc = self._inject_ipm()
        # Mock out facts and installed products:
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        # FIXME: test something here...
        #self.assertTrue(mock_ipm_wc.call_count > 0)

    @patch('subscription_manager.managercli.EntCertLib')
    def test_activation_keys_updates_certs_and_repos(self,
                                                     mock_entcertlib):
        connection.UEPConnection = StubUEP

        self._inject_mock_invalid_consumer()
        cmd = RegisterCommand()
        cmd._persist_identity_cert = self.stub_persist

        # Mock out facts and installed products:
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()

        mock_entcertlib_instance = mock_entcertlib.return_value

        mock_ipm_wc = self._inject_ipm()
        cmd.main(['register', '--activationkey=test_key', '--org=test_org'])

#        self.assertTrue(mock_ipm_wc.call_count > 0)

        self.assertTrue(mock_entcertlib_instance.update.called)

    @patch('subscription_manager.managercli.EntCertLib')
    def test_consumerid_updates_certs_and_repos(self, mock_entcertlib):

        def getConsumer(self, *args, **kwargs):
            pass

        StubUEP.getConsumer = getConsumer
        connection.UEPConnection = StubUEP

        self._inject_mock_invalid_consumer()
        cmd = RegisterCommand()
        cmd._persist_identity_cert = self.stub_persist

        # Mock out facts and installed products:
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()
        cmd.facts.update_check = Mock()

        mock_entcertlib_instance = mock_entcertlib.return_value

        connection.UEPConnection.getConsumer = Mock(return_value={'uuid': '123123'})

        mock_ipm = self._inject_ipm()
        cmd.main(['register', '--consumerid=123456', '--username=testuser1', '--password=password', '--org=test_org'])

        #self.assertTrue(mock_ipm.write_cache.call_count > 0)


        self.assertTrue(mock_certlib_instance.update.called)
        self.assertTrue(mock_entcertlib_instance.update.called)

    def test_strip_username_and_password(self):

        username, password = RegisterCommand._get_username_and_password(" ", " ")
        self.assertTrue(username == "")
        self.assertTrue(password == "")

        username, password = RegisterCommand._get_username_and_password(" Jar Jar ", " Binks ")
        self.assertTrue(username == "Jar Jar")
        self.assertTrue(password == "Binks")

