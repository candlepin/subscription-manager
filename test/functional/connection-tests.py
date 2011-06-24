import unittest
from rhsm.connection import *

class ConnectionTests(unittest.TestCase):

    def setUp(self):
        self.cp = UEPConnection(username="admin", password="admin")

    def test_supports_resource(self):
        self.assertTrue(self.cp.supports_resource('consumers'))
        self.assertTrue(self.cp.supports_resource('admin'))
        self.assertFalse(self.cp.supports_resource('boogity'))

