from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import collections
import os
import shutil
import tempfile

from . import stubs
from subscription_manager import productid
from subscription_manager import certdirectory

from rhsm.certificate2 import Product

from mock import Mock, patch
from .fixture import SubManFixture


class StubDirectory(certdirectory.Directory):
    def __init__(self, path=None):
        self.path = path


class TestComparableProductEquality(unittest.TestCase):
    product_info = {'id': 70, 'name': "Awesome OS", 'arch': ["ALL"],
             'tags': "awesomeos-1, awesomeos-1-server"}

    older = "1.0"
    newer = "1.1"

    def setUp(self):

        self.older_product = self.product(self.older)
        self.newer_product = self.product(self.newer)
        self.same_as_older = self.product(self.older)

        self.older = productid.ComparableProduct(self.older_product)
        self.newer = productid.ComparableProduct(self.newer_product)
        self.same_as_older = productid.ComparableProduct(self.same_as_older)

    def product(self, version):
        return Product(id=self.product_info['id'],
                       name=self.product_info['name'],
                       version=version,
                       architectures=self.product_info['arch'],
                       provided_tags=self.product_info['tags'])

    def test_equal(self):
        self.assertTrue(self.older == self.same_as_older)
        self.assertTrue(self.same_as_older == self.older)

        self.assertFalse(self.older == self.newer)
        self.assertFalse(self.newer == self.older)

        self.assertTrue(self.older == self.older)


class TestComparableProduct(TestComparableProductEquality):
    def test_lt(self):
        self.assertTrue(self.older < self.newer)
        self.assertFalse(self.newer < self.older)
        self.assertFalse(self.older < self.older)

    def test_gt(self):
        self.assertTrue(self.newer > self.older)
        self.assertFalse(self.older > self.newer)
        self.assertFalse(self.older > self.older)

    def test_ge(self):
        self.assertTrue(self.newer >= self.older)
        self.assertFalse(self.older >= self.newer)
        self.assertTrue(self.older >= self.older)

    def test_le(self):
        self.assertTrue(self.older <= self.newer)
        self.assertFalse(self.newer <= self.older)
        self.assertTrue(self.older <= self.older)

    def test_not_equal(self):
        self.assertTrue(self.older != self.newer)
        self.assertTrue(self.newer != self.older)

        self.assertFalse(self.older != self.same_as_older)
        self.assertFalse(self.same_as_older != self.older)
        self.assertFalse(self.older != self.older)


class TestComparableNowWithMoreDecimalPlaces(TestComparableProduct):
    older = "1"
    newer = "1.0"


class TestComparableProduct9To10(TestComparableProduct):
    older = "5.9"
    newer = "5.10"


class TestComparableToMicro(TestComparableProduct):
    older = "5.9"
    newer = "5.9.1"


class TestComparableJustMajorToMinorMicro(TestComparableProduct):
    older = "5"
    newer = "5.0.1"


class TestComparableJustMajorToManySubVersions(TestComparableProduct):
    older = "5"
    newer = "5.0.0.0.0.0.0.0.0.0.100"


class TestComparableJustMajorToMinor(TestComparableProduct):
    older = "5"
    newer = "5.11"


class TestComparableZero(TestComparableProduct):
    older = "0"
    newer = "0.0001"


class TestComparableProductMajorMinorMicro(TestComparableProduct):
    older = "10.11.3"
    newer = "10.11.20"


class TestComparableProductMajorMinorMicroMajorMinor(TestComparableProduct):
    older = "10.11.3"
    newer = "10.20"


class TestComparableProductMajor(TestComparableProduct):
    older = "10.11.3"
    newer = "31"


class TestComparableProductAlpha(TestComparableProduct):
    older = "5.11.a"
    newer = "5.11.b"


class TestComparableProductNumberToAlpha(TestComparableProduct):
    older = "5.11.10"
    newer = "5.11.10b"


class TestComparableProductJustAlpha(TestComparableProduct):
    older = "D"
    newer = "E"


class TestComparableProductMutliAlpha(TestComparableProduct):
    older = "a.b.b"
    newer = "a.b.c"


class TestComparableProductShortAlpha(TestComparableProduct):
    older = "a.b.c"
    newer = "a.c"


class TestCompareBetaGA(TestComparableProduct):
    older = "5.10 Beta"
    newer = "5.10 GA"


class TestCompareBetaProductNoGa(TestComparableProduct):
    older = "5.10 Beta"
    newer = "5.10"


class TestCompareBetaProductHyphen(TestComparableProduct):
    older = "5.10-Beta"
    newer = "5.10"


class TestCompareELSProduct(TestComparableProduct):
    older = "4 ELS"
    newer = "4.2.0 ELS"


class TestCompareAlphaBetaProduct(TestComparableProduct):
    older = "5.10 Alpha"
    newer = "5.10 Beta"


class TestCompareAlphaBetaProductHyphen(TestComparableProduct):
    older = "5.10-Alpha"
    newer = "5.10 Beta"


class TestCompareAlphaProductHyphen(TestComparableProduct):
    older = "5.10-Alpha"
    newer = "5.10"


class TestComparableProductCert(TestComparableProduct):
    def setUp(self):
        self.older_product_cert = self._create_older_cert()
        self.new_product_cert = self._create_newer_cert()
        self.same_as_older_cert = self._create_older_cert()

        self.older = productid.ComparableProductCert(self.older_product_cert)
        self.newer = productid.ComparableProductCert(self.new_product_cert)
        self.same_as_older = productid.ComparableProductCert(self.same_as_older_cert)

    def _create_older_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6", "rhel-6,rhel-6-server")

    def _create_newer_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6.1", "rhel-6,rhel-6-server")

    def _create_cert(self, product_id, label, version, provided_tags):
        cert = stubs.StubProductCertificate(
                stubs.StubProduct(product_id, label, version=version,
                                   provided_tags=provided_tags))
        cert.delete = Mock()
        cert.write = Mock()
        return cert


class TestProductDatabase(unittest.TestCase):
    def setUp(self):
        patcher = patch('subscription_manager.productid.DatabaseDirectory')
        self.mock_dir = patcher.start()
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.mock_dir.return_value = StubDirectory(path=self.temp_dir)
        self.pdb = productid.ProductDatabase()

        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # mock this so we can verify we call write to create a new one
    @patch("subscription_manager.productid.ProductDatabase.write")
    def test_create_no_dir(self, mock_write):
        # tiny tmp file race here...
        no_dir = "%s/doesnt_exist" % self.temp_dir
        os.mkdir(no_dir)
        with patch('subscription_manager.productid.DatabaseDirectory') as mock_dir:
            mock_dir.return_value = StubDirectory(path=no_dir)
            mock_dir.write = Mock()
            productid.ProductDatabase()
            self.assertTrue(mock_write.called)

    def test_add(self):
        self.pdb.add("product", "repo")
        self.assertEqual(self.pdb.content['product'], ["repo"])

    def test_add_multiple(self):
        self.pdb.add("product", "repo1")
        self.pdb.add("product", "repo2")
        self.assertEqual(set(self.pdb.content['product']), set(['repo1', 'repo2']))

    def test_write(self):
        self.pdb.add("product", "repo")
        self.pdb.write()

    @patch('subscription_manager.productid.json.dump', side_effect=IOError)
    def test_write_exception(self, mock_dumps):
        self.pdb.add("product", "repo")
        # mostly looking for no exception here
        self.pdb.write()
        # let's read it back and verify we didnt right anything
        # but reset in memoty version first
        self.pdb.content = {}
        self.pdb.read()
        self.assertEqual(0, len(self.pdb.content))

    def test_read(self):
        f = open(self.pdb.dir.abspath('productid.js'), 'w')
        buf = """{"12345": "rhel-6"}\n"""
        f.write(buf)
        f.close()
        self.pdb.read()
        self.assertTrue("12345" in self.pdb.content)

    @patch('subscription_manager.productid.json.load', side_effect=IOError)
    def test_read_exception(self, mock_load):
        f = open(self.pdb.dir.abspath('productid.js'), 'w')
        buf = """{"12345": "rhel-6"}\n"""
        f.write(buf)
        f.close()
        self.pdb.read()
        self.assertFalse("12345" in self.pdb.content)

#    # not sure this case is worth handling
#    @patch("__builtin__.open", side_effect=IOError)
#    def test_read_open_fails(self, mock_open):
#        self.pdb.read()

    def test_find_repos(self):
        self.pdb.add("product", "repo")
        repo = self.pdb.find_repos("product")
        self.assertTrue("repo" in repo)

    def test_find_repos_old_format(self):
        self.pdb.populate_content({'product': 'repo'})
        repo = self.pdb.find_repos("product")
        self.assertTrue(isinstance(repo, collections.Iterable))
        self.assertTrue("repo" in repo)

    def test_add_old_format(self):
        self.pdb.populate_content({'product': 'repo'})
        self.pdb.add('product', 'repo2')
        repo = self.pdb.find_repos("product")
        self.assertTrue("repo" in repo)
        self.assertTrue("repo2" in repo)

    def test_find_repos_mixed_old_and_new_format(self):
        self.pdb.populate_content({'product1': 'repo1',
                                   'product2': ['repo2']})
        repo1 = self.pdb.find_repos("product1")
        self.assertTrue(isinstance(repo1, collections.Iterable))
        self.assertTrue("repo1" in repo1)
        repo2 = self.pdb.find_repos("product2")
        self.assertTrue(isinstance(repo2, collections.Iterable))
        self.assertTrue("repo2" in repo2)

    def test_add_mixed_old_and_new_format(self):
        self.pdb.populate_content({'product1': 'product1-repo1',
                                   'product2': ['product2-repo1'],
                                   'product3': 'product3-repo1'})
        self.pdb.add('product2', 'product2-repo2')
        self.pdb.add('product1', 'product1-repo2')
        product1_repos = self.pdb.find_repos('product1')
        product2_repos = self.pdb.find_repos('product2')
        product3_repos = self.pdb.find_repos('product3')
        self.assertTrue(isinstance(product1_repos, collections.Iterable))
        self.assertTrue(isinstance(product2_repos, collections.Iterable))
        self.assertTrue(isinstance(product3_repos, collections.Iterable))
        self.assertEqual(["product1-repo1", "product1-repo2"],
                          product1_repos)
        self.assertEqual(["product2-repo1", "product2-repo2"],
                          product2_repos)
        self.assertEqual(['product3-repo1'],
                          product3_repos)

    def test_delete(self):
        self.pdb.add("product", "repo")
        self.pdb.delete("product")
        no_repo = self.pdb.find_repos("product")
        self.assertEqual(None, no_repo)

    def test_delete_non_existing(self):
        self.pdb.add("product", "repo")
        len_content = len(self.pdb.content)
        self.pdb.delete("some-other-product")
        len_content2 = len(self.pdb.content)
        self.assertEqual(len_content, len_content2)


class TestProductManager(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.prod_dir = stubs.StubProductDirectory([])
        self.prod_db_mock = Mock()
        self.prod_mgr = productid.ProductManager(product_dir=self.prod_dir,
                product_db=self.prod_db_mock)

    def assert_nothing_happened(self):
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repos.called)

    def test_update_installed_no_packages_no_repos_no_active_no_enabled_no_certs(self):
        self.prod_mgr.update_installed(set([]), set([]))
        # we should do nothing here
        self.assert_nothing_happened()

        # plugin should get called with empty list
        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEqual(4, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_packages_no_repos_no_active_no_enabled(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.update_installed(set([]), set([]))
        # we should do nothing here
        self.assert_nothing_happened()

        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEqual(4, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_packages_no_repos_no_active_with_enabled(self):
        """if repos are enabled but not active, basically nothing should happen"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        enabled = [(cert, 'rhel-6-server')]

        self.prod_mgr.update_installed(enabled, set([]))

        self.assert_nothing_happened()

        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEqual(4, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_packages_no_repos_with_active_with_enabled(self):
        """rhel-6-server enabled and active, with product cert already installed should do nothing"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        enabled = [(cert, 'rhel-6-server')]
        active = set(['rhel-6-server'])

        # mock this so we can verify it's called correctly
        self.prod_dir.find_by_product = Mock(return_value=cert)
        self.prod_mgr._is_desktop = Mock(return_value=False)
        self.prod_mgr._is_workstation = Mock(return_value=False)

        self.prod_repo_map = {'69': 'rhel-6-server'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)
        # this is the normal case, with a product cert already installed,
        #  the repo enabled, and packages installed from it (active)
        self.prod_mgr.update_installed(enabled, active)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)

        self.assertTrue(self.prod_mgr._is_desktop.called)
        self.assertTrue(self.prod_mgr._is_workstation.called)

        self.prod_dir.find_by_product.assert_called_with('69')
        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEqual(4, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_product_certs_with_active_with_enabled(self):
        """no product cert, repo enabled and active, cert should be installed.
        This is the new product cert scenario"""

        # simulate the cert from the repo metadata, not the cert isnt added to
        # the product dir
        cert = self._create_server_cert()

        enabled = [(cert, 'rhel-6-server')]
        active = set(['rhel-6-server'])

        #self.prod_repo_map = {'69': 'rhel-6-server'}
        self.prod_repo_map = {}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        cert.write = Mock()
        self.prod_dir.find_by_product = Mock(return_value=None)
        self.prod_mgr._is_desktop = Mock(return_value=False)
        self.prod_mgr._is_workstation = Mock(return_value=False)

        # we dont actually use the return value anywhere...
        self.prod_mgr.update_installed(enabled, active)

        self.prod_dir.find_by_product.assert_called_with('69')
        self.assertTrue(cert.write.called)
        self.assertTrue(self.prod_mgr._is_desktop.called)
        self.assertTrue(self.prod_mgr._is_workstation.called)
        self.assertTrue(self.prod_db_mock.add.called)
        self.assertTrue(self.prod_db_mock.write.called)

        self.prod_db_mock.add.assert_called_with('69', 'rhel-6-server')
        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[(cert.product, cert)])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[cert])
        self.assertEqual(4, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_active_with_product_certs_installed_anaconda(self):
        """simulate no active packages (since they are installed via anaconda) repos
        but product cert installed.  variations of rh#859197"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        enabled = [(cert, 'rhel-6-server')]
        active = set([])

        cert.write = Mock()
        self.prod_dir.find_by_product = Mock(return_value=None)
        self.prod_mgr._is_desktop = Mock(return_value=False)
        self.prod_mgr._is_workstation = Mock(return_value=False)

        # we dont actually use the return value anywhere...
        self.prod_mgr.update_installed(enabled, active)

    def test_update_no_packages_no_repos(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        enabled = []
        active = []

        self.prod_mgr.update(enabled, active, False)
        # not a lot to test with no repos and no dbs
        # should be no product id db writing in this case
        self.assert_nothing_happened()

    def _create_mock_package(self, name, arch, repoid):
        mock_package = Mock()
        mock_package.repoid = repoid
        mock_package.name = name
        mock_package.arch = arch
        return mock_package

    def _create_mock_packages(self, package_infos):
        mock_packages = []
        for package_info in package_infos:
            # (name, arch, repoid) in package_info tuple
            mock_packages.append(self._create_mock_package(package_info[0],
                                                           package_info[1],
                                                           package_info[2]))
        return mock_packages

    def _create_mock_repo(self, repo_id):
        mock_repo = Mock()
        mock_repo.retrieveMD = Mock(return_value='somefilename')
        mock_repo.id = repo_id
        return mock_repo

    def _create_mock_repos(self, repo_ids):
        mock_repos = []
        for repo_id in repo_ids:
            mock_repos.append(self._create_mock_repo(repo_id))
        return mock_repos

    def test_update_with_enabled_but_not_in_active(self):
        """rhel6 repo is enabled, but it is not active, ala anaconda

        We are simulating post anaconda setup, with a registered client,
        subscribed to a rhel6 channel, but that hasn't installed anything
        from that channel yet. If yum is ran, and does not install something
        from rhel-6-server-rpms, we enter ProductManager.update with this
        scenario.

        product cert: installed (69.pem via anaconda)
        enabled repos: rhel-6-server-rpms
        active repos: ['anaconda']
        productid.js: 69 -> anaconda

        Expected: 69.pem to not be deleted
                  no other certs to install
                  (ie, nothing)
        Actual: 69.pem is deleted
                (no product cert installed, productid.js db not updated)
                since the enabled 'rhel-6-server-rpms' repo is not in 'active',
                we delete the 69.product cert
        """
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr._get_cert = Mock(return_value=cert)

        anaconda_repo = 'anaconda-RedHatEnterpriseLinux-201301150237.x86_64'

        self.prod_repo_map = {'69': [anaconda_repo, "rhel-6-server-rpms"]}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        enabled = [(cert, 'rhel-6-server-rpms'),
                   (cert, 'some-other-repo')]
        active = ['anaconda']
        cert.delete = Mock()
        self.prod_mgr.update(enabled, active, False)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_with_enabled_but_random_active_repo_provision_product_cert(self):
        """rhel6 repo is enabled, but it is not active, ala anaconda

        We are simulating post anaconda setup, with a registered client,
        subscribed to a rhel6 channel, but that hasn't installed anything
        from that channel yet. yum thinks all the packages are from another
        repo (say, maybe a local install repo without a product cert)
        If yum is ran, and does not install something
        from rhel-6-server-rpms, we enter ProductManager.update with this
        scenario.

        product cert: installed (69.pem via anaconda)
        enabled repos: rhel-6-server-rpms
        active repos: ['some-other-thing']
        productid.js: 69 -> some-other-thing

        Expected: 69.pem to not be deleted
                  no other certs to install
                  (ie, nothing)
        """
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr._get_cert = Mock(return_value=cert)

        random_repo = 'whatever-dude-repo'

        # rhel6 product cert installed (by hand?)
        # but it is not in the product db
        self.prod_repo_map = {}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        enabled = [(cert, 'rhel-6-server-rpms')]
        active = [random_repo]

        cert.delete = Mock()
        self.prod_mgr.update(enabled, active, tracks_repos=True)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_pkgs_anaconda_repoid_and_rhel6_repoid(self):
        """simulate a freshish install, with at least one package from rhel6 installed

        product cert: installed (69.pem)
        enabled repos: rhel-6-server-rpms
        active repos: ['rhel-6-server-rpms']
        productid.js: 69-> anaconda  (note, this is wrong)

        Expected: 69.pem to not be deleted
                  no other certs to install
                  (ie, nothing)
        Actual: 69.pem is deleted
                (no product cert installed, productid.js db not updated)
                since the enabled 'rhel-6-server-rpms' repo is not in 'active',
                we delete the 69.product cert
        """
        # create a rhel6 product cert
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr._get_cert = Mock(return_value=cert)

        anaconda_repo = 'anaconda-RedHatEnterpriseLinux-201301150237.x86_64'
        # at least one package installed from rhel6 repo

        enabled = [(cert, 'rhel-6-server-rpms')]
        active = ['rhel-6-server-rpms']
        # only one product cert, so find_repos is simple to mock
        self.prod_db_mock.find_repos.return_value = [anaconda_repo, "rhel-6-server-rpms"]

        cert.delete = Mock()
        self.prod_mgr.update(enabled, active, tracks_repos=True)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_multiple_repos_per_productid(self):
        """simulate cases where multiple repo's have the same product id cert"""
        # create a rhel6 product cert
        # for this scenario, the product cert is exactly the same for each repo
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr._get_cert = Mock(return_value=cert)

        anaconda_repo = 'anaconda-RedHatEnterpriseLinux-201301150237.x86_64'

        mock_repo_ids = ['rhel-6-server-rpms',
                         'rhel-6-mock-repo-2',
                         'rhel-6-mock-repo-3']

        # note that since _get_cert is patched, these all return the same
        # product cert
        enabled = [(cert, 'rhel-6-server-rpms'),
                   (cert, 'rhel-6-mock-repo-2'),
                   (cert, 'rhel-6-mock-repo-3')]
        active = ['rhel-6-server-rpms',
                  'rhel-6-mock-repo-2',
                  'rhel-6-mock-repo-3']
        self.prod_db_mock.find_repos.return_value = mock_repo_ids + [anaconda_repo]

        cert.delete = Mock()
        self.prod_mgr.update(enabled, active, tracks_repos=True)

        # we should not delete, because we have a package from 'rhel-6-server-rpms' installed
        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_productid_update_repo_with_updated_product_cert(self):
        """Test the case of a new product cert being available in an enabled
        and active repo. This is testing product cert version updating."""
        # create a rhel6 product cert and add to the local installed product
        # dir.
        old_cert = self._create_server_cert()
        self.prod_dir.certs.append(old_cert)

        # the repo has a new product cert in it's md
        new_cert = self._create_newer_server_cert()
        self.prod_mgr._get_cert = Mock(return_value=new_cert)

        enabled = [(new_cert, 'rhel-6-server-rpms')]
        active = ['rhel-6-server-rpms']

        self.prod_db_mock.find_repos.return_value = ['rhel-6-server-rpms']

        # disarm cert delete
        old_cert.delete = Mock()

        self.prod_mgr.update(enabled, active, tracks_repos=True)

        # not removing the product, should delete the cert...yet
        self.assertFalse(new_cert.delete.called)
        # product db should not change
        self.assertFalse(self.prod_db_mock.delete.called)
        # new cert is written
        self.assertTrue(new_cert.write.called)

    def test_productid_update_repo_with_same_product_cert(self):
        """Test the case of a new product cert being available in an enabled
        and active repo. This is testing product cert version updating."""
        # create a rhel6 product cert and add to the local installed product
        # dir.
        old_cert = self._create_server_cert()
        self.prod_dir.certs.append(old_cert)

        # the repo has a new product cert in it's md
        same_cert = self._create_server_cert()
        self.prod_mgr._get_cert = Mock(return_value=same_cert)

        enabled = [(old_cert, 'rhel-6-server-rpms')]
        active = ['rhel-6-server-rpms']

        self.prod_db_mock.find_repos.return_value = ['rhel-6-server-rpms']

        # disarm cert delete
        old_cert.delete = Mock()

        self.prod_mgr.update(enabled, active, tracks_repos=True)

        # not removing the product, should delete the cert...yet
        self.assertFalse(same_cert.delete.called)
        # product db should not change
        self.assertFalse(self.prod_db_mock.delete.called)
        # new cert is not written or updated
        self.assertFalse(same_cert.write.called)

    def test_product_update_repo_with_older_product_cert(self):
        """Test the case of a new product cert being available in an enabled
        and active repo. This is testing product cert version updating."""
        # create a rhel6 product cert and add to the local installed product
        # dir.
        installed_cert = self._create_newer_server_cert()
        self.prod_dir.certs.append(installed_cert)

        # the repo has a new product cert in it's md
        older_cert = self._create_server_cert()
        self.prod_mgr._get_cert = Mock(return_value=older_cert)

        enabled = [(installed_cert, 'rhel-6-server-rpms')]
        active = ['rhel-6-server-rpms']

        self.prod_db_mock.find_repos.return_value = ['rhel-6-server-rpms']

        # disarm cert delete
        installed_cert.delete = Mock()

        self.prod_mgr.update(enabled, active, tracks_repos=True)

        # not removing the product, should delete the cert...yet
        self.assertFalse(older_cert.delete.called)
        # product db should not change
        self.assertFalse(self.prod_db_mock.delete.called)
        # new cert is not written or updated
        self.assertFalse(older_cert.write.called)

    def test_update_no_active_with_product_cert_anaconda_and_rhel(self):
        """
        Test the case where we have one arbitrary repo with nothing installed
        and another repo that is temporarily disabled.

        Expected:
            The product id for the no longer active repo is deleted.
        Actual:
            BZ 1222627.
            The product id for the no longer active repo remains.
        """
        jboss_cert = self._create_cert("183", "jboss", "1.0", "jboss")
        server_cert = self._create_server_cert()
        self.prod_dir.certs.append(jboss_cert)
        self.prod_dir.certs.append(server_cert)

        self.prod_repo_map = {
            "183": ['some-other-repo'],
            "69": ['rhel-6-server-rpms']
        }
        self.prod_db_mock.find_repos = Mock(
                side_effect=self.find_repos_side_effect)
        enabled = [(jboss_cert, 'some-other-repo'),
                   (server_cert, 'rhel-6-server-rpms')]
        # There should be no active repos because in this case we are
        # temporarily disabling the 'rhel-6-server-rpms' repo
        active = set([])
        temp_disabled_repos = ['rhel-6-server-rpms']
        self.prod_mgr.find_temp_disabled_repos = Mock(
                return_value=temp_disabled_repos)

        self.prod_mgr.update(enabled, active, tracks_repos=True)

        self.assertTrue(jboss_cert.delete.called)
        self.assertTrue(self.prod_db_mock.delete.called)
        self.assertFalse(server_cert.delete.called)

    def test_update_removed_product_cert_in_protected_dir(self):
        """Simulates situation, when there is product certificate
        in protected directory"""
        cert = self._create_non_rhel_cert()
        self.prod_dir.certs.append(cert)

        # Modify path of cert to be in protected directory
        cert.path = '/etc/pki/product-default/fake_product.pem'

        self.prod_mgr.pdir.refresh = Mock()

        # Simulate situation, where product cert would be deleted outside
        # protected directory
        self.prod_repo_map = {'1234568': 'medios-6-server-rpms'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        self.prod_mgr.update_removed(set([]))

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_removed_no_active_with_product_cert_anaconda_and_rhel(self):
        """Simulate packages are installed with anaconda repo, and none
        installed from the enabled repo."""
        cert = self._create_server_cert()
        # Prod. cert. is in protected directory
        cert.path = '/etc/pki/product-default/69.pem'
        self.prod_dir.certs.append(cert)

        self.prod_db_mock.find_repos.return_value = ["anaconda", "rhel-6-server-rpms"]
        # we have rhel6 product id installed, and the repo is enabled, but
        # we have no packages installed from that repo (they are from the anconda
        # repo)

        cert.delete = Mock()
        self.prod_mgr.update_removed(set(['some-random-thing']))

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_removed_no_active_with_product_cert_anaconda(self):
        """Simulate packages are installed with anaconda repo, and none
        installed from the enabled repo."""
        cert = self._create_server_cert()
        # Prod. cert. is in protected directory
        cert.path = '/etc/pki/product-default/69.pem'
        self.prod_dir.certs.append(cert)

        self.prod_db_mock.find_repos.return_value = ["anaconda"]
        # we have rhel6 product id installed, and the repo is enabled, but
        # we have no packages installed from that repo (they are from the anconda
        # repo)

        cert.delete = Mock()
        self.prod_mgr.update_removed(set(['some-random-thing']))

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

#TODO: test update_installed with a installed product cert, enabled, but not active
#       because the packages were installed from anaconda

    def test_update_removed_no_packages_no_repos_no_active_no_certs(self):
        self.prod_mgr.update_removed(set([]))
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)

    def test_update_removed_metadata_errors(self):
        """verify we dont delete a repo if there was a metadata error for that repo"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr.meta_data_errors = ['rhel-6-server-rpms']
        self.prod_db_mock.find_repos.return_value = ["rhel-6-server-rpms"]
        self.prod_mgr.update_removed(set([]))
        self.assertFalse(cert.delete.called)

    def test_update_removed_repo_not_found_in_db(self):
        """product cert with a repo that we dont have in productid db.
           we should not delete the cert """
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_db_mock.find_repos.return_value = None
        self.prod_mgr.update_removed(set([]))
        self.assertFalse(cert.delete.called)

    def test_update_removed_repo_in_active(self):
        """product cert with a repo, that is active, should not
        delete the certificate"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_db_mock.find_repos.return_value = ["rhel-6-server-rpms"]

        self.prod_mgr.update_removed(set(['rhel-6-server-rpms']))
        self.assertFalse(cert.delete.called)

    def test_update_removed_no_packages_no_repos_no_active_rhel(self):
        """
        We have a product cert, It is not in active, but it is in protected
        directory. Thus it will not be deleted.
        """
        cert = self._create_server_cert()
        # Prod. cert. is in protected directory
        cert.path = '/etc/pki/product-default/69.pem'
        self.prod_dir.certs.append(cert)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_repo_map = {'69': 'rhel-6-server-rpms'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        self.prod_mgr.update_removed(set([]))
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(cert.delete.called)

        self.assertFalse(self.prod_mgr.pdir.refresh.called)

    def test_update_removed_non_rhel_repo_disabled(self):
        cert1 = self._create_server_cert()
        cert1.path = '/etc/pki/product-default/69.pem'
        self.prod_dir.certs.append(cert1)

        cert2 = self._create_non_rhel_cert()
        self.prod_dir.certs.append(cert2)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_repo_map = {'69': 'rhel-6-server-rpms',
                              '12345678': 'medios-6-server-rpms'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        self.prod_mgr.update_removed(set(['rhel-6-server-rpms']),
                                     temp_disabled_repos=['medios-6-server-rpms'])
        self.assertFalse(cert1.delete.called)
        self.assertFalse(cert2.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)

        self.prod_mgr.update_removed(set(['rhel-6-server-rpms', 'medios-6-server-rpms']),
                                     temp_disabled_repos=['medios-6-server-rpms'])
        self.assertFalse(cert1.delete.called)
        self.assertFalse(cert2.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)

    def test_update_removed_no_packages_no_repos_no_active(self):
        """we have a product cert, but it is not in active, so it
        should be deleted"""
        cert = self._create_non_rhel_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_repo_map = {'1234568': 'medios-6-server-rpms'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        self.prod_mgr.update_removed(set([]))
        self.assertTrue(self.prod_db_mock.delete.called)
        self.assertTrue(self.prod_db_mock.write.called)
        # we have 1234568.pem installed, but it is not active, we
        # should delete it from prod db
        self.prod_db_mock.delete.assert_called_with('1234568')
        self.assertTrue(cert.delete.called)

        self.assertTrue(self.prod_mgr.pdir.refresh.called)
        # TODO self.prod_mgr.pdir.refresh is called

        # TODO: test if pdir handles things added to it while iterating over it
        # TODO: test if product_id plugins are called on just product deletion
        # TODO: test if we support duplicates in enabled repo list
        # TODO: is there a reason available is a set and enabled is a list? if so, test those cases

    def test_update_removed_disabled_repos(self):
        """We have a product cert, that maps to repos that are being disabled via
        the yum commandline --disablerepo. We should not delete certs in that case."""
        cert = self._create_non_rhel_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_repo_map = {'1234568': 'medios-6-server-rpms'}
        self.prod_db_mock.find_repos.return_value = None

        # How would we have a repo be disabled but in active? If it includes
        # packages that are installed that are also in a different enabled repo.
        self.prod_mgr.update_removed(set(['medios-6-server-rpms']),
                                     temp_disabled_repos=['medios-6-server-rpms'])
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(cert.delete.called)

    def _create_cert(self, product_id, label, version, provided_tags, prod_default=False):
        cert = stubs.StubProductCertificate(
                stubs.StubProduct(product_id, label, version=version,
                                   provided_tags=provided_tags))
        cert.delete = Mock()
        cert.write = Mock()
        if prod_default:
            cert.path = '/etc/pki/product-default/' + product_id + '.pem'
        else:
            cert.path = '/etc/pki/product/' + product_id + '.pem'
        return cert

    def _create_desktop_cert(self):
        return self._create_cert("68", "Red Hat Enterprise Linux Desktop",
                                 "5.9", "rhel-5,rhel-5-client", True)

    def _create_workstation_cert(self):
        return self._create_cert("71", "Red Hat Enterprise Linux Workstation",
                                 "5.9", "rhel-5-client-workstation,rhel-5-workstation", True)

    def _create_newer_workstation_cert(self):
        return self._create_cert("71", "Red Hat Enterprise Linux Workstation",
                                 "5.10", "rhel-5-client-workstation,rhel-5-workstation", True)

    def _create_server_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6", "rhel-6,rhel-6-server", True)

    def _create_newer_server_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6.1", "rhel-6,rhel-6-server", True)

    def _create_non_rhel_cert(self):
        return self._create_cert("1234568", "Mediocre OS",
                                 "6", "medios-6,medios-6-server", False)

    def test_is_workstation(self):
        workstation_cert = self._create_workstation_cert()
        self.assertTrue(self.prod_mgr._is_workstation(
            workstation_cert.products[0]))

    def test_is_desktop(self):
        desktop_cert = self._create_desktop_cert()
        self.assertTrue(self.prod_mgr._is_desktop(
            desktop_cert.products[0]))

    def _gen_pc_list(self, cert_list):
        return [(cert.products[0], cert) for cert in cert_list]

    def test_list_has_workstation_and_desktop_cert(self):
        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()
        server_cert = self._create_server_cert()

        all_cert_list = self._gen_pc_list([desktop_cert, workstation_cert, server_cert])
        just_desktop_cert_list = self._gen_pc_list([desktop_cert])
        just_workstation_cert_list = self._gen_pc_list([workstation_cert])
        no_workstation_cert_list = self._gen_pc_list([desktop_cert, server_cert])
        neither_cert_list = self._gen_pc_list([server_cert])
        just_both_cert_list = self._gen_pc_list([workstation_cert, desktop_cert])

        # has desktop and workstation
        self.assertTrue(self.prod_mgr._list_has_workstation_and_desktop_cert(all_cert_list))
        self.assertTrue(self.prod_mgr._list_has_workstation_and_desktop_cert(just_both_cert_list))

        self.assertFalse(self.prod_mgr._list_has_workstation_and_desktop_cert(just_desktop_cert_list))
        self.assertFalse(self.prod_mgr._list_has_workstation_and_desktop_cert(just_workstation_cert_list))
        self.assertFalse(self.prod_mgr._list_has_workstation_and_desktop_cert(neither_cert_list))
        self.assertFalse(self.prod_mgr._list_has_workstation_and_desktop_cert(no_workstation_cert_list))

    def test_desktop_workstation_cleanup(self):
        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()
        server_cert = self._create_server_cert()

        all_cert_list = self._gen_pc_list([desktop_cert, workstation_cert, server_cert])
        just_desktop_cert_list = self._gen_pc_list([desktop_cert])
        just_workstation_cert_list = self._gen_pc_list([workstation_cert])
        no_workstation_cert_list = self._gen_pc_list([desktop_cert, server_cert])
        neither_cert_list = self._gen_pc_list([server_cert])
        just_both_cert_list = self._gen_pc_list([workstation_cert, desktop_cert])

        filtered = self.prod_mgr._desktop_workstation_cleanup(all_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([workstation_cert, server_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_desktop_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([desktop_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_workstation_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([workstation_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(no_workstation_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([server_cert, desktop_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(neither_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([server_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_both_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEqual(filtered_certs, set([workstation_cert]))

    def find_repos_side_effect(self, product_hash):
        return self.prod_repo_map.get(product_hash)

    # If Desktop cert exists, delete it and then write Workstation:
    def test_workstation_overrides_desktop(self):

        desktop_cert = self._create_desktop_cert()
        self.prod_dir.certs.append(desktop_cert)
        workstation_cert = self._create_workstation_cert()

        self.prod_repo_map = {'71': ["repo2"],
                              '68': ["repo1"]}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        # Desktop comes first in this scenario:
        enabled = [
                (desktop_cert, 'repo1'),
                (workstation_cert, 'repo2'),
        ]

        self.prod_mgr.update_installed(enabled, ['repo1', 'repo2'])

        self.assertTrue(desktop_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertTrue(workstation_cert.write.called)
        self.prod_db_mock.delete.assert_called_with("68")

    # If workstation cert exists, desktop write should be skipped:
    def test_workstation_skips_desktop(self):

        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()
        self.prod_dir.certs.append(workstation_cert)
        some_other_cert = stubs.StubProductCertificate(
            stubs.StubProduct("8127", "Some Other Product"))
        some_other_cert.delete = Mock()
        some_other_cert.write = Mock()

        self.prod_repo_map = {'71': ["repo2"],
                              '68': ["repo1"],
                              '8127': ["repo3"]}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        # Workstation comes first in this scenario:
        enabled = [
                (workstation_cert, 'repo2'),
                (desktop_cert, 'repo1'),
                (some_other_cert, 'repo3'),
        ]

        self.prod_mgr.update_installed(enabled, ['repo1', 'repo2', 'repo3'])

        self.assertFalse(workstation_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertFalse(desktop_cert.delete.called)

        # Testing a bug where desktop cert skipping ended the whole process:
        self.assertTrue(some_other_cert.write.called)
        self.assertFalse(some_other_cert.delete.called)

        self.assertFalse(self.prod_db_mock.delete.called)

    def test_workstation_desktop_same_time(self):

        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()
        #self.prod_dir.certs.append(workstation_cert)

        self.prod_repo_map = {}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        # Desktop comes first in this scenario:
        enabled = [
                (desktop_cert, 'repo1'),
                (workstation_cert, 'repo2'),
        ]

        products_installed, products_updated = self.prod_mgr.update_installed(enabled, ['repo1', 'repo2'])
        self.assertFalse(desktop_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertTrue(workstation_cert.write.called)

        self.assertFalse(desktop_cert.delete.called)
        self.assertFalse(workstation_cert.delete.called)

        self.assertTrue(workstation_cert in products_installed)
        self.assertFalse(desktop_cert in products_installed)

        self.assertTrue(self.prod_db_mock.add.called)
        self.assertTrue(self.prod_db_mock.write.called)

        # verify the list order doesnt matter
        products_installed, products_updated = self.prod_mgr.update_installed(enabled, ['repo2', 'repo1'])
        self.assertFalse(desktop_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertTrue(workstation_cert.write.called)

        self.assertFalse(desktop_cert.delete.called)
        self.assertFalse(workstation_cert.delete.called)

        self.assertTrue(workstation_cert in products_installed)
        self.assertFalse(desktop_cert in products_installed)
