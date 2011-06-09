import unittest
import tempfile

import stubs

from subscription_manager import factlib
from subscription_manager import certlib

class MockActionLock(certlib.ActionLock):
    PATH = tempfile.mkstemp()[1]

    def __init__(self):
        certlib.ActionLock.__init__(self)

#FIXME: need a mocked/stubbed facts.Facts here

class TestFactlib(unittest.TestCase):

    def setUp(self):
        factlib.ConsumerIdentity = stubs.StubConsumerIdentity
        self.fl = factlib.FactLib(lock=MockActionLock())

    def test_factlib_updates(self):
        update = self.fl.update()
