import unittest
import stubs

from subscription_manager.gui import subscription_assistant


class TestSubscriptionAssistant(unittest.TestCase):
    def test_subscription_assistant(self):
        subscription_assistant.SubscriptionAssistant(None, None, None)
