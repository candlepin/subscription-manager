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
import connection
from certlib import ConsumerIdentity
from managercli import RegisterCommand
import managerlib

import os
import unittest

class CliRegistrationTests(unittest.TestCase):

    def test_register_persists_consumer_cert(self):
        class StubUEP:
            def __init__(self, username=None, password=None, cert_file=None, key_file=None):
                pass
  
            def registerConsumer(self, name, type, facts):
                return 'Dummy Consumer'

        self.persisted_consumer = None

        def stub_persist(consumer):
            self.persisted_consumer = consumer

        # Given
        connection.UEPConnection = StubUEP
        managerlib.persist_consumer_cert = stub_persist
        ConsumerIdentity.exists = classmethod(lambda cls: False)

        # When
        cmd = RegisterCommand()
        cmd.main(['register', '--username=testuser1', '--password=password'])

        # Then
        self.assertEqual('Dummy Consumer', self.persisted_consumer)

