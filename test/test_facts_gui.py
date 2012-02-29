import sys
import unittest

from stubs import MockStderr, MockStdout, StubUEP, StubFacts
from subscription_manager.gui import factsgui, managergui
from mock import Mock


class FactDialogTests(unittest.TestCase):

    def setUp(self):

        expected_facts = {'fact1': 'one',
                          'fact2': 'two',
                          'system': 'Unknown',
                          'system.uuid': 'MOCKUUID'}

        self.expected_facts = expected_facts
        self.stub_facts = StubFacts(expected_facts)

        self.uep = StubUEP()

        self.consumer = Mock()
        self.consumer.uuid = "MOCKUUID"
        self.consumer.name = "MOCK CONSUMER"

        sys.stderr = MockStderr
        sys.stdout = MockStdout

    def tearDown(self):
        sys.stderr = sys.__stderr__
        sys.stdout = sys.__stdout__

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
        managergui.consumer = {'uuid': 'Random UUID',
                               'consumer_name': 'system'}

        dialog = factsgui.SystemFactsDialog(self.uep, self.consumer,
                self.stub_facts)
        dialog.show()

        enabled = dialog.update_button.get_property('sensitive')

        self.assertTrue(enabled)
