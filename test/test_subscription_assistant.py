import unittest
from subscription_manager.gui.subscription_assistant import SubscriptionAssistant

class TestSubscriptionAssistant(unittest.TestCase):
    def test_subscription_assistant(self):
        SubscriptionAssistant(None, None, None)
