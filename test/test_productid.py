import unittest
import yum

import stubs
from subscription_manager import productid
from mock import Mock, patch


class TestProductManager(unittest.TestCase):

    def setUp(self):
        self.prod_dir = stubs.StubProductDirectory([])
        self.prod_db_mock = Mock()
        self.prod_mgr = productid.ProductManager(product_dir=self.prod_dir,
                product_db=self.prod_db_mock)

    def test_removed(self):
        self.prod_db_mock.find_repo.return_value = "repo1"
        cert = self._create_desktop_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr.update_removed([])
        self.assertTrue(cert.delete.called)

    def test_update_no_packages_no_repos(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.pkgSack.returnPackages.return_value = []
        mock_yb.repos.listEnabled.return_value = []

        self.prod_mgr.update(mock_yb)
        # not a lot to test with no repos and no dbs
        # should be no product id db writing in this case
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repo.called)

    def test_get_enabled_no_packages(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.repos.listEnabled.return_value = []
        self.prod_mgr.get_enabled(mock_yb)

    def test_get_active_no_packages(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        mock_yb = Mock(spec=yum.YumBase)
        mock_yb.pkgSack.returnPackages.return_value = []
        active = self.prod_mgr.get_active(mock_yb)
        self.assertEquals(set([]), active)

    def test_update_installed_no_packages_no_repos_no_active_no_enabled_no_certs(self):
        self.prod_mgr.update_installed(set([]), set([]))
        # we should do nothing here
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repo.called)

        # plugin should get called with empty list
        self.prod_mgr.plugin_manager.run.assert_called_with('post_product_id_install', product_list=[])

    def test_update_installed_no_packages_no_repos_no_active_no_enabled(self):
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.update_installed(set([]), set([]))
        # we should do nothing here
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repo.called)

        self.prod_mgr.plugin_manager.run.assert_called_with('post_product_id_install', product_list=[])

    def test_update_installed_no_packages_no_repos_no_active_with_enabled(self):
        """if repos are enabled but not active, basically nothing should happen"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        enabled = [(cert, 'rhel-6-server')]

        self.prod_mgr.update_installed(enabled, set([]))

        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repo.called)

        self.prod_mgr.plugin_manager.run.assert_called_with('post_product_id_install', product_list=[])

    def test_update_installed_no_packages_no_repos_with_active_with_enabled(self):
        """rhel-6-server enabled and active, with product cert already installed should do nothing"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)
        enabled = [(cert, 'rhel-6-server')]
        active = set(['rhel-6-server'])

        # mock this so we can verify it's called correctly
        self.prod_dir.findByProduct = Mock(return_value=cert)
        self.prod_mgr._is_desktop = Mock(return_value=False)
        self.prod_mgr._is_workstation = Mock(return_value=False)

        # this is the normal case, with a product cert already installed,
        #  the repo enabled, and packages installed from it (active)
        self.prod_mgr.update_installed(enabled, active)
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.add.called)
        self.assertFalse(self.prod_db_mock.write.called)
        self.assertFalse(self.prod_db_mock.find_repo.called)
        self.assertTrue(self.prod_mgr._is_desktop.called)
        self.assertTrue(self.prod_mgr._is_workstation.called)

        self.prod_dir.findByProduct.assert_called_with('69')

    def test_update_removed_no_packages_no_repos_no_active_no_certs(self):
        self.prod_mgr.update_removed(set([]))
        self.assertFalse(self.prod_db_mock.delete.called)
        self.assertFalse(self.prod_db_mock.write.called)

    def test_update_removed_no_packages_no_repos_no_active(self):
        """we have a product cert, but it is not in active, so it
        should be deleted"""
        cert = self._create_server_cert()
        self.prod_dir.certs.append(cert)

        self.prod_mgr.pdir.refresh = Mock()

        self.prod_mgr.update_removed(set([]))
        self.assertTrue(self.prod_db_mock.delete.called)
        self.assertTrue(self.prod_db_mock.write.called)
        # we have 69.pem installed, but it is not active, we
        # should delete it from prod db
        self.prod_db_mock.delete.assert_called_with('69')
        self.assertTrue(cert.delete.called)

        self.assertTrue(self.prod_mgr.pdir.refresh.called)
        # TODO self.prod_mgr.pdir.refresh is called

# TODO: test if pdir handles things added to it while iterating over it
# TODO: test if product_id plugins are called on just product deletion
# TODO: test if we support duplicates in enabled repo list
# TODO: is there a reason available is a set and enabled is a list? if so, test those cases

    def _create_cert(self, id, label, version, provided_tags):
        cert = stubs.StubProductCertificate(
                stubs.StubProduct(id, label, version=version,
                                   provided_tags=provided_tags))
        cert.delete = Mock()
        cert.write = Mock()
        return cert

    def _create_desktop_cert(self):
        return self._create_cert("68", "Red Hat Enterprise Linux Desktop",
                                 "5", "rhel-5-client")

    def _create_workstation_cert(self):
        return self._create_cert("71", "Red Hat Enterprise Linux Workstation",
                                 "5", "rhel-5-client-workstation")

    def _create_server_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "6", "rhel-6-server")

    def test_is_workstation(self):
        workstation_cert = self._create_workstation_cert()
        self.assertTrue(self.prod_mgr._is_workstation(
            workstation_cert.products[0]))

    def test_is_desktop(self):
        desktop_cert = self._create_desktop_cert()
        self.assertTrue(self.prod_mgr._is_desktop(
            desktop_cert.products[0]))

    # If Desktop cert exists, delete it and then write Workstation:
    def test_workstation_overrides_desktop(self):

        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()

        def write_cert_side_effect(path):
            self.prod_dir.certs.append(desktop_cert)

        desktop_cert.write.side_effect = write_cert_side_effect
        workstation_cert.write.side_effect = write_cert_side_effect

        # Desktop comes first in this scenario:
        enabled = [
                (desktop_cert, 'repo1'),
                (workstation_cert, 'repo2'),
        ]

        self.prod_mgr.update_installed(enabled, ['repo1', 'repo2'])

        self.assertTrue(desktop_cert.write.called)
        self.assertTrue(desktop_cert.delete.called)

        self.assertTrue(workstation_cert.write.called)
        self.prod_db_mock.delete.assert_called_with("68")

    # If workstation cert exists, desktop write should be skipped:
    def test_workstation_skips_desktop(self):

        desktop_cert = self._create_desktop_cert()
        workstation_cert = self._create_workstation_cert()
        some_other_cert = stubs.StubProductCertificate(
            stubs.StubProduct("8127", "Some Other Product"))
        some_other_cert.delete = Mock()
        some_other_cert.write = Mock()

        def write_cert_side_effect(path):
            self.prod_dir.certs.append(workstation_cert)

        desktop_cert.write.side_effect = write_cert_side_effect
        workstation_cert.write.side_effect = write_cert_side_effect

        # Workstation comes first in this scenario:
        enabled = [
                (workstation_cert, 'repo2'),
                (desktop_cert, 'repo1'),
                (some_other_cert, 'repo3'),
        ]

        self.prod_mgr.update_installed(enabled, ['repo1', 'repo2', 'repo3'])

        self.assertTrue(workstation_cert.write.called)
        self.assertFalse(workstation_cert.delete.called)

        self.assertFalse(desktop_cert.write.called)
        self.assertFalse(desktop_cert.delete.called)

        # Testing a bug where desktop cert skipping ended the whole process:
        self.assertTrue(some_other_cert.write.called)
        self.assertFalse(some_other_cert.delete.called)

        self.assertFalse(self.prod_db_mock.delete.called)

    @patch("subscription_manager.productid.yum")
    def test_yum_version_tracks_repos(self, yum_mock):
        yum_mock.__version_info__ = (1, 2, 2)
        self.assertFalse(self.prod_mgr._check_yum_version_tracks_repos())

        yum_mock.__version_info__ = (3, 2, 35)
        self.assertTrue(self.prod_mgr._check_yum_version_tracks_repos())

        yum_mock.__version_info__ = (3, 2, 28)
        self.assertTrue(self.prod_mgr._check_yum_version_tracks_repos())
