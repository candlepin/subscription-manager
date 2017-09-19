from __future__ import print_function, division, absolute_import

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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import tempfile
import os

from mock import patch, MagicMock
from shutil import rmtree

from .stubs import StubProduct, StubEntitlementCertificate, \
    StubProductCertificate
from subscription_manager.certdirectory import Path, EntitlementDirectory, \
    ProductDirectory, ProductCertificateDirectory, Directory
from subscription_manager.repolib import YumRepoFile
from subscription_manager.productid import ProductDatabase


class PathTests(unittest.TestCase):
    """
    Tests for the certlib Path class, changes to it's ROOT setting can affect
    a variety of things that only surface in anaconda.
    """

    def setUp(self):
        patcher = patch('os.path.exists')
        self.addCleanup(patcher.stop)
        mock_exists = patcher.start()
        mock_exists.return_value = True

    def tearDown(self):
        Path.ROOT = "/"

    def test_normal_root(self):
        # this is the default, but have to set it as other tests can modify
        # it if they run first.
        self.assertEqual('/etc/pki/consumer/', Path.abs('/etc/pki/consumer/'))
        self.assertEqual('/etc/pki/consumer/', Path.abs('etc/pki/consumer/'))

    def test_modified_root(self):
        Path.ROOT = '/mnt/sysimage/'
        self.assertEqual('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEqual('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_modified_root_no_trailing_slash(self):
        Path.ROOT = '/mnt/sysimage'
        self.assertEqual('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEqual('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_repo_file(self):
        # Fake that the redhat.repo exists:

        Path.ROOT = '/mnt/sysimage'
        rf = YumRepoFile()
        self.assertEqual("/mnt/sysimage/etc/yum.repos.d/redhat.repo", rf.path)

    def test_product_database(self):
        Path.ROOT = '/mnt/sysimage'
        prod_db = ProductDatabase()
        self.assertEqual('/mnt/sysimage/var/lib/rhsm/productid.js',
                prod_db.dir.abspath('productid.js'))

    def test_sysimage_pathjoin(self):
        Path.ROOT = '/mnt/sysimage'
        ed = EntitlementDirectory()
        self.assertEqual('/mnt/sysimage/etc/pki/entitlement/1-key.pem',
                Path.join(ed.productpath(), '1-key.pem'))

    def test_normal_pathjoin(self):
        ed = EntitlementDirectory()
        self.assertEqual('/etc/pki/entitlement/1-key.pem',
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


class StubPath(Path):

    @staticmethod
    def join(a, b):
        return os.path.join(a, b)

    @staticmethod
    def abs(path):
        return path

    @classmethod
    def isdir(cls, path):
        if path.endswith('.pem'):
            return False
        if path.endswith('doesnt/exist/'):
            return False
        return True


@patch('subscription_manager.certdirectory.Path', new_callable=StubPath)
class DirectoryTest(unittest.TestCase):
    klass = Directory

    def setUp(self):
        self.cleanup_paths = []
        self.d = self._get_directory()

    def tearDown(self):
        for path in self.cleanup_paths:
            rmtree(path)

    def _get_directory(self):
        temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(temp_dir)
        self.list_len = 0
        return self.klass(path=temp_dir)

    def _get_missing_directory(self):
        temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(temp_dir)
        return self.klass(path=os.path.join(temp_dir, '/doesnt/exist/'))

    def test(self, mockPath):
        self.assertEqual(len(self.d.list()), self.list_len)

    def test_listall(self, mockPath):
        self.d.list_all()

    def test_listdirs(self, mockPath):
        self.d.listdirs()

    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_missing_dir(self, mockPath, mockMakedirs, mockExists):
        mockExists.return_value = False
        self.d = self._get_missing_directory()


class DirectoryWithCertsTest(DirectoryTest):
    def _get_directory(self):
        temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(temp_dir)
        self._populate_directory(temp_dir)
        return self.klass(path=temp_dir)

    def _populate_directory(self, path):
        for i in range(1, 5):
            file_path = os.path.join(path, '%s.pem' % i)
            f = open(file_path, 'w')
            f.close()

        f = open(os.path.join(path, 'blip.blorp'), 'w')
        f.close()
        self.list_len = 4


class EntitlementDirectoryWithCertsTest(DirectoryWithCertsTest):
    klass = EntitlementDirectory

    def setUp(self):
        self.patcher = patch('subscription_manager.certdirectory.create_from_file')
        self.mock_cff = self.patcher.start()

        # sub in tmp path
        self.path_patcher = patch("subscription_manager.certdirectory.EntitlementDirectory.productpath")
        self.mock_productpath = self.path_patcher.start()

        mock_product = MagicMock()
        mock_product.id = '123456789'

        self.mock_cert = MagicMock()
        self.mock_cert.serial = '37'
        self.mock_cert.is_expired.return_value = False
        self.mock_cert.products = [mock_product]

        self.mock_cff.return_value = self.mock_cert
        super(EntitlementDirectoryWithCertsTest, self).setUp()

        self.mock_cert.key_path.return_value = self.temp_dir

    def _get_directory(self):
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(self.temp_dir)
        self._populate_directory(self.temp_dir)
        self.mock_productpath.return_value = self.temp_dir
        return self.klass()

    def _populate_directory(self, path):
        for i in range(1, 5):
            file_path = os.path.join(path, '%s.pem' % i)
            key_path = os.path.join(path, "%s-key.pem" % i)
            f = open(file_path, 'w')
            k = open(key_path, 'w')
            f.close()
            k.close()

        f = open(os.path.join(path, 'blip.blorp'), 'w')
        f.close()
        self.list_len = 4

    def _get_missing_directory(self):
        temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(temp_dir)
        self.mock_productpath.return_value = os.path.join(temp_dir, '/doesnt/exist/')
        return self.klass()

    def tearDown(self):
        self.patcher.stop()
        self.path_patcher.stop()
        super(EntitlementDirectoryWithCertsTest, self).tearDown()

    def test_list_valid(self):
        res = self.d.list_valid()
        self.assertEqual(len(res), self.list_len)

    def test_list_for_product(self):
        res = self.d.list_for_product('123')
        self.assertTrue(isinstance(res, list))

    def test_list_for_product_match(self):
        res = self.d.list_for_product('123456789')
        self.assertTrue(isinstance(res, list))


class ProductCertificateDirectoryTest(DirectoryTest):
    klass = ProductCertificateDirectory


class ProductCertificateDirectoryWithCertsTest(DirectoryWithCertsTest):
    klass = ProductCertificateDirectory

    def setUp(self):
        self.cleanup_paths = []
        self.patcher = patch('subscription_manager.certdirectory.create_from_file')
        self.mock_cff = self.patcher.start()

        mock_product = MagicMock()
        mock_product.id = '123456789'
        mock_product.provided_tags = ['mock-tag-1']

        self.mock_cert = MagicMock()
        self.mock_cert.products = [mock_product]
        self.mock_cert.serial = '37'
        self.mock_cert.is_expired.return_value = False

        self.mock_cff.return_value = self.mock_cert
        self.d = self._get_directory()

    def tearDown(self):
        self.patcher.stop()
        for path in self.cleanup_paths:
            if os.path.exists(path):
                rmtree(path)

    def test_list_valid(self):
        res = self.d.list_valid()
        self.assertEqual(len(res), self.list_len)

    def test_list_expired_no_expired(self):
        res = self.d.list_expired()
        self.assertTrue(isinstance(res, list))

    def test_list_expired_some_expired(self):
        self.mock_cert.is_expired.return_value = True
        res = self.d.list_expired()
        self.assertTrue(isinstance(res, list))
        self.assertEqual(len(res), self.list_len)

    def test_find(self):
        res = self.d.find('1')
        self.assertEqual(res, None)

    def test_find_matches(self):
        res = self.d.find('37')
        self.assertEqual(res.serial, '37')

    def test_find_by_product(self):
        res = self.d.find_by_product('123')
        self.assertEqual(res, None)

    def test_find_by_product_match(self):
        res = self.d.find_by_product('123456789')
        self.assertEqual(res, self.mock_cert)

    def test_find_all_by_product_no_match(self):
        res = self.d.find_all_by_product('123')
        self.assertTrue(isinstance(res, list))
        self.assertEqual(len(res), 0)

    def test_find_all_by_product_match(self):
        res = self.d.find_all_by_product('123456789')
        self.assertTrue(isinstance(res, list))
        self.assertEqual(len(res), 1)

    def test_get_provided_tags(self):
        res = self.d.get_provided_tags()
        self.assertTrue(isinstance(res, set))
        self.assertEqual(set(['mock-tag-1']), res)

    def test_get_installed_products(self):
        res = self.d.get_installed_products()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res), 1)

    def test_refresh(self):
        # load, and "cache", load again to hit cache,
        # refresh to clear cache, load again
        self.d.list()
        self.d.list()
        self.d.refresh()
        self.d.list()

    def test_clean(self):
        self.d.clean()

    def test_delete(self):
        self.d.delete()

    def test_str(self):
        res = "%s" % self.d
        self.assertEqual(res, self.d.path)


class ProductDirectoryTest(ProductCertificateDirectoryWithCertsTest):
    klass = ProductDirectory

    def _get_directory(self):
        int_temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(int_temp_dir)
        self._populate_directory(int_temp_dir)
        default_temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.cleanup_paths.append(default_temp_dir)
        self.list_len = 4
        return self.klass(path=int_temp_dir, default_path=default_temp_dir)


class AlsoProductDirectoryTest(unittest.TestCase):
    @patch('os.path.exists')
    def test_get_installed_products(self, MockExists):
        MockExists.return_value = True
        pd = ProductDirectory()
        top_product = StubProduct("top")
        provided_products = [StubProduct("provided")]
        pd.list = lambda: [StubProductCertificate(top_product, provided_products)]
        installed_products = pd.get_installed_products()
        self.assertTrue("top" in installed_products)

    @patch('os.path.exists')
    def test_default_products(self, MockExists):
        MockExists.return_value = True
        pd = ProductDirectory()
        top_product = StubProduct("top")
        default_product = StubProduct("default")
        pd.installed_prod_dir.list = lambda: [StubProductCertificate(top_product, [])]
        pd.default_prod_dir.list = lambda: [StubProductCertificate(default_product, [])]
        results = pd.list()
        self.assertEqual(2, len(results))
        resulting_ids = [cert.products[0].id for cert in results]
        self.assertTrue("top" in resulting_ids)
        self.assertTrue("default" in resulting_ids)

    @patch('os.path.exists')
    def test_default_products_matching_ids(self, MockExists):
        MockExists.return_value = True
        pd = ProductDirectory()
        top_product = StubProduct("top")
        default_product = StubProduct("top")
        pd.installed_prod_dir.list = lambda: [StubProductCertificate(top_product, [])]
        pd.default_prod_dir.list = lambda: [StubProductCertificate(default_product, [])]
        results = pd.list()
        self.assertEqual(1, len(results))
        resulting_ids = [cert.products[0].id for cert in results]
        self.assertTrue("top" in resulting_ids)
