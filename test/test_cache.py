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

import os
import unittest
import random
import shutil
import socket
import tempfile
import threading
from mock import Mock

# used to get a user readable cfg class for test cases
from stubs import StubProduct, StubProductCertificate, StubCertificateDirectory, \
        StubEntitlementCertificate, StubPool, StubEntitlementDirectory
from fixture import SubManFixture

from rhsm import ourjson as json
from subscription_manager.cache import ProfileManager, \
        InstalledProductsManager, EntitlementStatusCache, \
        PoolTypeCache, ReleaseStatusCache, StatusCache

from rhsm.profile import Package, RPMProfile

from rhsm.connection import RestlibException, UnauthorizedException

from subscription_manager import injection as inj


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

    def test_update_check_packages_disabled(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        self.profile_mgr._set_report_package_profile(0)
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

    @staticmethod
    def _mock_pkg_profile(packages):
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


class TestStatusCache(unittest.TestCase):
    def test_register_and_remove_load_status_callback(self):
        def test_callback_one(a, b, c):
            pass

        def test_callback_two(a, b, c):
            pass

        result = StatusCache.remove_load_status_callback(test_callback_one)
        self.assertFalse(result)

        result = StatusCache.register_load_status_callback(test_callback_one)
        self.assertTrue(result)

        result = StatusCache.register_load_status_callback(test_callback_two)
        self.assertTrue(result)

        result = StatusCache.register_load_status_callback(test_callback_one)
        self.assertFalse(result)

        result = StatusCache.register_load_status_callback(test_callback_two)
        self.assertFalse(result)

        result = StatusCache.remove_load_status_callback(test_callback_one)
        self.assertTrue(result)

        result = StatusCache.remove_load_status_callback(test_callback_one)
        self.assertFalse(result)

        result = StatusCache.remove_load_status_callback(test_callback_two)
        self.assertTrue(result)

        result = StatusCache.remove_load_status_callback(test_callback_two)
        self.assertFalse(result)

    def test_execute_callbacks(self):
        call_count = [0, 0]

        def test_callback_one(a, b, c):
            self.assertEquals((a, b, c), ('a', 'b', 'c'))
            call_count[0] += 1

        def test_callback_two(a, b, c):
            self.assertEquals((a, b, c), ('a', 'b', 'c'))
            call_count[1] += 1

        StatusCache._notify_load_status_callbacks('a', 'b', 'c')
        self.assertEquals(call_count, [0, 0])

        StatusCache.register_load_status_callback(test_callback_one)

        StatusCache._notify_load_status_callbacks('a', 'b', 'c')
        self.assertEquals(call_count, [1, 0])

        StatusCache.register_load_status_callback(test_callback_two)

        StatusCache._notify_load_status_callbacks('a', 'b', 'c')
        self.assertEquals(call_count, [2, 1])

        StatusCache.remove_load_status_callback(test_callback_one)

        StatusCache._notify_load_status_callbacks('a', 'b', 'c')
        self.assertEquals(call_count, [2, 2])

        StatusCache.remove_load_status_callback(test_callback_two)

        StatusCache._notify_load_status_callbacks('a', 'b', 'c')
        self.assertEquals(call_count, [2, 2])


class TestInstalledProductsCache(SubManFixture):

    def setUp(self):
        super(TestInstalledProductsCache, self).setUp()
        self.prod_dir = StubCertificateDirectory([
            StubProductCertificate(StubProduct('a-product', name="Product A", provided_tags="product,product-a")),
            StubProductCertificate(StubProduct('b-product', name="Product B", provided_tags="product,product-b")),
            StubProductCertificate(StubProduct('c-product', name="Product C", provided_tags="product-c")),
        ])

        inj.provide(inj.PROD_DIR, self.prod_dir)
        self.mgr = InstalledProductsManager()

    def test_cert_parsing(self):
        self.assertEqual(3, len(self.mgr.installed.keys()))
        self.assertTrue('a-product' in self.mgr.installed)
        self.assertTrue('b-product' in self.mgr.installed)
        self.assertTrue('c-product' in self.mgr.installed)
        self.assertEquals("Product A", self.mgr.installed['a-product']['productName'])
        self.assertEquals(set(["product", "product-a", "product-b", "product-c"]), set(self.mgr.tags))

    def test_load_data(self):
        cached = {
                'products': {
                    'prod1': 'Product 1',
                    'prod2': 'Product 2'
                },
                'tags': ['p1', 'p2']
        }
        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(cached))

        data = self.mgr._load_data(mock_file)
        self.assertEquals(data, cached)

    def test_has_changed(self):
        cached = {
                'products': {
                   'prod1': 'Product 1',
                   'prod2': 'Product 2'
                },
                'tags': ['p1', 'p2']
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_has_changed_with_tags_only(self):
        cached = {
                'products': {
                    'a-product': {'productName': 'Product A', 'productId': 'a-product', 'version': '1.0', 'arch': 'x86_64'},
                    'b-product': {'productName': 'Product B', 'productId': 'b-product', 'version': '1.0', 'arch': 'x86_64'},
                    'c-product': {'productName': 'Product C', 'productId': 'c-product', 'version': '1.0', 'arch': 'x86_64'}
                },
                'tags': ['different']
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_old_format_seen_as_invalid(self):
        cached = {
                'a-product': {'productName': 'Product A', 'productId': 'a-product', 'version': '1.0', 'arch': 'x86_64'},
                'b-product': {'productName': 'Product B', 'productId': 'b-product', 'version': '1.0', 'arch': 'x86_64'},
                'c-product': {'productName': 'Product C', 'productId': 'c-product', 'version': '1.0', 'arch': 'x86_64'}
    }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_has_not_changed(self):
        cached = {
                'products': {
                    'a-product': {'productName': 'Product A', 'productId': 'a-product', 'version': '1.0', 'arch': 'x86_64'},
                    'b-product': {'productName': 'Product B', 'productId': 'b-product', 'version': '1.0', 'arch': 'x86_64'},
                    'c-product': {'productName': 'Product C', 'productId': 'c-product', 'version': '1.0', 'arch': 'x86_64'}
                },
                'tags': ['product-a', 'product-b', 'product-c', 'product']
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

        expected = ["product", "product-a", "product-b", "product-c"]
        uep.updateConsumer.assert_called_with(uuid,
                content_tags=set(expected),
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
        expected = ["product", "product-a", "product-b", "product-c"]
        uep.updateConsumer.assert_called_with(uuid,
                content_tags=set(expected),
                installed_products=self.mgr.format_for_server())
        self.assertEquals(0, self.mgr.write_cache.call_count)


class TestReleaseStatusCache(SubManFixture):
    def setUp(self):
        super(TestReleaseStatusCache, self).setUp()
        self.release_cache = ReleaseStatusCache()
        self.release_cache.write_cache = Mock()

    def test_load_from_server(self):
        uep = Mock()
        dummy_release = {'releaseVer': 'MockServer'}
        uep.getRelease = Mock(return_value=dummy_release)

        self.release_cache.read_status(uep, "THISISAUUID")

        self.assertEquals(dummy_release, self.release_cache.server_status)

    def test_server_no_release_call(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=RestlibException("boom"))

        status = self.release_cache.read_status(uep, "SOMEUUID")
        self.assertEquals(None, status)

    def test_server_network_error_no_cache(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=socket.error("boom"))
        self.release_cache._cache_exists = Mock(return_value=False)
        self.assertEquals(None, self.release_cache.read_status(uep, "SOMEUUID"))

    def test_server_network_error_with_cache(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=socket.error("boom"))
        dummy_release = {'releaseVer': 'MockServer'}
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        self.release_cache._cache_exists = Mock(return_value=True)

        status = self.release_cache.read_status(uep, "SOMEUUID")
        self.assertEquals(dummy_release, status)

    def test_server_network_works_with_cache(self):
        uep = Mock()
        dummy_release = {'releaseVer': 'MockServer'}
        uep.getRelease = Mock(return_value=dummy_release)

        self.release_cache._cache_exists = Mock(return_value=True)
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        self.assertEquals(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))
        self.assertEquals(1, self.release_cache.write_cache.call_count)
        self.assertEquals(0, self.release_cache._read_cache.call_count)

        self.assertEquals(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))
        self.assertEquals(1, uep.getRelease.call_count)

    def test_server_network_works_cache_caches(self):
        uep = Mock()
        dummy_release = {'releaseVer': 'MockServer'}
        uep.getRelease = Mock(return_value=dummy_release)

        self.release_cache._cache_exists = Mock(return_value=False)
        self.release_cache.server_status = None
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        self.assertEquals(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))
        self.assertEquals(1, self.release_cache.write_cache.call_count)
        self.assertEquals(0, self.release_cache._read_cache.call_count)

        self.release_cache._cache_exists = Mock(return_value=True)
        self.assertEquals(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))
        self.assertEquals(1, self.release_cache.write_cache.call_count)
        self.assertEquals(1, uep.getRelease.call_count)


class TestEntitlementStatusCache(SubManFixture):

    def setUp(self):
        super(TestEntitlementStatusCache, self).setUp()
        self.status_cache = EntitlementStatusCache()
        self.status_cache.write_cache = Mock()

    def test_load_from_server(self):
        uep = Mock()
        dummy_status = {"a": "1"}
        uep.getCompliance = Mock(return_value=dummy_status)

        self.status_cache.load_status(uep, "SOMEUUID")

        self.assertEquals(dummy_status, self.status_cache.server_status)
        self.assertEquals(1, self.status_cache.write_cache.call_count)

    def test_server_no_compliance_call(self):
        uep = Mock()
        uep.getCompliance = Mock(side_effect=RestlibException("boom"))
        status = self.status_cache.load_status(uep, "SOMEUUID")
        self.assertEquals(None, status)

    def test_server_network_error(self):
        dummy_status = {"a": "1"}
        uep = Mock()
        uep.getCompliance = Mock(side_effect=socket.error("boom"))
        self.status_cache._cache_exists = Mock(return_value=True)
        self.status_cache._read_cache = Mock(return_value=dummy_status)

        status = self.status_cache.load_status(uep, "SOMEUUID")
        self.assertEquals(dummy_status, status)
        self.assertEquals(1, self.status_cache._read_cache.call_count)

    # Extremely unlikely but just in case:
    def test_server_network_error_no_cache(self):
        uep = Mock()
        uep.getCompliance = Mock(side_effect=socket.error("boom"))
        self.status_cache._cache_exists = Mock(return_value=False)
        self.assertEquals(None, self.status_cache.load_status(uep, "SOMEUUID"))

    def test_write_cache(self):
        mock_server_status = {'fake server status': random.uniform(1, 2 ** 32)}
        status_cache = EntitlementStatusCache()
        status_cache.server_status = mock_server_status
        cache_dir = tempfile.mkdtemp()
        cache_file = os.path.join(cache_dir, 'status_cache.json')
        status_cache.CACHE_FILE = cache_file
        status_cache.write_cache()

        def threadActive(name):
            for thread in threading.enumerate():
                if thread.getName() == name:
                    return True
            return False

        # If the file exists, and the thread that writes it does not, we know writing has completed
        while not (os.path.exists(cache_file) and not threadActive("WriteCacheEntitlementStatusCache")):
            pass
        try:
            new_status_buf = open(cache_file).read()
            new_status = json.loads(new_status_buf)
            self.assertEquals(new_status, mock_server_status)
        finally:
            shutil.rmtree(cache_dir)

    def test_unauthorized_exception_handled(self):
        uep = Mock()
        uep.getCompliance = Mock(side_effect=UnauthorizedException(401, "GET"))
        self.assertEquals(None, self.status_cache.load_status(uep, "aaa"))


class TestPoolTypeCache(SubManFixture):

    def setUp(self):
        super(TestPoolTypeCache, self).setUp()
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.cp_provider.consumer_auth_cp = Mock()
        self.cp = self.cp_provider.consumer_auth_cp
        certs = [StubEntitlementCertificate(StubProduct('pid1'), pool=StubPool('someid'))]
        self.ent_dir = StubEntitlementDirectory(certificates=certs)

    def test_empty_cache(self):
        pooltype_cache = PoolTypeCache()
        result = pooltype_cache.get("some id")
        self.assertEquals('', result)

    def test_get_pooltype(self):
        self.cp.getEntitlementList.return_value = [self._build_ent_json('poolid', 'some type')]
        pooltype_cache = PoolTypeCache()
        pooltype_cache._do_update()
        result = pooltype_cache.get("poolid")
        self.assertEquals('some type', result)

    def test_requires_update(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir

        # Doesn't have data for pool with id 'someid'
        self.assertTrue(pooltype_cache.requires_update())

        pooltype_cache.pooltype_map['someid'] = 'some type'

        # After adding data for that entitlements pool, it shouldn't need an update
        self.assertFalse(pooltype_cache.requires_update())

    def test_update(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir
        self.cp.getEntitlementList.return_value = [
                self._build_ent_json('poolid', 'some type'),
                self._build_ent_json('poolid2', 'some other type')]

        # requires_update should be true, and should allow this method
        # to generate a correct mapping
        pooltype_cache.update()

        self.assertEquals(2, len(pooltype_cache.pooltype_map))
        self.assertEquals('some type', pooltype_cache.get('poolid'))
        self.assertEquals('some other type', pooltype_cache.get('poolid2'))

    # This is populated when available subs are refreshed
    def test_update_from_pools(self):
        # Input is a map of pool ids to pool json
        pools_map = {}

        for i in range(5):
            pool_id = 'poolid' + str(i)
            pools_map[pool_id] = self._build_pool_json(pool_id, 'some type')

        pooltype_cache = PoolTypeCache()
        pooltype_cache.update_from_pools(pools_map)

        self.assertEquals(5, len(pooltype_cache.pooltype_map))
        for i in range(5):
            expected_id = 'poolid' + str(i)
            self.assertEquals('some type', pooltype_cache.get(expected_id))

    def test_requires_update_ents_with_no_pool(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir
        for ent in self.ent_dir.certs:
            ent.pool = None

        # No ents have pools so there is nothing we can update
        self.assertFalse(pooltype_cache.requires_update())

    def _build_ent_json(self, pool_id, pool_type):
        result = {}
        result['id'] = "1234"
        result['pool'] = self._build_pool_json(pool_id, pool_type)
        return result

    def _build_pool_json(self, pool_id, pool_type):
        return {'id': pool_id, 'calculatedAttributes': {'compliance_type': pool_type}}
