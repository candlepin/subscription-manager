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

from stubs import StubUEP
import rhsm.connection as connection
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.managercli import RegisterCommand
from subscription_manager import managerlib


class CliRegistrationTests(unittest.TestCase):

    def test_register_persists_consumer_cert(self):

        self.persisted_consumer = Mock()

        def stub_persist(consumer):
            self.persisted_consumer = consumer
            return self.persisted_consumer

        # Given
        connection.UEPConnection = StubUEP
        managerlib.persist_consumer_cert = stub_persist
        ConsumerIdentity.exists = classmethod(lambda cls: False)

        # When
        cmd = RegisterCommand()

        # Mock out facts:
        cmd.facts.get_facts = Mock()
        cmd.facts.get_facts.return_value = {'fact1': 'val1', 'fact2': 'val2'}
        cmd.facts.write_cache = Mock()

        cmd.main(['register', '--username=testuser1', '--password=password'])

        # Then
        self.assertEqual('dummy-consumer-uuid', self.persisted_consumer["uuid"])
        
