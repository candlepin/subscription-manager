# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

import imp
import os
import types


import mock
from nose.plugins.skip import SkipTest

try:
    import yum
except ImportError as e:
    raise SkipTest(e)


from . import fixture
from . import stubs

import subscription_manager.injection as inj
from subscription_manager import productid

# Yeah, this is weird. The yum plugins aren't on sys.path, nor are they in the
# local src path that nosetest searches for modules. src/plugins is also not a
# package dir (no __init__). And to top it off, the module name isn't a valid
# python module name ('product-id.py', ie with an invalid '-').
plugin_file_path = os.path.join(os.path.dirname(__file__), '../src/plugins/product-id.py')
plugin_file = open(plugin_file_path, 'r')

dir_path, module_name = os.path.split(plugin_file_path)
module_name = module_name.split(".py")[0]


# NOTE: the yum plugin 'product-id' gets imported as yum_product_id
fp, pathname, description = imp.find_module(module_name, [dir_path])
try:
    yum_product_id = imp.load_module('yum_product_id', fp, pathname, description)
finally:
    fp.close()


class TestYumPluginModule(fixture.SubManFixture):
    def setUp(self):
        super(TestYumPluginModule, self).setUp()

    def test(self):
        self.assertTrue(isinstance(yum_product_id, types.ModuleType))
        return


class TestYumProductManager(fixture.SubManFixture):
    def setUp(self):
        super(TestYumProductManager, self).setUp()
        self.pdb_patcher = mock.patch('subscription_manager.productid.ProductDatabase',
                                      spec=productid.ProductDatabase)
        self.mock_pdb = self.pdb_patcher.start()

        self.yb_patcher = mock.patch('yum.YumBase', spec=yum.YumBase)
        self.mock_yb = self.yb_patcher.start()

    def tearDown(self):
        self.pdb_patcher.stop()
        self.yb_patcher.stop()

    @mock.patch('yum.YumBase', spec=yum.YumBase)
    def test(self, mock_yb):
        yum_product_id.YumProductManager(mock_yb)

    def test_get_enabled_no_packages(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.mock_yb.repos.listEnabled.return_value = []
        pm = yum_product_id.YumProductManager(self.mock_yb)
        pm.get_enabled()

    def test_removed(self):
        # non rhel cert, not in active, with enabled repo
        self.mock_pdb.find_repos.return_value = ["repo1"]
        cert = self._create_non_rhel_cert()
        prod_dir = stubs.StubProductDirectory([])
        prod_dir.certs.append(cert)
        inj.provide(inj.PROD_DIR, prod_dir)

        pm = yum_product_id.YumProductManager(self.mock_yb)
        pm.update_removed([])
        self.assertTrue(cert.delete.called)

    def test_get_enabled_with_repos(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        repo_id = 'rhel-6-server'

        # mock the repo metadata read of the product cert
        mock_repo = mock.Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = mock.Mock(return_value='somefilename')
        mock_repo.id = repo_id

        pm = yum_product_id.YumProductManager(self.mock_yb)
        pm._get_cert = mock.Mock(return_value=cert)

        self.mock_yb.repos.listEnabled.return_value = [mock_repo]
        res = pm.get_enabled()
        self.assertEqual(res[0][0], cert)
        self.assertEqual(res[0][1], repo_id)

    @mock.patch('yum_product_id.log')
    def test_get_enabled_exception(self, mock_log):
        mock_repo = mock.Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = mock.Mock(return_value='somefilename')
        repo_id = 'rhel-6-server'
        mock_repo.id = repo_id

        pm = yum_product_id.YumProductManager(self.mock_yb)
        pm._get_cert = mock.Mock(side_effect=IOError)

        self.mock_yb.repos.listEnabled.return_value = [mock_repo]
        enabled = pm.get_enabled()

        self.assertTrue(mock_log.warning.called)
        self.assertEqual([], enabled)

    @mock.patch('yum_product_id.log')
    def test_get_enabled_metadata_error(self, mock_log):
        mock_repo = mock.Mock(spec=yum.repos.Repository)
        mock_repo.retrieveMD = mock.Mock(side_effect=yum.Errors.RepoMDError)
        repo_id = 'rhel-6-server'
        mock_repo.id = repo_id

        self.mock_yb.repos.listEnabled.return_value = [mock_repo]

        pm = yum_product_id.YumProductManager(self.mock_yb)
        pm.get_enabled()

        self.assertTrue(mock_repo.id in pm.meta_data_errors)
        self.assertFalse(mock_log.exception.called)

    def test_get_active_no_packages(self):
        cert = self._create_server_cert()

        prod_dir = stubs.StubProductDirectory([])
        prod_dir.certs.append(cert)
        inj.provide(inj.PROD_DIR, prod_dir)

        self.mock_yb.pkgSack.returnPackages.return_value = []
        pm = yum_product_id.YumProductManager(self.mock_yb)

        active = pm.get_active()
        self.assertEqual(set([]), active)

    def test_get_active_with_active_packages(self):
        mock_package = mock.Mock(spec=yum.rpmsack.RPMInstalledPackage)
        mock_package.repoid = 'this-is-not-a-rh-repo'
        mock_package.name = 'some-cool-package'
        mock_package.arch = 'noarch'

        self.mock_yb.pkgSack.returnPackages.return_value = [mock_package]

        pm = yum_product_id.YumProductManager(self.mock_yb)
        active = pm.get_active()
        self.assertEqual(set([mock_package.repoid]), active)

    def test_get_active_without_active_packages(self):
        mock_package = mock.Mock(spec=yum.rpmsack.RPMInstalledPackage)
        mock_package.repoid = 'this-is-not-a-rh-repo'
        mock_package.name = 'some-cool-package'
        mock_package.arch = 'noarch'

        self.mock_yb.pkgSack.returnPackages.return_value = [mock_package]

        # No packages in the enabled repo 'this-is-not-a-rh-repo' are installed.
        self.mock_yb.rpmdb.searchNevra.return_value = False

        pm = yum_product_id.YumProductManager(self.mock_yb)
        active = pm.get_active()
        self.assertEqual(set([]), active)

    def test_get_active_with_active_packages_rhel57_installed_repo(self):
        """rhel5.7 says every package is in 'installed' repo"""
        mock_package = mock.Mock(spec=yum.rpmsack.RPMInstalledPackage)
        mock_package.repoid = 'installed'
        mock_package.name = 'some-cool-package'
        mock_package.arch = 'noarch'

        self.mock_yb.pkgSack.returnPackages.return_value = [mock_package]

        pm = yum_product_id.YumProductManager(self.mock_yb)
        active = pm.get_active()
        self.assertEqual(set([]), active)

    def _create_cert(self, product_id, label, version, provided_tags):
        cert = stubs.StubProductCertificate(
                stubs.StubProduct(product_id, label, version=version,
                                   provided_tags=provided_tags))
        cert.delete = mock.Mock()
        cert.write = mock.Mock()
        return cert

    def _create_server_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6", "rhel-6,rhel-6-server")

    def _create_non_rhel_cert(self):
        return self._create_cert("1234568", "Mediocre OS",
                                 "6", "medios-6,medios-6-server")
