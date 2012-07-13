#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import unittest
from datetime import datetime

import certdata
from rhsm.certificate import create_from_pem, CertificateException
from rhsm.certificate2 import *


class V1CertTests(unittest.TestCase):

    def setUp(self):
        self.prod_cert = create_from_pem(certdata.PRODUCT_CERT_V1_0)
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V1_0)

    def test_no_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem, "")

    def test_junk_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem,
                "DOESTHISLOOKLIKEACERTTOYOU?")

    def test_factory_method_on_product_cert(self):
        self.assertEquals("1.0", str(self.prod_cert.version))
        self.assertTrue(isinstance(self.prod_cert, ProductCertificate))
        self.assertEquals(1, len(self.prod_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.prod_cert.products[0].name)

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("1.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)
        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)
        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)

    def test_is_valid(self):
        self.assertTrue(self.ent_cert.is_valid(on_date=datetime(2012, 12, 1)))
        self.assertFalse(self.ent_cert.is_valid(on_date=datetime(2014, 12, 1)))

    def test_order(self):
        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)

    def _find_content_by_label(self, content, label):
        """ Just pulls out content from a list if label matches. """
        for c in content:
            if c.label == label:
                return c

    def test_content(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "always-enabled-content")
        self.assertEquals("always-enabled-content", content.name)
        self.assertEquals(True, content.enabled)
        self.assertEquals("/foo/path/always/$releasever", content.url)
        self.assertEquals("/foo/path/always/gpg", content.gpg)

    # TODO: test exception when cert major version is newer than we can handle


class V2CertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V2_0)

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("2.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)

        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)

        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)

    def test_is_valid(self):
        self.assertTrue(self.ent_cert.is_valid(on_date=datetime(2012, 12, 1)))
        self.assertFalse(self.ent_cert.is_valid(on_date=datetime(2014, 12, 1)))

    def _find_content_by_label(self, content, label):
        """ Just pulls out content from a list if label matches. """
        for c in content:
            if c.label == label:
                return c

    def test_order(self):
        self.assertEquals(2, self.ent_cert.order.quantity_used)
        self.assertEquals("1", self.ent_cert.order.stacking_id)
        self.assertEquals("awesomeos-x86_64", self.ent_cert.order.sku)

    def test_content_enabled(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "always-enabled-content")
        self.assertEquals("always-enabled-content", content.name)
        self.assertEquals(True, content.enabled)
        self.assertEquals(200, content.metadata_expire)
        self.assertEquals("/foo/path/always/$releasever", content.url)
        self.assertEquals("/foo/path/always/gpg", content.gpg)

    def test_content_disabled(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "never-enabled-content")
        self.assertEquals("never-enabled-content", content.name)
        self.assertEquals(False, content.enabled)


class IdentityCertTests(unittest.TestCase):

    def test_creation(self):
        id_cert = create_from_pem(certdata.IDENTITY_CERT)
        self.assertTrue(isinstance(id_cert, IdentityCertificate))
        self.assertEquals("DirName:/CN=redhat.local.rm-rf.ca", id_cert.alt_name)
        self.assertEquals("eaadd6ea-852d-4430-94a7-73d5887d48e8", id_cert.subject['CN'])
        self.assertFalse(hasattr(id_cert, 'products'))


class ContentTests(unittest.TestCase):

    def test_enabled(self):
        c = Content(name="mycontent", label="mycontent", enabled=None)
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled="1")
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled=True)
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled="0")
        self.assertFalse(c.enabled)
        self.assertRaises(CertificateException, Content, name="mycontent",
                label="mycontent", enabled="5")

