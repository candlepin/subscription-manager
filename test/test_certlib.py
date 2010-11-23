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
        cert1 = mock_ent_cert('product1', start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = mock_ent_cert('product2', start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = mock_ent_dir([cert1, cert2])
        ent_dir.listValid.return_value = [cert1, cert2]
        last_compliant_date = find_last_compliant(ent_dir=ent_dir)
        self.assertEqual(2050, last_compliant_date.year)

    def test_unentitled_products(self):
        product_dir = mock_product_dir([mock_product_cert('unentitledProduct')])
        cert1 = mock_ent_cert('product1', start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = mock_ent_cert('product2', start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = mock_ent_dir_no_product([cert1, cert2])
        ent_dir.listValid.return_value = [cert1, cert2]

        # Because we have an unentitled product, we should get back the current
        # date as the last date of compliance:
        today = datetime.now(GMT())
        last_compliant_date = find_last_compliant(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(today.year, last_compliant_date.year)
        self.assertEqual(today.month, last_compliant_date.month)
        self.assertEqual(today.day, last_compliant_date.day)

    def test_entitled_products(self):
        product_dir = mock_product_dir([mock_product_cert('product1')])
        cert1 = mock_ent_cert('product1', start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = mock_ent_cert('product2', start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = mock_ent_dir([cert1, cert2])
        ent_dir.listValid.return_value = [cert1, cert2]

        # Because we have an unentitled product, we should get back the current
        # date as the last date of compliance:
        today = datetime.now(GMT())
        last_compliant_date = find_last_compliant(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(2050, last_compliant_date.year)

    def test_all_expired_entitlements(self):
        pass



class CertSorterTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_unentitled_products(self):
        pass

    def test_entitled_products(self):
        pass

    def test_entitled_but_not_installed(self):
        pass

    def test_expired(self):
        pass
