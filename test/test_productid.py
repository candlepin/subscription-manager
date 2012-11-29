import unittest

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
        self.firstcall = True

        def _my_retval(*args):
            if self.firstcall:
                self.firstcall = False
                return ["repo1"]
            return []

        self.prod_db_mock.findRepos.side_effect = _my_retval
        cert = self._create_desktop_cert()
        self.prod_dir.certs.append(cert)
        self.prod_mgr.updateRemoved([])
        self.assertTrue(cert.delete.called)

    def _create_desktop_cert(self):
        cert = stubs.StubProductCertificate(
            stubs.StubProduct("68", "Red Hat Enterprise Linux Desktop",
                version="5", provided_tags="rhel-5-client"))
        cert.delete = Mock()
        cert.write = Mock()
        return cert

    def _create_workstation_cert(self):
        cert = stubs.StubProductCertificate(
            stubs.StubProduct("71", "Red Hat Enterprise Linux Workstation",
                version="5", provided_tags="rhel-5-client-workstation"))
        cert.delete = Mock()
        cert.write = Mock()
        return cert

    def test_is_workstation(self):
        workstation_cert = self._create_workstation_cert()
        self.assertTrue(self.prod_mgr._isWorkstation(
            workstation_cert.products[0]))

    def test_is_desktop(self):
        desktop_cert = self._create_desktop_cert()
        self.assertTrue(self.prod_mgr._isDesktop(
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

        self.prod_mgr.updateInstalled(enabled, ['repo1', 'repo2'])

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

        self.prod_mgr.updateInstalled(enabled, ['repo1', 'repo2', 'repo3'])

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

    @patch("simplejson.load")
    def test_convert_on_open(self, load_mock):
        json_data = {}
        json_data["10"] = "foo"
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        self.assertEquals(type(prod_db.findRepos("10")), list)

    @patch("simplejson.load")
    def test_add_to_existing(self, load_mock):
        json_data = {}
        json_data["10"] = "foo"
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        prod_db.add("10", "bar")
        self.assertEquals(len(prod_db.findRepos("10")), 2)

    @patch("simplejson.load")
    def test_add_to_new(self, load_mock):
        json_data = {}
        json_data["10"] = "foo"
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        prod_db.add("11", "bar")
        self.assertEquals(len(prod_db.findRepos("11")), 1)

    @patch("simplejson.load")
    def test_remove_entry(self, load_mock):
        json_data = {}
        json_data["10"] = "foo"
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        prod_db.delete("10", "bar")
        self.assertEquals(prod_db.findRepos("10"), None)

    @patch("simplejson.load")
    def test_remove_single(self, load_mock):
        json_data = {}
        json_data["10"] = ["foo", "bar"]
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        prod_db.delete("10", "bar")
        self.assertEquals(prod_db.findRepos("10"), ["foo"])

    @patch("simplejson.load")
    def test_remove_all(self, load_mock):
        json_data = {}
        json_data["10"] = "foo"
        load_mock.return_value = json_data
        prod_db = productid.ProductDatabase()
        prod_db.read()
        prod_db.delete("10")
        self.assertEquals(prod_db.findRepos("10"), None)
