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

from mock import patch

from stubs import StubProduct, StubEntitlementCertificate
from subscription_manager.certdirectory import Path, EntitlementDirectory
from subscription_manager.repolib import RepoFile
from subscription_manager.productid import ProductDatabase


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

        Path.ROOT = '/mnt/sysimage'
        rf = RepoFile()
        self.assertEquals("/mnt/sysimage/etc/yum.repos.d/redhat.repo", rf.path)

    def test_product_database(self):
        Path.ROOT = '/mnt/sysimage'
        prod_db = ProductDatabase()
        self.assertEquals('/mnt/sysimage/var/lib/rhsm/productid.js',
                prod_db.dir.abspath('productid.js'))

    def test_sysimage_pathjoin(self):
        Path.ROOT = '/mnt/sysimage'
        ed = EntitlementDirectory()
        self.assertEquals('/mnt/sysimage/etc/pki/entitlement/1-key.pem',
                Path.join(ed.productpath(), '1-key.pem'))

    def test_normal_pathjoin(self):
        ed = EntitlementDirectory()
        self.assertEquals('/etc/pki/entitlement/1-key.pem',
                Path.join(ed.productpath(), "1-key.pem"))


# make sure _check_key returns the right value
class TestEntitlementDirectoryCheckKey(unittest.TestCase):
    @patch('os.path.exists')
    @patch('os.access')
    def test_check_key(self, MockAccess, MockExists):
        ent_dir = EntitlementDirectory()
        MockAccess.return_value = True
        MockExists.return_value = True
        product = StubProduct("product1")
        ent_cert = StubEntitlementCertificate(product)
        ret = ent_dir._check_key(ent_cert)
        self.assertTrue(ret)

    @patch('os.path.exists')
    @patch('os.access')
    def test_check_key_false(self, MockAccess, MockExists):
        ent_dir = EntitlementDirectory()
        MockAccess.return_value = False
        MockExists.return_value = True
        product = StubProduct("product1")
        ent_cert = StubEntitlementCertificate(product)
        ret = ent_dir._check_key(ent_cert)
        self.assertFalse(ret)
