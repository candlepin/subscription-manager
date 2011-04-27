import unittest

from subscription_manager.gui import subscription_assistant

class TestSubscriptionAssistant(unittest.TestCase):
    def test_subscription_assistant(self):
        sa = subscription_assistant.SubscriptionAssistant(None, None, None)
        
