import unittest
import tempfile

import stubs

from subscription_manager import factlib
from subscription_manager import certlib


class MockActionLock(certlib.ActionLock):
    PATH = tempfile.mkstemp()[1]

    def __init__(self):
        certlib.ActionLock.__init__(self)


class TestFactlib(unittest.TestCase):

    def setUp(self):
        self.stub_uep = stubs.StubUEP()
        self.fl = factlib.FactLib(lock=MockActionLock(), uep=self.stub_uep)

        self.expected_facts = {'fact1': 'F1', 'fact2': 'F2'}

        def init_facts():
            return stubs.StubFacts(self.expected_facts)
        self.fl.action._get_facts = init_facts

    def test_factlib_updates_when_identity_does_not_exist(self):
        factlib.ConsumerIdentity = stubs.StubConsumerIdentity
        count = self.fl.update()
        self.assertEquals(len(self.expected_facts), count)

    def test_factlib_updates_when_identity_exists(self):
        factlib.ConsumerIdentity = ConsumerIdentityExistsStub

        self.facts_passed_to_server = None
        self.consumer_uuid_passed_to_server = None
        def track_facts_update(consumer_uuid, facts):
            self.facts_passed_to_server = facts
            self.consumer_uuid_passed_to_server = consumer_uuid

        self.stub_uep.updateConsumerFacts = track_facts_update

        count = self.fl.update()
        self.assertEquals(len(self.expected_facts), count)
        self.assertEquals(self.expected_facts, self.facts_passed_to_server)
        self.assertEquals(stubs.StubConsumerIdentity.CONSUMER_ID, self.consumer_uuid_passed_to_server)

class ConsumerIdentityExistsStub(stubs.StubConsumerIdentity):
    def __init__(self, keystring, certstring):
        super(ConsumerIdentityExistsStub, self).__init__(keystring, certstring)

    @classmethod
    def exists(cls):
        return True