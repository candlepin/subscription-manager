import unittest

from rhsm.certificate import OID


class OIDTests(unittest.TestCase):

    def setUp(self):
        self.oid = OID("1.2.3.4.5.6.7")

    def test_length(self):
        self.assertEquals(7, len(self.oid))

    def test_match_positive(self):
        self.assertTrue(self.oid.match(OID("1.2.3.4.5.6.7")))
        self.assertTrue(self.oid.match(OID("1.")))
        self.assertTrue(self.oid.match(OID("1.2.3.")))
        self.assertTrue(self.oid.match(OID("1.*.3.4.5.6.7")))
        self.assertTrue(self.oid.match(OID("1.*.3.4.*.6.*")))
        self.assertTrue(self.oid.match(OID(".*")))
        self.assertTrue(self.oid.match(OID(".5.6.7")))
        self.assertTrue(self.oid.match(OID(".7")))

    def test_match_negative(self):
        self.assertFalse(self.oid.match(OID("1.2.3.4.5.9.7")))
        self.assertFalse(self.oid.match(OID("1.2.4.")))
        self.assertFalse(self.oid.match(OID("1.*.4.")))
        # * matches only one item
        self.assertFalse(self.oid.match(OID("1.*")))

        # Not an OID
        self.assertFalse(self.oid.match("1.2.3.4.5.6.7"))
