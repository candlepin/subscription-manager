#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import unittest
from mock import Mock
import simplejson as json

# used to get a user readable cfg class for test cases
from stubs import *

from subscription_manager.cache import *
from rhsm.profile import *


class _FACT_MATCHER(object):
    def __eq__(self, other):
        return True


FACT_MATCHER = _FACT_MATCHER()


class TestProfileManager(unittest.TestCase):

    def setUp(self):
        current_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        self.current_profile = self._mock_pkg_profile(current_pkgs)
        self.profile_mgr = ProfileManager(current_profile=self.current_profile)

    def test_update_check_no_change(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updatePackageProfile = Mock()

        self.profile_mgr.has_changed = Mock(return_value=False)
        self.profile_mgr.write_cache = Mock()
        self.profile_mgr.update_check(uep, uuid)

        self.assertEquals(0, uep.updatePackageProfile.call_count)
        self.assertEquals(0, self.profile_mgr.write_cache.call_count)

    def test_update_check_has_changed(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updatePackageProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid)

        uep.updatePackageProfile.assert_called_with(uuid,
                FACT_MATCHER)
        self.assertEquals(1, self.profile_mgr.write_cache.call_count)

    def test_update_check_packages_not_supported(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.supports_resource = Mock(return_value=False)
        uep.updatePackageProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid)

        self.assertEquals(0, uep.updatePackageProfile.call_count)
        uep.supports_resource.assert_called_with('packages')
        self.assertEquals(0, self.profile_mgr.write_cache.call_count)

    def test_update_check_error_uploading(self):
        uuid = 'FAKEUUID'
        uep = Mock()

        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()
        # Throw an exception when trying to upload:
        uep.updatePackageProfile = Mock(side_effect=Exception('BOOM!'))

        self.assertRaises(Exception, self.profile_mgr.update_check, uep, uuid)
        uep.updatePackageProfile.assert_called_with(uuid,
                FACT_MATCHER)
        self.assertEquals(0, self.profile_mgr.write_cache.call_count)

    def test_has_changed_no_cache(self):
        self.profile_mgr._cache_exists = Mock(return_value=False)
        self.assertTrue(self.profile_mgr.has_changed())

    def test_has_changed_no_changes(self):
        cached_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        cached_profile = self._mock_pkg_profile(cached_pkgs)

        self.profile_mgr._cache_exists = Mock(return_value=True)
        self.profile_mgr._read_cache = Mock(return_value=cached_profile)

        self.assertFalse(self.profile_mgr.has_changed())
        self.profile_mgr._read_cache.assert_called_with()

    def test_has_changed(self):
        cached_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package3", version="3.0.0", release=3, arch="x86_64")]
        cached_profile = self._mock_pkg_profile(cached_pkgs)

        self.profile_mgr._cache_exists = Mock(return_value=True)
        self.profile_mgr._read_cache = Mock(return_value=cached_profile)

        self.assertTrue(self.profile_mgr.has_changed())
        self.profile_mgr._read_cache.assert_called_with()

    def _mock_pkg_profile(self, packages):
        """
        Turn a list of package objects into an RPMProfile object.
        """

        dict_list = []
        for pkg in packages:
            dict_list.append(pkg.to_dict())

        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(dict_list))

        mock_profile = RPMProfile(from_file=mock_file)
        return mock_profile


class TestInstalledProductsCache(unittest.TestCase):

    def setUp(self):
        self.prod_dir = StubCertificateDirectory([
            StubProductCertificate(StubProduct('a-product', name="Product A")),
            StubProductCertificate(StubProduct('b-product', name="Product B")),
            StubProductCertificate(StubProduct('c-product', name="Product C")),
        ])

        self.mgr = InstalledProductsManager(self.prod_dir)

    def test_cert_parsing(self):
        self.assertEqual(3, len(self.mgr.installed.keys()))
        self.assertTrue('a-product' in self.mgr.installed)
        self.assertTrue('b-product' in self.mgr.installed)
        self.assertTrue('c-product' in self.mgr.installed)
        self.assertEquals("Product A", self.mgr.installed['a-product'])

    def test_load_data(self):
        cached = {
                'prod1': 'Product 1',
                'prod2': 'Product 2'
        }
        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(cached))

        data = self.mgr._load_data(mock_file)
        self.assertEquals(data, cached)

    def test_has_changed(self):
        cached = {
                'prod1': 'Product 1',
                'prod2': 'Product 2'
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_has_not_changed(self):
        cached = {
                'a-product': 'Product A',
                'b-product': 'Product B',
                'c-product': 'Product C',
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertFalse(self.mgr.has_changed())

    def test_update_check_no_change(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updateConsumer = Mock()

        self.mgr.has_changed = Mock(return_value=False)
        self.mgr.write_cache = Mock()
        self.mgr.update_check(uep, uuid)

        self.assertEquals(0, uep.updateConsumer.call_count)
        self.assertEquals(0, self.mgr.write_cache.call_count)

    def test_update_check_has_changed(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updateConsumer = Mock()
        self.mgr.has_changed = Mock(return_value=True)
        self.mgr.write_cache = Mock()

        self.mgr.update_check(uep, uuid)

        uep.updateConsumer.assert_called_with(uuid,
                installed_products=self.mgr.format_for_server())
        self.assertEquals(1, self.mgr.write_cache.call_count)

    def test_update_check_error_uploading(self):
        uuid = 'FAKEUUID'
        uep = Mock()

        self.mgr.has_changed = Mock(return_value=True)
        self.mgr.write_cache = Mock()
        # Throw an exception when trying to upload:
        uep.updateConsumer = Mock(side_effect=Exception('BOOM!'))

        self.assertRaises(Exception, self.mgr.update_check, uep, uuid)
        uep.updateConsumer.assert_called_with(uuid,
                installed_products=self.mgr.format_for_server())
        self.assertEquals(0, self.mgr.write_cache.call_count)
