import unittest

from mock import Mock
from stubs import StubUEP, StubEntitlementCertificate, StubCertificateDirectory, StubProduct, StubBackend, StubFacts, StubProductDirectory
#from subscription_manager.gui.subscription_assistant import SubscriptionAssistant
from subscription_manager.gui import subscription_assistant
from subscription_manager import certlib

class TestSubscriptionAssistant(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.consumer = Mock()
        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': '',
                          'system.uuid': 'MOCKUUID'}
        self.facts = StubFacts(fact_dict = expected_facts)

        self.ent_dir = StubCertificateDirectory([])

        self.prod_dir = StubProductDirectory([])


    def test_subscription_assistant(self):
        subscription_assistant.SubscriptionAssistant(self.backend, self.consumer, 
                                                     self.facts, self.ent_dir,
                                                     self.prod_dir)
