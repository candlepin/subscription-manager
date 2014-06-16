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

from datetime import datetime
import types
import unittest

import certdata
from rhsm.certificate import create_from_pem, CertificateException
from rhsm.certificate2 import *

from mock import patch


class V1ProductCertTests(unittest.TestCase):
    def setUp(self):
        self.prod_cert = create_from_pem(certdata.PRODUCT_CERT_V1_0)

    def test_factory_method_on_product_cert(self):
        self.assertEquals("1.0", str(self.prod_cert.version))
        self.assertTrue(isinstance(self.prod_cert, ProductCertificate))
        self.assertEquals(1, len(self.prod_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.prod_cert.products[0].name)
        self.assertEquals('100000000000002', self.prod_cert.subject['CN'])

    def test_os_old_cert(self):
        self.assertTrue(self.prod_cert.products[0].brand_type is None)

    def test_set_brand_type(self):
        brand_type = "OS"

        self.prod_cert.products[0].brand_type = brand_type
        self.assertEquals(brand_type, self.prod_cert.products[0].brand_type)

    def test_set_brand_name(self):
        brand_name = "Awesome OS Super"

        self.prod_cert.products[0].brand_name = brand_name
        self.assertEquals(brand_name, self.prod_cert.products[0].brand_name)


class V1EntCertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V1_0)

    def test_no_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem, "")

    def test_junk_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem,
                "DOESTHISLOOKLIKEACERTTOYOU?")

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("1.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)
        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)
        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)
        self.assertEquals('ff80808138574bd20138574d85a50b2f', self.ent_cert.subject['CN'])

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

    def test_access_path_tree_fails(self):
        # not supported for v3 certs
        self.assertRaises(AttributeError, getattr, self.ent_cert, '_path_tree')

    def test_check_path(self):
        # matches /foo/path/never
        self.assertTrue(self.ent_cert.check_path('/foo/path/never'))
        self.assertTrue(self.ent_cert.check_path('/foo/path/never/'))
        self.assertTrue(self.ent_cert.check_path('/foo/path/never/bar/a/b/c'))
        self.assertTrue(self.ent_cert.check_path('/foo/path/never/bar//a/b/c'))

    def test_check_path_with_var(self):
        # matches /path/to/$basearch/$releasever/awesomeos
        self.assertTrue(self.ent_cert.check_path('/path/to/foo/bar/awesomeos'))
        self.assertTrue(self.ent_cert.check_path('/path/to/foo/bar/awesomeos/'))
        self.assertTrue(self.ent_cert.check_path('/path/to/foo/bar/awesomeos/a/b/c'))

    def test_check_path_fail(self):
        self.assertFalse(self.ent_cert.check_path('foo'))
        self.assertFalse(self.ent_cert.check_path('/foo'))
        self.assertFalse(self.ent_cert.check_path('/foo/'))
        self.assertFalse(self.ent_cert.check_path('/foo/path/'))

    @patch('rhsm.certificate2.EntitlementCertificate._validate_v1_url')
    def test_download_url_identification(self, mock_validate):
        # there are 4 OIDs in the testing cert that should be checked, and
        # many others that should not. This verifies that exactly 4 OIDs get
        # checked.
        mock_validate.return_value = False
        self.ent_cert.check_path('/foo')
        self.assertEqual(mock_validate.call_count, 4)

    # TODO: test exception when cert major version is newer than we can handle


class V3CertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V3_0)

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("3.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)

        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)

        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)
        self.assertEquals('ff80808139d9e26c0139da23489a0066',
                self.ent_cert.subject['CN'])

    def test_factory_method_without_ent_data(self):
        data = certdata.ENTITLEMENT_CERT_V3_0.split('-----BEGIN ENTITLEMENT DATA-----')[0]
        cert = create_from_pem(data)
        self.assertTrue(cert.content is None)
        self.assertTrue(cert.order is None)
        self.assertEqual(cert.products, [])

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

    def test_content_no_arches(self):
        """Handle entitlement certs with no arch info on content"""
        content = self._find_content_by_label(self.ent_cert.content,
                                              "always-enabled-content")
        # we should get the default empty list if there are no arches
        # specified, ala the test entitlement cert
        self.assertEquals([], content.arches)

    @patch('os.unlink')
    def test_delete(self, unlink_mock):
        """ Entitlement cert deletion should cleanup key as well. """
        cert_path = "/etc/pki/entitlement/12345.pem"
        key_path = "/etc/pki/entitlement/12345-key.pem"
        self.ent_cert.path = cert_path
        self.unlinked = []
        self.ent_cert.delete()

        self.assertEquals(2, unlink_mock.call_count)
        self.assertEquals(cert_path, unlink_mock.call_args_list[0][0][0])
        self.assertEquals(key_path, unlink_mock.call_args_list[1][0][0])

    def test_cert_with_carriage_returns(self):
        # make sure it can parse a cert where the "-----" etc. lines end with
        # "\r\n" instead of just "\n". Failure to parse in this case was
        # discovered when trying to parse an employee-sku cert that jbowes
        # emailed to mhrivnak. the origin of the offending carriage returns is
        # unknown.
        crcert = certdata.ENTITLEMENT_CERT_V3_0.replace('-\n', '-\r\n')
        create_from_pem(crcert)

    def test_match_path(self):
        self.assertTrue(self.ent_cert.check_path('/path/to/awesomeos/x86_64'))
        self.assertTrue(self.ent_cert.check_path('/path/to/awesomeos//x86_64'))

    def test_match_deep_path(self):
        self.assertTrue(self.ent_cert.check_path('/path/to/awesomeos/x86_64/foo/bar'))

    def test_missing_pool(self):
        self.assertEquals(None, self.ent_cert.pool)


class V3_2CertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V3_2)

    def test_read_pool(self):
        self.assertEquals("3.2", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals('8a8d01f53cda9dd0013cda9ed5100475',
                self.ent_cert.pool.id)


class TestEntCertV1KeyPath(unittest.TestCase):
    cert_data = certdata.ENTITLEMENT_CERT_V1_0

    def setUp(self):
        self.ent_cert = create_from_pem(self.cert_data)

    def test_key_path(self):
        self.ent_cert.path = "/etc/pki/entitlement/12345.pem"
        expected_key_path = "/etc/pki/entitlement/12345-key.pem"

        actual_key_path = self.ent_cert.key_path()
        self.assertEquals(actual_key_path, expected_key_path)

    def test_key_path_extra_pem(self):
        self.ent_cert.path = "/etc/pki/entitlement/12345-with-a.pem-in-the-name.pem"
        expected_key_path = "/etc/pki/entitlement/12345-with-a.pem-in-the-name-key.pem"

        actual_key_path = self.ent_cert.key_path()
        self.assertEquals(actual_key_path, expected_key_path)

    def test_key_path_no_pem(self):
        self.ent_cert.path = "/etc/pki/entitlement/12345"
        self.assertRaises(CertificateException, self.ent_cert.key_path)

    def test_key_path_no_slash(self):
        self.ent_cert.path = "12345.pem"
        expected_key_path = "12345-key.pem"

        actual_key_path = self.ent_cert.key_path()
        self.assertEquals(actual_key_path, expected_key_path)


class TestEntCertV3_0KeyPath(TestEntCertV1KeyPath):
    cert_data = certdata.ENTITLEMENT_CERT_V3_0


class TestEntCertV3_2KeyPath(TestEntCertV1KeyPath):
    cert_data = certdata.ENTITLEMENT_CERT_V3_2


class V3_2ContentArchCertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V3_2_WITH_CONTENT_ARCH)

    def test_read_content_arches(self):
        for content in self.ent_cert.content:
            self.assertTrue(isinstance(content.arches, types.ListType))
            if content.label == 'always-enabled-content':
                self.assertEquals(['ALL'], content.arches)
            if content.label == 'awesomeos-x86_64-i386-content':
                self.assertTrue('i386' in content.arches)
                self.assertTrue('x86_64' in content.arches)
                self.assertFalse('ALL' in content.arches)


class IdentityCertTests(unittest.TestCase):

    def test_creation(self):
        id_cert = create_from_pem(certdata.IDENTITY_CERT)
        self.assertTrue(isinstance(id_cert, IdentityCertificate))
        self.assertEquals("URI:CN=redhat.local.rm-rf.ca", id_cert.alt_name)
        self.assertEquals("0f5d4617-d913-4a0f-be61-d8a9c88e1476", id_cert.subject['CN'])
        self.assertFalse(hasattr(id_cert, 'products'))

    def test_default_version(self):
        id_cert = create_from_pem(certdata.IDENTITY_CERT)
        self.assertTrue(isinstance(id_cert, IdentityCertificate))
        self.assertEquals('1.0', str(id_cert.version))


class ContentTests(unittest.TestCase):

    def test_enabled(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=None)
        self.assertTrue(c.enabled)
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled="1")
        self.assertTrue(c.enabled)
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=True)
        self.assertTrue(c.enabled)
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled="0")
        self.assertFalse(c.enabled)
        self.assertRaises(CertificateException, Content, content_type="yum",
                name="mycontent", label="mycontent", enabled="5")

    def test_content_requires_type(self):
        self.assertRaises(CertificateException, Content, name="testcontent",
                          label="testcontent", enabled=True)
        self.assertRaises(CertificateException, Content, content_type=None,
                          name="testcontent", label="testcontent", enabled=True)
        self.assertRaises(CertificateException, Content, content_type="",
                          name="testcontent", label="testcontent", enabled=True)

    def test_arches_not_set(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1)
        self.assertTrue(isinstance(c.arches, types.ListType))
        self.assertEquals([], c.arches)

    def test_arches_empty(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1, arches=[])
        self.assertTrue(isinstance(c.arches, types.ListType))
        self.assertEquals([], c.arches)

    def test_arches(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1, arches=['i386', 's390'])
        self.assertTrue(isinstance(c.arches, types.ListType))
        self.assertTrue('i386' in c.arches)
        self.assertTrue('s390' in c.arches)

    def test_arches_all(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1, arches=['ALL'])
        self.assertTrue(isinstance(c.arches, types.ListType))
        self.assertTrue('ALL' in c.arches)

    def test_compare(self):
        c = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1, arches=['ALL'])
        d = c
        e = Content(content_type="yum", name="mycontent", label="mycontent", enabled=1, arches=['ALL'])
        f = Content(content_type="yum", name="othercontent", label="othercontent", enabled=1)

        self.assertEqual(c, c)
        self.assertNotEqual(c, None)
        self.assertNotEquals(c, "not a content")
        self.assertEqual(c, d)
        self.assertEqual(c, e)
        self.assertNotEqual(c, f)


class ProductTests(unittest.TestCase):

    def test_arch_multi_valued(self):
        p = Product(id="pid", name="pname", architectures="i386,x86_64")
        self.assertEquals(2, len(p.architectures))
        self.assertEquals("i386", p.architectures[0])
        self.assertEquals("x86_64", p.architectures[1])

    def test_none_arch(self):
        p = Product(id="pid", name="pname")
        self.assertTrue(p.architectures is not None)
        self.assertTrue(isinstance(p.architectures, list))

    def test_no_brand_type(self):
        p = Product(id="pid", name="pname")
        self.assertTrue(p.brand_type is None)

    def test_brand_type(self):
        p = Product(id="pid", name="pname",
                    brand_type="pbrand_type")
        self.assertTrue(p.brand_type == "pbrand_type")

    def test_brand_type_none(self):
        p = Product(id="pid", name="pname",
                    brand_type=None)
        self.assertTrue(p.brand_type is None)

    def test_brand_type_empty_string(self):
        p = Product(id='pid', name='pname',
                    brand_type="")
        self.assertEquals(p.brand_type, "")

    def test_no_brand_name(self):
        p = Product(id="pid", name="pname")
        self.assertTrue(p.brand_name is None)

    def test_brand_name(self):
        p = Product(id="pid", name="pname",
                    brand_name="pbrand_name")
        self.assertTrue(p.brand_name == "pbrand_name")

    def test_brand_name_none(self):
        p = Product(id="pid", name="pname",
                    brand_name=None)
        self.assertTrue(p.brand_name is None)

    def test_brand_name_empty_string(self):
        p = Product(id="pid", name="pname",
                    brand_name="")
        self.assertEquals(p.brand_name, "")
