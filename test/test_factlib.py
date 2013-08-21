#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import stubs
import fixture

from subscription_manager import factlib
from subscription_manager import injection as inj


class TestFactlib(fixture.SubManFixture):

    def setUp(self):
        super(TestFactlib, self).setUp()
        self.stub_uep = stubs.StubUEP()
        self.expected_facts = {'fact1': 'F1', 'fact2': 'F2'}

        inj.provide(inj.FACTS, stubs.StubFacts(self.expected_facts))
        self.fl = factlib.FactLib(uep=self.stub_uep)

    def test_factlib_updates_when_identity_does_not_exist(self):
        factlib.ConsumerIdentity = stubs.StubConsumerIdentity
        update_report = self.fl.update()
        count = update_report.updates()
        self.assertEquals(len(self.expected_facts), count)

    def test_factlib_updates_when_identity_exists(self):
        factlib.ConsumerIdentity = ConsumerIdentityExistsStub

        self.facts_passed_to_server = None
        self.consumer_uuid_passed_to_server = None

        def track_facts_update(consumer_uuid, facts):
            self.facts_passed_to_server = facts
            self.consumer_uuid_passed_to_server = consumer_uuid

        self.stub_uep.updateConsumerFacts = track_facts_update

        update_report = self.fl.update()
        count = update_report.updates()
        self.assertEquals(len(self.expected_facts), count)
        self.assertEquals(self.expected_facts, self.facts_passed_to_server)
        self.assertEquals(stubs.StubConsumerIdentity.CONSUMER_ID, self.consumer_uuid_passed_to_server)


class ConsumerIdentityExistsStub(stubs.StubConsumerIdentity):
    def __init__(self, keystring, certstring):
        super(ConsumerIdentityExistsStub, self).__init__(keystring, certstring)

    @classmethod
    def exists(cls):
        return True
