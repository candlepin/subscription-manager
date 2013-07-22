import os
import shutil
import tempfile
import types
import unittest

import yum

import stubs
from subscription_manager import productid
from subscription_manager import certdirectory
from mock import Mock, patch
from fixture import SubManFixture


class StubDirectory(certdirectory.Directory):
    def __init__(self, path=None):
        self.path = path


class TestProductDatabase(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('subscription_manager.productid.DatabaseDirectory')
        self.mock_dir = self.patcher.start()
        self.temp_dir = tempfile.mkdtemp(prefix='subscription-manager-unit-tests-tmp')
        self.mock_dir.return_value = StubDirectory(path=self.temp_dir)
        self.pdb = productid.ProductDatabase()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    # mock this so we can verify we call write to create a new one
    @patch("subscription_manager.productid.ProductDatabase.write")
    def test_create_no_dir(self, mock_write):
        # tiny tmp file race here...
        no_dir = "%s/doesnt_exist" % self.temp_dir
        os.mkdir(no_dir)
        patcher = patch('subscription_manager.productid.DatabaseDirectory')
        mock_dir = patcher.start()
        mock_dir.return_value = StubDirectory(path=no_dir)

        mock_dir.write = Mock()
        productid.ProductDatabase()
        self.assertTrue(mock_write.called)

    def test_add(self):
        self.pdb.add("product", "repo")
        self.assertEquals(self.pdb.content['product'], ["repo"])

    def test_add_multiple(self):
        self.pdb.add("product", "repo1")
        self.pdb.add("product", "repo2")
        self.assertEquals(set(self.pdb.content['product']), set(['repo1', 'repo2']))

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
        self.assertEquals(0, len(self.pdb.content))

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
        self.pdb.content = {'product': 'repo'}
        repo = self.pdb.find_repos("product")
        self.assertTrue(isinstance(repo, types.ListType))
        self.assertTrue("repo" in repo)

    def test_add_old_format(self):
        self.pdb.content = {'product': 'repo'}
        self.pdb.add('product', 'repo2')
        repo = self.pdb.find_repos("product")
        self.assertTrue("repo" in repo)
        self.assertTrue("repo2" in repo)

    def test_find_repos_mixed_old_and_new_format(self):
        self.pdb.content = {'product1': 'repo1',
                            'product2': ['repo2']}
        repo1 = self.pdb.find_repos("product1")
        self.assertTrue(isinstance(repo1, types.ListType))
        self.assertTrue("repo1" in repo1)
        repo2 = self.pdb.find_repos("product2")
        self.assertTrue(isinstance(repo2, types.ListType))
        self.assertTrue("repo2" in repo2)

    def test_add_mixed_old_and_new_format(self):
        self.pdb.content = {'product1': 'product1-repo1',
                            'product2': ['product2-repo1'],
                            'product3': 'product3-repo1'}
        self.pdb.add('product2', 'product2-repo2')
        self.pdb.add('product1', 'product1-repo2')
        product1_repos = self.pdb.find_repos('product1')
        product2_repos = self.pdb.find_repos('product2')
        product3_repos = self.pdb.find_repos('product3')
        self.assertTrue(isinstance(product1_repos, types.ListType))
        self.assertTrue(isinstance(product2_repos, types.ListType))
        self.assertTrue(isinstance(product3_repos, types.ListType))
        self.assertEquals(["product1-repo1", "product1-repo2"],
                          product1_repos)
        self.assertEquals(["product2-repo1", "product2-repo2"],
                          product2_repos)
        self.assertEquals(['product3-repo1'],
                          product3_repos)

    def test_delete(self):
        self.pdb.add("product", "repo")
        self.pdb.delete("product")
        no_repo = self.pdb.find_repos("product")
        self.assertEquals(None, no_repo)

    def test_delete_non_existing(self):
        self.pdb.add("product", "repo")
        len_content = len(self.pdb.content)
        self.pdb.delete("some-other-product")
        len_content2 = len(self.pdb.content)
        self.assertEquals(len_content, len_content2)


class TestProductManager(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.prod_dir = stubs.StubProductDirectory([])
        self.prod_db_mock = Mock()
        self.prod_mgr = productid.ProductManager(product_dir=self.prod_dir,
                product_db=self.prod_db_mock)

    def test_removed(self):
        # non rhel cert, not in active, with enabled repo
        self.prod_db_mock.find_repos.return_value = ["repo1"]
        cert = self._create_non_rhel_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr.update_removed([])
        self.assertTrue(cert.delete.called)

    def test_get_enabled_no_packages(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.repos.listEnabled.return_value = []
        self.prod_mgr.get_enabled(mock_yb)

    def test_get_enabled_with_repos(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        # mock the repo metadata read of the product cert
        mock_repo = Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = Mock(return_value='somefilename')
        mock_repo.id = Mock(return_value='rhel-6-server')
        self.prod_mgr._get_cert = Mock(return_value=cert)

        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.repos.listEnabled.return_value = [mock_repo]
        self.prod_mgr.get_enabled(mock_yb)

    @patch('subscription_manager.productid.log')
    def test_get_enabled_exception(self, mock_log):
        mock_repo = Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = Mock(return_value='somefilename')
        mock_repo.id = Mock(return_value='rhel-6-server')
        self.prod_mgr._get_cert = Mock(side_effect=IOError)

        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.repos.listEnabled.return_value = [mock_repo]
        enabled = self.prod_mgr.get_enabled(mock_yb)

        self.assertTrue(mock_log.exception.called)
        self.assertEquals([], enabled)

    @patch('subscription_manager.productid.log')
    def test_get_enabled_metadata_error(self, mock_log):
        mock_repo = Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = Mock(side_effect=yum.Errors.RepoMDError)
        mock_repo.id = Mock(return_value='rhel-6-server')

        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.repos.listEnabled.return_value = [mock_repo]
        self.prod_mgr.get_enabled(mock_yb)
        self.assertTrue(mock_repo.id in self.prod_mgr.meta_data_errors)
        self.assertFalse(mock_log.exception.called)

    def test_get_active_no_packages(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.pkgSack.returnPackages.return_value = []
        active = self.prod_mgr.get_active(mock_yb)
        self.assertEquals(set([]), active)

    def test_get_active_with_active_packages(self):
        mock_yb = Mock(spec=yum.YumBase)
        mock_package = Mock(spec=yum.rpmsack.RPMInstalledPackage)
        mock_package.repoid = 'this-is-not-a-rh-repo'
        mock_package.name = 'some-cool-package'
        mock_package.arch = 'noarch'
        mock_yb.pkgSack.returnPackages.return_value = [mock_package]
        active = self.prod_mgr.get_active(mock_yb)
        self.assertEquals(set([mock_package.repoid]), active)

    def test_get_active_with_active_packages_rhel57_installed_repo(self):
        """rhel5.7 says every package is in 'installed' repo"""
        mock_yb = Mock(spec=yum.YumBase)
        mock_package = Mock(spec=yum.rpmsack.RPMInstalledPackage)
        mock_package.repoid = 'installed'
        mock_package.name = 'some-cool-package'
        mock_package.arch = 'noarch'
        mock_yb.pkgSack.returnPackages.return_value = [mock_package]
        active = self.prod_mgr.get_active(mock_yb)
        self.assertEquals(set([]), active)

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
        self.assertEquals(2, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_packages_no_repos_no_active_no_enabled(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.update_installed(set([]), set([]))
        # we should do nothing here
        self.assert_nothing_happened()

        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEquals(2, self.prod_mgr.plugin_manager.run.call_count)

    def test_update_installed_no_packages_no_repos_no_active_with_enabled(self):
        """if repos are enabled but not active, basically nothing should happen"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        enabled = [(cert, 'rhel-6-server')]

        self.prod_mgr.update_installed(enabled, set([]))

        self.assert_nothing_happened()

        self.prod_mgr.plugin_manager.run.assert_any_call('pre_product_id_install', product_list=[])
        self.prod_mgr.plugin_manager.run.assert_any_call('post_product_id_install', product_list=[])
        self.assertEquals(2, self.prod_mgr.plugin_manager.run.call_count)

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
        self.assertEquals(2, self.prod_mgr.plugin_manager.run.call_count)

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
        self.assertEquals(2, self.prod_mgr.plugin_manager.run.call_count)

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

    @patch("subscription_manager.productid.yum.YumBase", spec=yum.YumBase)
    def test_update_no_yum_base(self, mock_yb):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        mock_yb.pkgSack.returnPackages.return_value = []
        mock_yb.repos.listEnabled.return_value = []
        self.prod_mgr.update(yb=None)

        self.assert_nothing_happened()

    def test_update_no_packages_no_repos(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.pkgSack.returnPackages.return_value = []
        mock_yb.repos.listEnabled.return_value = []

        self.prod_mgr.update(mock_yb)
        # not a lot to test with no repos and no dbs
        # should be no product id db writing in this case
        self.assert_nothing_happened()

    def _create_mock_package(self, name, arch, repoid):
        mock_package = Mock(spec=yum.rpmsack.RPMInstalledPackage)
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
        mock_repo = Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = Mock(return_value='somefilename')
        mock_repo.id = repo_id
        return mock_repo

    def _create_mock_repos(self, repo_ids):
        mock_repos = []
        for repo_id in repo_ids:
            mock_repos.append(self._create_mock_repo(repo_id))
        return mock_repos

    @patch('yum.YumBase', spec=yum.YumBase)
    def test_update_with_enabled_but_not_in_active(self, mock_yb):
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

        mock_package = self._create_mock_package('some-cool-package',
                                                 'noarch',
                                                 anaconda_repo)

        mock_yb.pkgSack.returnPackages.return_value = [mock_package]

        # we only test existince of this guy... which might not
        # be correct?
        mock_yb.rpmdb.searchNevra.return_value = Mock()

        self.prod_repo_map = {'69': [anaconda_repo, "rhel-6-server-rpms"]}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        mock_yb.repos.listEnabled.return_value = self._create_mock_repos(['rhel-6-server-rpms',
                                                                          'some-other-repo'])

        cert.delete = Mock()
        self.prod_mgr.update(mock_yb)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    @patch('yum.YumBase', spec=yum.YumBase)
    def test_update_with_enabled_but_random_active_repo_provision_product_cert(self, mock_yb):
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
        mock_package = self._create_mock_package('some-cool-package',
                                                 'noarch',
                                                 random_repo)

        mock_yb.pkgSack.returnPackages.return_value = [mock_package]

        # we only test existince of this guy... which might not
        # be correct?
        mock_yb.rpmdb.searchNevra.return_value = Mock()

        # rhel6 product cert installed (by hand?)
        # but it is not in the product db
        self.prod_repo_map = {}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        mock_yb.repos.listEnabled.return_value = self._create_mock_repos(['rhel-6-server-rpms',
                                                                          random_repo])

        cert.delete = Mock()
        self.prod_mgr.update(mock_yb)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    @patch('yum.YumBase', spec=yum.YumBase)
    def test_update_pkgs_anaconda_repoid_and_rhel6_repoid(self, mock_yb):
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
        mock_packages = self._create_mock_packages([('some-cool-package',
                                                     'noarch',
                                                     anaconda_repo),
                                                    ('some-awesome-package',
                                                     'noarch',
                                                     'rhel-6-server-rpms')])
        mock_yb.pkgSack.returnPackages.return_value = mock_packages

        mock_yb.repos.listEnabled.return_value = self._create_mock_repos(['rhel-6-server-rpms'])
        # only one product cert, so find_repos is simple to mock
        self.prod_db_mock.find_repos.return_value = [anaconda_repo, "rhel-6-server-rpms"]

        cert.delete = Mock()
        self.prod_mgr.update(mock_yb)

        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    @patch('yum.YumBase', spec=yum.YumBase)
    def test_update_multiple_repos_per_productid(self, mock_yb):
        """simulate cases where multiple repo's have the same product id cert"""
        # create a rhel6 product cert
        # for this scenario, the product cert is exactly the same for each repo
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr._get_cert = Mock(return_value=cert)

        anaconda_repo = 'anaconda-RedHatEnterpriseLinux-201301150237.x86_64'
        # at least one package installed from rhel6 repo
        mock_packages = self._create_mock_packages([('some-cool-package',
                                                     'noarch',
                                                     anaconda_repo),
                                                    ('some-awesome-package',
                                                     'noarch',
                                                     'rhel-6-server-rpms')])
        mock_yb.pkgSack.returnPackages.return_value = mock_packages

        mock_repo_ids = ['rhel-6-server-rpms',
                         'rhel-6-mock-repo-2',
                         'rhel-6-mock-repo-3']

        # note that since _get_cert is patched, these all return the same
        # product cert
        mock_yb.repos.listEnabled.return_value = self._create_mock_repos(mock_repo_ids)
        self.prod_db_mock.find_repos.return_value = mock_repo_ids + [anaconda_repo]

        cert.delete = Mock()
        self.prod_mgr.update(mock_yb)

        # we should not delete, because we have a package from 'rhel-6-server-rpms' installed
        self.assertFalse(cert.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.delete.called)

    def test_update_removed_no_active_with_product_cert_anaconda_and_rhel(self):
        #"""simulate packages are installed with anaconda repo, and none
        #installed from the enabled repo. This currently causes a product
        #cert deletion"""
        cert = self._create_server_cert()
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
        #"""simulate packages are installed with anaconda repo, and none
        #installed from the enabled repo. This currently causes a product
        #cert deletion"""
        cert = self._create_server_cert()
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
        """we have a product cert, but it is not in active, but it is rhel, so do not delete"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_repo_map = {'69': 'rhel-6-server-rpms'}
        self.prod_db_mock.find_repos = Mock(side_effect=self.find_repos_side_effect)

        self.prod_mgr.update_removed(set([]))
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)
        # we have 69.pem installed, but it is not active, we
        # should delete it from prod db
        #self.prod_db_mock.delete.assert_called_with('69')
        self.assertFalse(cert.delete.called)

        self.assertFalse(self.prod_mgr.pdir.refresh.called)

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

    def _create_cert(self, product_id, label, version, provided_tags):
        cert = stubs.StubProductCertificate(
                stubs.StubProduct(product_id, label, version=version,
                                   provided_tags=provided_tags))
        cert.delete = Mock()
        cert.write = Mock()
        return cert

    def _create_desktop_cert(self):
        return self._create_cert("68", "Red Hat Enterprise Linux Desktop",
                                 "5.9", "rhel-5,rhel-5-client")

    def _create_workstation_cert(self):
        return self._create_cert("71", "Red Hat Enterprise Linux Workstation",
                                 "5.9", "rhel-5-client-workstation,rhel-5-workstation")

    def _create_server_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6", "rhel-6,rhel-6-server")

    def _create_non_rhel_cert(self):
        return self._create_cert("1234568", "Mediocre OS",
                                 "6", "medios-6,medios-6-server")

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
        self.assertEquals(filtered_certs, set([workstation_cert, server_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_desktop_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEquals(filtered_certs, set([desktop_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_workstation_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEquals(filtered_certs, set([workstation_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(no_workstation_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEquals(filtered_certs, set([server_cert, desktop_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(neither_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEquals(filtered_certs, set([server_cert]))

        filtered = self.prod_mgr._desktop_workstation_cleanup(just_both_cert_list)
        filtered_certs = set([cert for (product, cert) in filtered])
        self.assertEquals(filtered_certs, set([workstation_cert]))

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

        products_installed = self.prod_mgr.update_installed(enabled, ['repo1', 'repo2'])
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
        products_installed = self.prod_mgr.update_installed(enabled, ['repo2', 'repo1'])
        self.assertFalse(desktop_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertTrue(workstation_cert.write.called)

        self.assertFalse(desktop_cert.delete.called)
        self.assertFalse(workstation_cert.delete.called)

        self.assertTrue(workstation_cert in products_installed)
        self.assertFalse(desktop_cert in products_installed)

    @patch("subscription_manager.productid.yum")
    def test_yum_version_tracks_repos(self, yum_mock):
        yum_mock.__version_info__ = (1, 2, 2)
        self.assertFalse(self.prod_mgr._check_yum_version_tracks_repos())

        yum_mock.__version_info__ = (3, 2, 35)
        self.assertTrue(self.prod_mgr._check_yum_version_tracks_repos())

        yum_mock.__version_info__ = (3, 2, 28)
        self.assertTrue(self.prod_mgr._check_yum_version_tracks_repos())
