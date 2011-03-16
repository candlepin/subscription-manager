import unittest

import facts
from gui import factsgui, managergui
from mock import Mock


class StubUEP:
    def __init__(self, username=None, password=None,
                 proxy_hostname=None, proxy_port=None,
                 proxy_user=None, proxy_password=None,
                 cert_file=None, key_file=None):
        pass



class FactDialogTests(unittest.TestCase):

    def setUp(self):

        expected_facts = { 'fact1': 'one',
                           'fact2': 'two',
                           'system': '',
                           'system.uuid': 'MOCKUUID'}
        class StubFacts:
            def get_facts(self):
                return expected_facts

            def get_last_update(self):
                return None

            def find_facts(self):
                return expected_facts

        self.expected_facts = expected_facts
        self.stub_facts = StubFacts()
        
        self.uep = StubUEP()

        self.consumer = Mock()
        self.consumer.uuid = "MOCKUUID"
        self.consumer.name = "MOCK CONSUMER"

    def test_facts_are_displayed(self):
        found_facts = {}

        def check_facts(parent, facts):
            found_facts[facts[0]] = facts[1]

        dialog = factsgui.SystemFactsDialog(self.uep, self.consumer,
                self.stub_facts)
        dialog.facts_store.append = check_facts
        dialog.display_facts()

        self.assertEquals(self.expected_facts, found_facts)

    def test_update_button_disabled(self):
        # Need an unregistered consumer object:
        unregistered_consumer = Mock()
        unregistered_consumer.uuid = None
        unregistered_consumer.name = None

        dialog = factsgui.SystemFactsDialog(self.uep, unregistered_consumer,
                self.stub_facts)
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertFalse(enabled)

    def test_update_button_enabled(self):
        managergui.consumer = { 'uuid': 'Random UUID',
                                'consumer_name': 'system' }

        dialog = factsgui.SystemFactsDialog(self.uep, self.consumer,
                self.stub_facts)
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertTrue(enabled)
