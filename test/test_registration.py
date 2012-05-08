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
import unittest
from mock import Mock

from stubs import StubUEP, StubEntitlementDirectory, StubProductDirectory
import rhsm.connection as connection
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.managercli import RegisterCommand


class CliRegistrationTests(unittest.TestCase):

    def stub_persist(self, consumer):
        self.persisted_consumer = consumer
        return self.persisted_consumer

    def test_register_persists_consumer_cert(self):
        connection.UEPConnection = StubUEP

        # When
        cmd = RegisterCommand(ent_dir=StubEntitlementDirectory([]),
                              prod_dir=StubProductDirectory([]))

        ConsumerIdentity.exists = classmethod(lambda cls: False)
        cmd._persist_identity_cert = self.stub_persist
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()
        cmd.installed_mgr.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        # Then
        self.assertEqual('dummy-consumer-uuid', self.persisted_consumer["uuid"])

    def test_installed_products_cache_written(self):
        connection.UEPConnection = StubUEP

        cmd = RegisterCommand(ent_dir=StubEntitlementDirectory([]),
                              prod_dir=StubProductDirectory([]))
        cmd._persist_identity_cert = self.stub_persist
        ConsumerIdentity.exists = classmethod(lambda cls: False)

        # Mock out facts and installed products:
        cmd.facts.get_facts = Mock(return_value={'fact1': 'val1', 'fact2': 'val2'})
        cmd.facts.write_cache = Mock()
        cmd.installed_mgr.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        self.assertEquals(1, cmd.installed_mgr.write_cache.call_count)
