import unittest

import facts
from gui import factsgui, managergui

class FactDialogTests(unittest.TestCase):

    def test_facts_are_displayed(self):
        expected_facts = { 'fact1': 'one',
                           'fact2': 'two' }
        found_facts = {}

        class StubFacts:
            def get_facts(self):
                return expected_facts

        def check_facts(fact):
            found_facts[fact[0]] = fact[1]

        facts.getFacts = lambda: StubFacts()

        dialog = factsgui.SystemFactsDialog()
        dialog.facts_store.append = check_facts
        dialog.display_facts()

        self.assertEquals(expected_facts, found_facts)

    def test_update_button_disabled(self):
        managergui.consumer = None

        dialog = factsgui.SystemFactsDialog()
        dialog.show()

        enabled = dialog.update_button.get_sensitive()

        self.assertFalse(enabled)

    def test_update_button_enabled(self):
        managergui.consumer = { 'uuid': 'Random UUID',
                                'consumer_name': 'system' }

        dialog = factsgui.SystemFactsDialog()
        dialog.show()

        enabled = dialog.update_button.get_sensitive()

        self.assertTrue(enabled)
