#
# Copyright (c) 2010 Red Hat, Inc.
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
import os
from certlib import *
from repolib import RepoFile
from productid import ProductDatabase
from modelhelpers import *
from stubs import *
from certificate import GMT


def dummy_exists(filename):
    return True

class PathTests(unittest.TestCase):
    """
    Tests for the certlib Path class, changes to it's ROOT setting can affect
    a variety of things that only surface in anaconda.
    """

    def setUp(self):
        # monkey patch os.path.exists, be careful, this can break things 
        # including python-nose if we don't set it back in tearDown.
        self.actual_exists = os.path.exists
        os.path.exists = dummy_exists

    def tearDown(self):
        Path.ROOT = "/"
        os.path.exists = self.actual_exists

    def test_normal_root(self):
        # this is the default, but have to set it as other tests can modify
        # it if they run first.
        self.assertEquals('/etc/pki/consumer/', Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/etc/pki/consumer/', Path.abs('etc/pki/consumer/'))

    def test_modified_root(self):
        Path.ROOT = '/mnt/sysimage/'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_modified_root_no_trailing_slash(self):
        Path.ROOT = '/mnt/sysimage'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_repo_file(self):
        # Fake that the redhat.repo exists:
        old = os.path.exists

        Path.ROOT = '/mnt/sysimage'
        rf = RepoFile()
        self.assertEquals("/mnt/sysimage/etc/yum.repos.d/redhat.repo", rf.path)

    def test_product_database(self):
        Path.ROOT = '/mnt/sysimage'
        prod_db = ProductDatabase()
        self.assertEquals('/mnt/sysimage/var/lib/rhsm/productid.js',
                prod_db.dir.abspath('productid.js'))

    def test_sysimage_keypath(self):
        ed = EntitlementDirectory()
        Path.ROOT = '/mnt/sysimage'
        self.assertEquals('/mnt/sysimage/etc/pki/entitlement/key.pem', ed.keypath())

    def test_keypath(self):
        ed = EntitlementDirectory()
        self.assertEquals('/etc/pki/entitlement/key.pem', ed.keypath())


class FindLastCompliantTests(unittest.TestCase):

    def test_just_entitlements(self):
        cert1 = StubEntitlementCertificate(
                    StubProduct('product1'), start_date=datetime(2010, 1, 1),
                    end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime(2010, 1, 1),
                    end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])
        prod_dir = StubCertificateDirectory([])
        last_compliant_date = find_last_compliant(ent_dir=ent_dir,
                product_dir=prod_dir)
        self.assertEqual(2050, last_compliant_date.year)

    def test_unentitled_products(self):
        cert = StubProductCertificate(StubProduct('unentitledProduct'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of compliance:
        today = datetime.now(GMT())
        last_compliant_date = find_last_compliant(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(today.year, last_compliant_date.year)
        self.assertEqual(today.month, last_compliant_date.month)
        self.assertEqual(today.day, last_compliant_date.day)

    def test_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProductCertificate(StubProduct('product2')),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of compliance:
        today = datetime.now(GMT())
        last_compliant_date = find_last_compliant(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(2050, last_compliant_date.year)

    def test_all_expired_entitlements(self):
        pass


class CertSorterTests(unittest.TestCase):

    def setUp(self):
        # Setup mock product and entitlement certs:
        self.prod_dir = StubCertificateDirectory([
            # Will be unentitled:
            StubProductCertificate(StubProduct('product1')),
            # Will be entitled:
            StubProductCertificate(StubProduct('product2')),
            # Will be entitled but expired:
            StubProductCertificate(StubProduct('product3')),
        ])

        #self.ent_dir = StubCertificateDirectory([
        #    StubEntitlementCertificate(
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('product2')),
            StubEntitlementCertificate(StubProduct('product3'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct('product4'))
        ])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)

    def test_unentitled_products(self):
        self.assertEqual(1, len(self.sorter.unentitled))
        self.assertTrue(cert_list_has_product(self.sorter.unentitled, 'product1'))

    def test_entitled_products(self):
        self.assertEqual(2, len(self.sorter.valid))
        self.assertTrue(cert_list_has_product(self.sorter.valid, 'product2'))
        self.assertTrue(cert_list_has_product(self.sorter.valid, 'product4'))

    def test_expired(self):
        self.assertEqual(1, len(self.sorter.expired))
        self.assertTrue(cert_list_has_product(self.sorter.expired, 'product3'))

    def test_expired_in_future(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                on_date=datetime(2050, 1, 1))
        self.assertEqual(3, len(self.sorter.expired))
        self.assertTrue(cert_list_has_product(self.sorter.expired, 'product2'))
        self.assertTrue(cert_list_has_product(self.sorter.expired, 'product3'))
        self.assertTrue(cert_list_has_product(self.sorter.expired, 'product4'))

def cert_list_has_product(cert_list, product_id):
    found = False
    for cert in cert_list:
        if cert.getProduct().getHash() == product_id:
            found = True
            break
    return found


