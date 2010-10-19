import unittest

import facts
from gui import factsgui, managergui
from mock import Mock

class FactDialogTests(unittest.TestCase):

    def setUp(self):

        expected_facts = { 'fact1': 'one',
                           'fact2': 'two' }
        class StubFacts:
            def get_facts(self):
                return expected_facts

        self.expected_facts = expected_facts

        facts.getFacts = lambda: StubFacts()

        self.consumer = Mock()
        self.consumer.uuid = "MOCKUUID"
        self.consumer.name = "MOCK CONSUMER"

    def test_facts_are_displayed(self):
        found_facts = {}

        def check_facts(fact):
            found_facts[fact[0]] = fact[1]

        dialog = factsgui.SystemFactsDialog(self.consumer)
        dialog.facts_store.append = check_facts
        dialog.display_facts()

        self.assertEquals(self.expected_facts, found_facts)

    def test_update_button_disabled(self):
        # Need an unregistered consumer object:
        unregistered_consumer = Mock()
        unregistered_consumer.uuid = None
        unregistered_consumer.name = None

        dialog = factsgui.SystemFactsDialog(unregistered_consumer)
        dialog.show()

        enabled = dialog.update_button.get_sensitive()

        self.assertFalse(enabled)

    def test_update_button_enabled(self):
        managergui.consumer = { 'uuid': 'Random UUID',
                                'consumer_name': 'system' }

        dialog = factsgui.SystemFactsDialog(self.consumer)
        dialog.show()

        enabled = dialog.update_button.get_sensitive()

        self.assertTrue(enabled)
