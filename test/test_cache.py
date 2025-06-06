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
import base64
import unittest

import datetime
import os
import logging
import shutil
import socket
import tempfile
import time
from unittest.mock import Mock, patch, mock_open
from typing import Dict

# used to get a user readable cfg class for test cases
from .stubs import (
    StubProduct,
    StubProductCertificate,
    StubCertificateDirectory,
    StubEntitlementCertificate,
    StubPool,
    StubEntitlementDirectory,
    StubUEP,
)
from .fixture import SubManFixture

from rhsm import ourjson as json
from subscription_manager.cache import (
    ProfileManager,
    InstalledProductsManager,
    PoolTypeCache,
    ReleaseStatusCache,
    ContentAccessCache,
    PoolStatusCache,
    SupportedResourcesCache,
    AvailableEntitlementsCache,
    CurrentOwnerCache,
    SyspurposeComplianceStatusCache,
)

from rhsm.profile import Package, RPMProfile, EnabledReposProfile, ModulesProfile

from rhsm.connection import (
    UEPConnection,
    RestlibException,
    RateLimitExceededException,
    ProxyException,
)

from subscription_manager import injection as inj

from subscription_manager import isodate, cache

from test import subman_marker_slow, subman_marker_slow_timeout

log = logging.getLogger(__name__)


class _FACT_MATCHER:
    def __eq__(self, other):
        return True


FACT_MATCHER = _FACT_MATCHER()

CONTENT_REPO_FILE = """
[awesome-os-for-x86_64-upstream-rpms]
name = Awesome OS for x86_64 - Upstream (RPMs)
baseurl = https://cdn.awesome.com/content/dist/awesome/$releasever/x86_64/upstream/os
enabled = 1
gpgcheck = 1
gpgkey = file:///etc/pki/rpm-gpg/RPM-GPG-KEY-awesome-release
sslverify = 1
sslcacert = /etc/rhsm/ca/awesome-uep.pem
sslclientkey = /etc/pki/entitlement/0123456789012345678-key.pem
sslclientcert = /etc/pki/entitlement/0123456789012345678.pem
metadata_expire = 86400
ui_repoid_vars = releasever

[awesome-os-for-x86_64-debug-rpms]
name = Awesome OS for x86_64 - Debug (RPMs)
baseurl = https://cdn.awesome.com/content/dist/awesome/$releasever/x86_64/upstream/debug
enabled = 0
gpgcheck = 1
gpgkey = file:///etc/pki/rpm-gpg/RPM-GPG-KEY-awesome-release
sslverify = 1
sslcacert = /etc/rhsm/ca/awesome-uep.pem
sslclientkey = /etc/pki/entitlement/0123456789012345678-key.pem
sslclientcert = /etc/pki/entitlement/0123456789012345678.pem
metadata_expire = 86400
ui_repoid_vars = releasever
"""

ENABLED_MODULES = [
    {
        "name": "duck",
        "stream": 0,
        "version": "20180730233102",
        "context": "deadbeef",
        "arch": "noarch",
        "profiles": ["default"],
        "installed_profiles": [],
        "status": "enabled",
        "active": True,
    },
    {
        "name": "flipper",
        "stream": 0.69,
        "version": "20180707144203",
        "context": "c0ffee42",
        "arch": "x86_64",
        "profiles": ["default", "server"],
        "installed_profiles": ["server"],
        "status": "unknown",
        "active": True,
    },
]


class TestCurrentOwnerCache(unittest.TestCase):
    """
    Test case for class CurrentOwnerCache
    """

    CACHE_FILE_CONTENT = {
        "e068d900-ee2a-4d16-a8b7-709a8f1e8b79": {
            "created": "2020-11-24T09:44:43+0000",
            "updated": "2020-11-24T09:44:43+0000",
            "id": "ff80808175f9a3e90175f9a41dff0004",
            "key": "admin",
            "displayName": "Admin Owner",
            "parentOwner": None,
            "contentPrefix": None,
            "defaultServiceLevel": None,
            "upstreamConsumer": None,
            "logLevel": None,
            "autobindDisabled": False,
            "autobindHypervisorDisabled": False,
            "contentAccessMode": "entitlement",
            "contentAccessModeList": "entitlement",
            "lastRefreshed": None,
            "href": "/owners/admin",
        }
    }

    def setUp(self):
        self.uep = StubUEP()
        self.current_owner_cache = CurrentOwnerCache()
        self.identity = Mock()
        self.identity.uuid = "e068d900-ee2a-4d16-a8b7-709a8f1e8b79"

    def test_cache_status_unknown(self):
        """
        Test that cache is not used, when validity of consumer cert/key is unknown
        """
        self.uep.conn.is_consumer_cert_key_valid = None
        self.uep.getOwner = Mock(return_value={"key": "dummy_owner"})
        self.assertEqual(self.uep.getOwner.call_count, 0)
        self.current_owner_cache.write_cache = Mock()
        owner = self.current_owner_cache.read_data(uep=self.uep, identity=self.identity)
        self.uep.getOwner.assert_called_once()
        self.assertEqual(owner, {"key": "dummy_owner"})

    def test_cache_status_not_valid(self):
        """
        Test that cache is not used, when validity of consumer cert/key is false
        """
        self.uep.conn.is_consumer_cert_key_valid = False
        self.uep.getOwner = Mock(return_value={"key": "another_owner"})
        self.current_owner_cache.write_cache = Mock()
        self.assertEqual(self.uep.getOwner.call_count, 0)
        owner = self.current_owner_cache.read_data(uep=self.uep, identity=self.identity)
        self.uep.getOwner.assert_called_once()
        self.assertEqual(owner, {"key": "another_owner"})

    def test_cache_status_valid(self):
        """
        Test that owner information is read from cache, when validity of consumer cert/key is unknown
        """
        # Mock that consumer cert/key was used for communication with candlepin server
        # with successful result
        self.uep.conn.is_consumer_cert_key_valid = True
        self.uep.getOwner = Mock(return_value={"key": "dummy_owner"})
        self.current_owner_cache.read_cache_only = Mock(return_value=self.CACHE_FILE_CONTENT)
        self.current_owner_cache.write_cache = Mock()
        owner = self.current_owner_cache.read_data(uep=self.uep, identity=self.identity)
        self.assertEqual(self.uep.getOwner.call_count, 0)
        self.assertTrue(self.identity.uuid in self.CACHE_FILE_CONTENT)
        self.assertEqual(owner, self.CACHE_FILE_CONTENT[self.identity.uuid])

    def test_cache_obsoleted(self):
        """
        Test that owner information is read from server, when uuid of consumer is different from cache file
        """
        self.uep.conn.is_consumer_cert_key_valid = True
        # Mock that uuid of consumer has changed
        self.identity.uuid = "e068d900-f000-f000-f000-709a8f1e8b79"
        self.uep.getOwner = Mock(return_value={"key": "foo_owner"})
        self.current_owner_cache.read_cache_only = Mock(return_value=self.CACHE_FILE_CONTENT)
        self.current_owner_cache.write_cache = Mock()
        owner = self.current_owner_cache.read_data(uep=self.uep, identity=self.identity)
        self.uep.getOwner.assert_called_once()
        self.assertEqual(owner, {"key": "foo_owner"})


class TestProfileManager(SubManFixture):
    def setUp(self):
        super().setUp()

        current_pkgs = [
            Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
            Package(name="package2", version="2.0.0", release=2, arch="x86_64"),
        ]
        temp_repo_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_repo_dir)
        repo_file_name = os.path.join(temp_repo_dir, "awesome.repo")
        with open(repo_file_name, "w") as repo_file:
            repo_file.write(CONTENT_REPO_FILE)

        patcher = patch("rhsm.profile.dnf")
        self.addCleanup(patcher.stop)
        dnf_mock = patcher.start()
        dnf_mock.dnf = Mock()
        mock_db = Mock()
        mock_db.conf = Mock()
        mock_db.conf.substitutions = {"releasever": "1", "basearch": "x86_64"}
        dnf_mock.dnf.Base = Mock(return_value=mock_db)

        provider_patcher = patch("rhsm.profile.provider")
        provider_mock = provider_patcher.start()
        provider_mock.get_cloud_provider = Mock(return_value=None)
        self.addCleanup(provider_patcher.stop)

        self.current_profile = self._mock_pkg_profile(current_pkgs, repo_file_name, ENABLED_MODULES)
        self.profile_mgr = ProfileManager()
        self.profile_mgr.current_profile = self.current_profile

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_no_change(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.updatePackageProfile = Mock()

        self.profile_mgr.has_changed = Mock(return_value=False)
        self.profile_mgr.write_cache = Mock()
        self.profile_mgr.update_check(uep, uuid)

        self.assertEqual(0, uep.updatePackageProfile.call_count)
        self.assertEqual(0, self.profile_mgr.write_cache.call_count)

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_has_changed(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.has_capability = Mock(return_value=False)
        uep.updatePackageProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid, True)

        uep.updatePackageProfile.assert_called_with(uuid, FACT_MATCHER)
        self.assertEqual(1, self.profile_mgr.write_cache.call_count)

    @patch("subscription_manager.cache.get_supported_resources")
    def test_combined_profile_update_check_has_changed(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.has_capability = Mock(return_value=True)
        uep.updateCombinedProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid, True)

        uep.updateCombinedProfile.assert_called_with(uuid, FACT_MATCHER)
        self.assertEqual(1, self.profile_mgr.write_cache.call_count)

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_packages_not_supported(self, mock_get_supported_resources):
        # support anything else but not 'packages'
        mock_get_supported_resources.return_value = ["foo", "bar"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.updatePackageProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid)

        self.assertEqual(0, uep.updatePackageProfile.call_count)
        mock_get_supported_resources.assert_called_once()
        self.assertEqual(0, self.profile_mgr.write_cache.call_count)

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_packages_disabled(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        self.profile_mgr.report_package_profile = 0
        uep.updatePackageProfile = Mock()
        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        self.profile_mgr.update_check(uep, uuid)

        self.assertEqual(0, uep.updatePackageProfile.call_count)
        mock_get_supported_resources.assert_called_once()
        self.assertEqual(0, self.profile_mgr.write_cache.call_count)

    def test_report_package_profile_environment_variable(self):
        with patch.dict("os.environ", {"SUBMAN_DISABLE_PROFILE_REPORTING": "1"}), patch.object(
            cache, "conf"
        ) as conf:
            # report_package_profile is set to 1 and SUBMAN_DISABLE_PROFILE_REPORTING is set to 1, the
            # package profile should not be reported.
            conf.__getitem__.return_value.get_int.return_value = 1
            self.assertFalse(self.profile_mgr.profile_reporting_enabled())
            # report_package_profile in rhsm.conf is set to 0 and SUBMAN_DISABLE_PROFILE_REPORTING is set
            # to 1, the package profile should not be reported.
            conf.__getitem__.return_value.get_int.return_value = 0
            self.assertFalse(self.profile_mgr.profile_reporting_enabled())

        with patch.dict("os.environ", {"SUBMAN_DISABLE_PROFILE_REPORTING": "0"}), patch.object(
            cache, "conf"
        ) as conf:
            # report_package_profile in rhsm.conf is set to 1 and SUBMAN_DISABLE_PROFILE_REPORTING is set
            # to 0, the package profile should be reported.
            conf.__getitem__.return_value.get_int.return_value = 1
            self.assertTrue(self.profile_mgr.profile_reporting_enabled())
            # report_package_profile in rhsm.conf is set to 0 and SUBMAN_DISABLE_PROFILE_REPORTING is set
            # to 0, the package profile should not be reported.
            conf.__getitem__.return_value.get_int.return_value = 0
            self.assertFalse(self.profile_mgr.profile_reporting_enabled())

        with patch.dict("os.environ", {}), patch.object(cache, "conf") as conf:
            # report_package_profile in rhsm.conf is set to 1 and SUBMAN_DISABLE_PROFILE_REPORTING is not
            # set, the package profile should be reported.
            conf.__getitem__.return_value.get_int.return_value = 1
            self.assertTrue(self.profile_mgr.profile_reporting_enabled())
            # report_package_profile in rhsm.conf is set to 0 and SUBMAN_DISABLE_PROFILE_REPORTING is not
            # set, the package profile should not be reported.
            conf.__getitem__.return_value.get_int.return_value = 0
            self.assertFalse(self.profile_mgr.profile_reporting_enabled())

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_error_uploading(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.has_capability = Mock(return_value=False)

        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()
        # Throw an exception when trying to upload:
        uep.updatePackageProfile = Mock(side_effect=Exception("BOOM!"))

        self.assertRaises(Exception, self.profile_mgr.update_check, uep, uuid, True)
        uep.updatePackageProfile.assert_called_with(uuid, FACT_MATCHER)
        self.assertEqual(0, self.profile_mgr.write_cache.call_count)

    @patch("subscription_manager.cache.get_supported_resources")
    def test_combined_profile_update_check_error_uploading(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = "FAKEUUID"
        uep = Mock()
        uep.has_capability = Mock(return_value=True)

        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()
        # Throw an exception when trying to upload:
        uep.updateCombinedProfile = Mock(side_effect=Exception("BOOM!"))

        self.assertRaises(Exception, self.profile_mgr.update_check, uep, uuid, True)
        uep.updateCombinedProfile.assert_called_with(uuid, FACT_MATCHER)
        self.assertEqual(0, self.profile_mgr.write_cache.call_count)

    def test_has_changed_no_cache(self):
        self.profile_mgr._cache_exists = Mock(return_value=False)
        self.assertTrue(self.profile_mgr.has_changed())

    def test_has_changed_no_changes(self):
        cached_pkgs = [
            Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
            Package(name="package2", version="2.0.0", release=2, arch="x86_64"),
        ]
        temp_repo_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_repo_dir)
        repo_file_name = os.path.join(temp_repo_dir, "awesome.repo")
        with open(repo_file_name, "w") as repo_file:
            repo_file.write(CONTENT_REPO_FILE)
        cached_profile = self._mock_pkg_profile(cached_pkgs, repo_file_name, ENABLED_MODULES)

        self.profile_mgr._cache_exists = Mock(return_value=True)
        self.profile_mgr._read_cache = Mock(return_value=cached_profile)

        self.assertFalse(self.profile_mgr.has_changed())
        self.profile_mgr._read_cache.assert_called_with()

    def test_has_changed(self):
        cached_pkgs = [
            Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
            Package(name="package3", version="3.0.0", release=3, arch="x86_64"),
        ]
        cached_profile = self._mock_pkg_profile(cached_pkgs, "/non/existing/path/to/repo/file", [])

        self.profile_mgr._cache_exists = Mock(return_value=True)
        self.profile_mgr._read_cache = Mock(return_value=cached_profile)

        self.assertTrue(self.profile_mgr.has_changed())
        self.profile_mgr._read_cache.assert_called_with()

    @patch("subscription_manager.cache.get_supported_resources")
    def test_update_check_consumer_uuid_none(self, mock_get_supported_resources):
        mock_get_supported_resources.return_value = ["packages"]
        uuid = None
        uep = Mock()

        self.profile_mgr.has_changed = Mock(return_value=True)
        self.profile_mgr.write_cache = Mock()

        res = self.profile_mgr.update_check(uep, uuid)
        self.assertEqual(0, res)

    def test_package_json_handles_non_unicode(self):
        package = Package(name=b"\xf6", version=b"\xf6", release=b"\xf6", arch=b"\xf6", vendor=b"\xf6")
        data = package.to_dict()
        json_str = json.dumps(data)  # to json
        data = json.loads(json_str)  # and back to an object
        for attr in ["name", "version", "release", "arch", "vendor"]:
            self.assertEqual("\ufffd", data[attr])

    def test_package_json_as_unicode_type(self):
        package = Package(name="Björk", version="Björk", release="Björk", arch="Björk", vendor="Björk")
        data = package.to_dict()
        json_str = json.dumps(data)  # to json
        data = json.loads(json_str)  # and back to an object
        for attr in ["name", "version", "release", "arch", "vendor"]:
            self.assertEqual("Björk", data[attr])

    def test_package_json_missing_attributes(self):
        package = Package(name=None, version=None, release=None, arch=None, vendor=None)
        data = package.to_dict()
        json_str = json.dumps(data)  # to json
        data = json.loads(json_str)  # and back to an object
        for attr in ["name", "version", "release", "arch", "vendor"]:
            self.assertEqual(None, data[attr])

    def test_module_md_uniquify(self):
        modules_input = [
            {
                "name": "duck",
                "stream": 0,
                "version": "20180730233102",
                "context": "deadbeef",
                "arch": "noarch",
                "profiles": ["default"],
                "installed_profiles": [],
                "status": "enabled",
                "active": True,
            },
            {
                "name": "duck",
                "stream": 0,
                "version": "20180707144203",
                "context": "c0ffee42",
                "arch": "noarch",
                "profiles": ["default", "server"],
                "installed_profiles": ["server"],
                "status": "unknown",
                "active": True,
            },
        ]

        self.assertEqual(modules_input, ModulesProfile._uniquify(modules_input))
        # now test dup modules
        self.assertEqual(modules_input, ModulesProfile._uniquify(modules_input + [modules_input[0]]))

    def test_module_md_uniquify_active_and_inactive(self):
        modules_input = [
            {
                "name": "duck",
                "stream": 0,
                "version": "20180730233102",
                "context": "deadbeef",
                "arch": "noarch",
                "profiles": ["default"],
                "installed_profiles": [],
                "status": "enabled",
                "active": False,
            },
            {
                "name": "duck",
                "stream": 0,
                "version": "20180730233102",
                "context": "deadbeef",
                "arch": "noarch",
                "profiles": ["default"],
                "installed_profiles": [],
                "status": "enabled",
                "active": True,
            },
        ]

        expected_output = [
            {
                "name": "duck",
                "stream": 0,
                "version": "20180730233102",
                "context": "deadbeef",
                "arch": "noarch",
                "profiles": ["default"],
                "installed_profiles": [],
                "status": "enabled",
                "active": True,
            }
        ]

        self.assertEqual(expected_output, ModulesProfile._uniquify(modules_input))

    @staticmethod
    def _mock_pkg_profile(packages, repo_file, enabled_modules):
        """
        Turn a list of package objects into an RPMProfile object.
        """

        dict_list = []
        for pkg in packages:
            dict_list.append(pkg.to_dict())

        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(dict_list))

        mock_rpm_profile = RPMProfile(from_file=mock_file)

        mock_enabled_repos_profile = EnabledReposProfile(repo_file=repo_file)

        mock_module_profile = ModulesProfile()
        mock_module_profile.collect = Mock(return_value=enabled_modules)

        mock_profile = {
            "rpm": mock_rpm_profile,
            "enabled_repos": mock_enabled_repos_profile,
            "modulemd": mock_module_profile,
        }
        return mock_profile


class TestInstalledProductsCache(SubManFixture):
    def setUp(self):
        super(TestInstalledProductsCache, self).setUp()
        self.prod_dir = StubCertificateDirectory(
            [
                StubProductCertificate(
                    StubProduct("a-product", name="Product A", provided_tags="product,product-a")
                ),
                StubProductCertificate(
                    StubProduct("b-product", name="Product B", provided_tags="product,product-b")
                ),
                StubProductCertificate(StubProduct("c-product", name="Product C", provided_tags="product-c")),
            ]
        )

        inj.provide(inj.PROD_DIR, self.prod_dir)
        self.mgr = InstalledProductsManager()

    def test_cert_parsing(self):
        self.assertEqual(3, len(list(self.mgr.installed.keys())))
        self.assertTrue("a-product" in self.mgr.installed)
        self.assertTrue("b-product" in self.mgr.installed)
        self.assertTrue("c-product" in self.mgr.installed)
        self.assertEqual("Product A", self.mgr.installed["a-product"]["productName"])
        self.assertEqual(set(["product", "product-a", "product-b", "product-c"]), set(self.mgr.tags))

    def test_load_data(self):
        cached = {"products": {"prod1": "Product 1", "prod2": "Product 2"}, "tags": ["p1", "p2"]}
        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(cached))

        data = self.mgr._load_data(mock_file)
        self.assertEqual(data, cached)

    def test_has_changed(self):
        cached = {"products": {"prod1": "Product 1", "prod2": "Product 2"}, "tags": ["p1", "p2"]}

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_has_changed_with_tags_only(self):
        cached = {
            "products": {
                "a-product": {
                    "productName": "Product A",
                    "productId": "a-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
                "b-product": {
                    "productName": "Product B",
                    "productId": "b-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
                "c-product": {
                    "productName": "Product C",
                    "productId": "c-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
            },
            "tags": ["different"],
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_old_format_seen_as_invalid(self):
        cached = {
            "a-product": {
                "productName": "Product A",
                "productId": "a-product",
                "version": "1.0",
                "arch": "x86_64",
            },
            "b-product": {
                "productName": "Product B",
                "productId": "b-product",
                "version": "1.0",
                "arch": "x86_64",
            },
            "c-product": {
                "productName": "Product C",
                "productId": "c-product",
                "version": "1.0",
                "arch": "x86_64",
            },
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertTrue(self.mgr.has_changed())

    def test_has_not_changed(self):
        cached = {
            "products": {
                "a-product": {
                    "productName": "Product A",
                    "productId": "a-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
                "b-product": {
                    "productName": "Product B",
                    "productId": "b-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
                "c-product": {
                    "productName": "Product C",
                    "productId": "c-product",
                    "version": "1.0",
                    "arch": "x86_64",
                },
            },
            "tags": ["product-a", "product-b", "product-c", "product"],
        }

        self.mgr._read_cache = Mock(return_value=cached)
        self.mgr._cache_exists = Mock(return_value=True)

        self.assertFalse(self.mgr.has_changed())

    def test_update_check_no_change(self):
        uuid = "FAKEUUID"
        uep = Mock()
        uep.updateConsumer = Mock()

        self.mgr.has_changed = Mock(return_value=False)
        self.mgr.write_cache = Mock()
        self.mgr.update_check(uep, uuid)

        self.assertEqual(0, uep.updateConsumer.call_count)
        self.assertEqual(0, self.mgr.write_cache.call_count)

    def test_update_check_has_changed(self):
        uuid = "FAKEUUID"
        uep = Mock()
        uep.updateConsumer = Mock()
        self.mgr.has_changed = Mock(return_value=True)
        self.mgr.write_cache = Mock()

        self.mgr.update_check(uep, uuid, True)

        expected = ["product", "product-a", "product-b", "product-c"]
        uep.updateConsumer.assert_called_with(
            uuid, content_tags=set(expected), installed_products=self.mgr.format_for_server()
        )
        self.assertEqual(1, self.mgr.write_cache.call_count)

    def test_update_check_error_uploading(self):
        uuid = "FAKEUUID"
        uep = Mock()

        self.mgr.has_changed = Mock(return_value=True)
        self.mgr.write_cache = Mock()
        # Throw an exception when trying to upload:
        uep.updateConsumer = Mock(side_effect=Exception("BOOM!"))

        self.assertRaises(Exception, self.mgr.update_check, uep, uuid, True)
        expected = ["product", "product-a", "product-b", "product-c"]
        uep.updateConsumer.assert_called_with(
            uuid, content_tags=set(expected), installed_products=self.mgr.format_for_server()
        )
        self.assertEqual(0, self.mgr.write_cache.call_count)


class TestReleaseStatusCache(SubManFixture):
    def setUp(self):
        super(TestReleaseStatusCache, self).setUp()
        self.release_cache = ReleaseStatusCache()
        self.release_cache.write_cache = Mock()

    def test_load_from_server(self):
        uep = Mock()
        dummy_release = {"releaseVer": "MockServer"}
        uep.getRelease = Mock(return_value=dummy_release)

        self.release_cache.read_status(uep, "THISISAUUID")

        self.assertEqual(dummy_release, self.release_cache.server_status)

    def test_server_no_release_call(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=RestlibException("boom"))

        status = self.release_cache.read_status(uep, "SOMEUUID")
        self.assertEqual(None, status)

    def test_server_network_error_no_cache(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=socket.error("boom"))
        self.release_cache._cache_exists = Mock(return_value=False)
        self.assertEqual(None, self.release_cache.read_status(uep, "SOMEUUID"))

    def test_server_network_error_with_cache(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=socket.error("boom"))
        dummy_release = {"releaseVer": "MockServer"}
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        self.release_cache._cache_exists = Mock(return_value=True)
        self.assertEqual(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))

    def test_rate_limit_exceed_with_cache(self):
        uep = Mock()
        uep.getRelease = Mock(side_effect=RateLimitExceededException(429))
        dummy_release = {"releaseVer": "MockServer"}
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        self.release_cache._cache_exists = Mock(return_value=True)
        self.assertEqual(dummy_release, self.release_cache.read_status(uep, "SOMEUUID"))

    def test_server_not_needed_with_cache(self):
        uep = Mock()
        dummy_release = {"releaseVer": "MockServer"}
        uep.getRelease = Mock(return_value=dummy_release)

        self.release_cache._cache_exists = Mock(return_value=True)
        self.release_cache._read_cache = Mock(return_value=dummy_release)
        release = self.release_cache.read_status(uep, "SOMEUUID")
        self.assertEqual(dummy_release, release)
        self.assertEqual(1, self.release_cache._read_cache.call_count)
        self.assertEqual(0, uep.getRelease.call_count)

    def test_server_network_works_cache_caches(self):
        uep = Mock()
        dummy_release = {"releaseVer": "MockServer"}
        uep.getRelease = Mock(return_value=dummy_release)
        self.release_cache.write_cache = Mock()

        # Mock that cache does not exist
        self.release_cache._cache_exists = Mock(return_value=False)
        self.release_cache.server_status = None
        self.release_cache._read_cache = Mock(return_value=None)

        # Try to read status
        release = self.release_cache.read_status(uep, "SOMEUUID")

        # Assert that status was read from server and result was written
        # to cache file
        self.assertEqual(dummy_release, release)
        self.assertEqual(1, uep.getRelease.call_count)
        self.assertEqual(1, self.release_cache.write_cache.call_count)
        self.assertEqual(1, self.release_cache._read_cache.call_count)

        # Mock that cache file exists now
        self.release_cache._cache_exists = Mock(return_value=True)
        self.release_cache._read_cache = Mock(return_value=dummy_release)

        # Try to get release once again
        release = self.release_cache.read_status(uep, "SOMEUUID")

        # Assert that release was read from cache and not from server
        self.assertEqual(dummy_release, release)
        self.assertEqual(1, self.release_cache.write_cache.call_count)
        self.assertEqual(1, uep.getRelease.call_count)


class TestPoolStatusCache(SubManFixture):
    """
    Class for testing PoolStatusCache
    """

    def setUp(self):
        super(TestPoolStatusCache, self).setUp()
        self.pool_status_cache = PoolStatusCache()
        self.pool_status_cache.write_cache = Mock()

    def test_load_data(self):
        cached = {"pools": {"pool1": "Pool 1", "pool2": "Pool 2"}, "tags": ["p1", "p2"]}
        mock_file = Mock()
        mock_file.read = Mock(return_value=json.dumps(cached))

        data = self.pool_status_cache._load_data(mock_file)
        self.assertEqual(data, cached)

    def test_load_from_server(self):
        uep = Mock()
        dummy_pools = {"pools": {"pool1": "Pool 1", "pool2": "Pool 2"}, "tags": ["p1", "p2"]}
        uep.getEntitlementList = Mock(return_value=dummy_pools)

        self.pool_status_cache.read_status(uep, "THISISAUUID")

        self.assertEqual(dummy_pools, self.pool_status_cache.server_status)


class TestPoolTypeCache(SubManFixture):
    """
    Class for testing PoolTypeCache
    """

    def setUp(self):
        super(TestPoolTypeCache, self).setUp()
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.cp_provider.consumer_auth_cp = Mock()
        self.cp = self.cp_provider.consumer_auth_cp
        certs = [StubEntitlementCertificate(StubProduct("pid1"), pool=StubPool("someid"))]
        self.ent_dir = StubEntitlementDirectory(certificates=certs)
        self.pool_cache = inj.require(inj.POOL_STATUS_CACHE)
        self.pool_cache.write_cache = Mock()

    def test_empty_cache(self):
        pooltype_cache = PoolTypeCache()
        result = pooltype_cache.get("some id")
        self.assertEqual("", result)

    def test_get_pooltype(self):
        self.cp.getEntitlementList.return_value = [self._build_ent_json("poolid", "some type")]
        pooltype_cache = PoolTypeCache()
        pooltype_cache._do_update()
        result = pooltype_cache.get("poolid")
        self.assertEqual("some type", result)

    def test_requires_update(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir

        # Doesn't have data for pool with id 'someid'
        self.assertTrue(pooltype_cache.requires_update())

        pooltype_cache.pooltype_map["someid"] = "some type"

        # After adding data for that entitlements pool, it shouldn't need an update
        self.assertFalse(pooltype_cache.requires_update())

    def test_update(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir
        self.cp.getEntitlementList.return_value = [
            self._build_ent_json("poolid", "some type"),
            self._build_ent_json("poolid2", "some other type"),
        ]

        # requires_update should be true, and should allow this method
        # to generate a correct mapping
        pooltype_cache.update()

        self.assertEqual(2, len(pooltype_cache.pooltype_map))
        self.assertEqual("some type", pooltype_cache.get("poolid"))
        self.assertEqual("some other type", pooltype_cache.get("poolid2"))

    # This is populated when available subs are refreshed
    def test_update_from_pools(self):
        # Input is a map of pool ids to pool json
        pools_map = {}

        for i in range(5):
            pool_id = "poolid" + str(i)
            pools_map[pool_id] = self._build_pool_json(pool_id, "some type")

        pooltype_cache = PoolTypeCache()
        pooltype_cache.update_from_pools(pools_map)

        self.assertEqual(5, len(pooltype_cache.pooltype_map))
        for i in range(5):
            expected_id = "poolid" + str(i)
            self.assertEqual("some type", pooltype_cache.get(expected_id))

    def test_requires_update_ents_with_no_pool(self):
        pooltype_cache = PoolTypeCache()
        pooltype_cache.ent_dir = self.ent_dir
        for ent in self.ent_dir.certs:
            ent.pool = None

        # No ents have pools so there is nothing we can update
        self.assertFalse(pooltype_cache.requires_update())

    def test_reading_pool_type_from_json_cache(self):
        pool_status = [self._build_ent_json("poolid", "some type")]
        self.pool_cache.load_status = Mock()
        self.pool_cache.server_status = pool_status
        pooltype_cache = PoolTypeCache()
        pooltype_cache._do_update()
        result = pooltype_cache.get("poolid")
        self.assertEqual("some type", result)

    def _build_ent_json(self, pool_id, pool_type):
        result = {}
        result["id"] = "1234"
        result["pool"] = self._build_pool_json(pool_id, pool_type)
        return result

    def _build_pool_json(self, pool_id, pool_type):
        return {"id": pool_id, "calculatedAttributes": {"compliance_type": pool_type}}


class TestContentAccessCache(SubManFixture):
    MOCK_CONTENT = {
        "lastUpdate": "2016-12-01T21:56:35+0000",
        "contentListing": {"42": ["cert-part1", "cert-part2"]},
    }

    MOCK_CONTENT_EMPTY_CONTENT_LISTING = {"lastUpdate": "2016-12-01T21:56:35+0000", "contentListing": None}

    MOCK_CERT = """
before
-----BEGIN ENTITLEMENT DATA-----
entitlement data goes here
-----END ENTITLEMENT DATA-----
after
    """

    MOCK_OPEN_EMPTY = mock_open()

    MOCK_OPEN_CORRUPTED_CACHE = mock_open(read_data="[{]}")

    MOCK_OPEN_NOT_VALID_CACHE = mock_open(read_data="{}")

    MOCK_OPEN_CACHE = mock_open(read_data=json.dumps(MOCK_CONTENT))

    def setUp(self):
        super(TestContentAccessCache, self).setUp()
        self.cache = ContentAccessCache()
        self.cache.cp_provider = Mock()
        self.mock_uep = Mock()
        self.mock_uep.getAccessibleContent = Mock(return_value=self.MOCK_CONTENT)
        self.cache.cp_provider.get_consumer_auth_cp = Mock(return_value=self.mock_uep)
        self.cache.identity = Mock()
        self.cert = Mock()

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_empty_cache(self):
        self.assertFalse(self.cache.exists())

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_read_empty_cache(self):
        self.cache.exists = Mock(return_value=True)
        empty_cache = self.cache.read()
        self.assertEqual(empty_cache, "")
        result = self.cache.check_for_update()
        self.mock_uep.getAccessibleContent.assert_called_once()
        self.assertEqual(result, self.MOCK_CONTENT)

    @patch("subscription_manager.cache.open", MOCK_OPEN_CORRUPTED_CACHE)
    def test_read_corrupted_cache(self):
        """
        This is intended for testing reading corrupted cache
        """
        self.cache.exists = Mock(return_value=True)
        empty_cache = self.cache.read()
        self.assertEqual(empty_cache, "[{]}")
        result = self.cache.check_for_update()
        self.mock_uep.getAccessibleContent.assert_called_once()
        self.assertEqual(result, self.MOCK_CONTENT)

    @patch("subscription_manager.cache.open", MOCK_OPEN_NOT_VALID_CACHE)
    def test_read_not_valid_cache(self):
        """
        This is intended for testing of reading json file without valid data
        """
        self.cache.exists = Mock(return_value=True)
        empty_cache = self.cache.read()
        self.assertEqual(empty_cache, "{}")
        result = self.cache.check_for_update()
        self.mock_uep.getAccessibleContent.assert_called_once()
        self.assertEqual(result, self.MOCK_CONTENT)

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_writes_to_cache_after_read(self):
        self.cache.check_for_update()
        self.MOCK_OPEN_EMPTY.assert_any_call(ContentAccessCache.CACHE_FILE, "w")
        self.MOCK_OPEN_EMPTY().write.assert_any_call(json.dumps(self.MOCK_CONTENT))

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_cert_updated_after_read(self):
        self.cert.serial = 42
        update_data = self.cache.check_for_update()
        self.cache.update_cert(self.cert, update_data)
        self.MOCK_OPEN_EMPTY.assert_any_call(self.cert.path, "w")
        self.MOCK_OPEN_EMPTY().write.assert_any_call("".join(self.MOCK_CONTENT["contentListing"]["42"]))

    @patch("subscription_manager.cache.open", MOCK_OPEN_CACHE)
    def test_check_for_update_provides_date(self):
        mock_exists = Mock(return_value=True)
        with patch("os.path.exists", mock_exists):
            self.cache.check_for_update()
            date = isodate.parse_date("2016-12-01T21:56:35+0000")
            self.mock_uep.getAccessibleContent.assert_called_once_with(
                self.cache.identity.uuid, if_modified_since=date
            )

    @patch("os.path.exists", Mock(return_value=True))
    def test_cache_remove_deletes_file(self):
        mock_remove = Mock()
        with patch("os.remove", mock_remove):
            self.cache.remove()
            mock_remove.assert_called_once_with(ContentAccessCache.CACHE_FILE)

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_cache_handles_empty_content_listing(self):
        self.mock_uep.getAccessibleContent = Mock(return_value=self.MOCK_CONTENT_EMPTY_CONTENT_LISTING)
        self.cache.check_for_update()
        # getting this far means we did not raise an exception :-)

    @patch("subscription_manager.cache.open", MOCK_OPEN_EMPTY)
    def test_cache_fails_server_issues_gracefully(self):
        self.mock_uep.getAccessibleContent = Mock(side_effect=RestlibException(404))
        self.cache.check_for_update()
        # getting this far means we did not raise an exception :-)


class TestSupportedResourcesCache(SubManFixture):
    MOCK_CACHE_FILE_CONTENT = '{"a3f43883-315b-4cc4-bfb5-5771946d56d7": {"": "/", "cdn": "/cdn"}}'

    MOCK_SUPPORTED_RESOURCES_RESPONSE = {"pools": "/pools", "roles": "/roles", "users": "/users"}

    def setUp(self):
        super(TestSupportedResourcesCache, self).setUp()
        self.cache = SupportedResourcesCache()

    def test_reading_nonexisting_cache(self):
        data = self.cache.read_cache_only()
        self.assertIsNone(data)

    def test_reading_existing_cache(self):
        temp_cache_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_cache_dir)
        self.cache.CACHE_FILE = os.path.join(temp_cache_dir, "supported_resources.json")
        with open(self.cache.CACHE_FILE, "w") as cache_file:
            cache_file.write(self.MOCK_CACHE_FILE_CONTENT)
        data = self.cache.read_cache_only()
        self.assertTrue("a3f43883-315b-4cc4-bfb5-5771946d56d7" in data)
        self.assertEqual(data["a3f43883-315b-4cc4-bfb5-5771946d56d7"], {"": "/", "cdn": "/cdn"})

    def test_cache_is_obsoleted_by_new_identity(self):
        temp_cache_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_cache_dir)
        self.cache.CACHE_FILE = os.path.join(temp_cache_dir, "supported_resources.json")
        with open(self.cache.CACHE_FILE, "w") as cache_file:
            cache_file.write(self.MOCK_CACHE_FILE_CONTENT)
        mock_uep = Mock()
        mock_uep.get_supported_resources = Mock(return_value=self.MOCK_SUPPORTED_RESOURCES_RESPONSE)
        mock_identity = Mock()
        mock_identity.uuid = "f0000000-aaaa-bbbb-bbbb-5771946d56d8"
        data = self.cache.read_data(uep=mock_uep, identity=mock_identity)
        self.assertEqual(data, self.MOCK_SUPPORTED_RESOURCES_RESPONSE)

    @subman_marker_slow
    @subman_marker_slow_timeout
    def test_cache_is_obsoleted_by_timeout(self):
        old_timeout = self.cache.TIMEOUT
        self.cache.TIMEOUT = 1
        temp_cache_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_cache_dir)
        self.cache.CACHE_FILE = os.path.join(temp_cache_dir, "supported_resources.json")
        with open(self.cache.CACHE_FILE, "w") as cache_file:
            cache_file.write(self.MOCK_CACHE_FILE_CONTENT)
        mock_uep = Mock()
        mock_uep.get_supported_resources = Mock(return_value=self.MOCK_SUPPORTED_RESOURCES_RESPONSE)
        mock_identity = Mock()
        mock_identity.uuid = "a3f43883-315b-4cc4-bfb5-5771946d56d7"
        time.sleep(2)
        data = self.cache.read_data(uep=mock_uep, identity=mock_identity)
        self.assertEqual(data, self.MOCK_SUPPORTED_RESOURCES_RESPONSE)
        self.cache.TIMEOUT = old_timeout


class TestAvailableEntitlementsCache(SubManFixture):
    MOCK_CACHE_FILE_CONTENT = """{
    "b1002709-6d67-443e-808b-a7afcbe5b47e": {
        "filter_options": {
            "after_date": null,
            "future": null,
            "match_installed": null,
            "matches": "*fakeos*",
            "no_overlap": null,
            "on_date": null,
            "service_level": null,
            "show_all": null
        },
        "pools": [
            {
                "addons": null,
                "attributes": [],
                "contractNumber": "0",
                "endDate": "01/16/2021",
                "id": "ff8080816fb38f78016fb392d26f0267",
                "management_enabled": false,
                "pool_type": "Standard",
                "productId": "fakeos-bits",
                "productName": "Fake OS Bits",
                "providedProducts": {
                    "38072": "Fake OS Bits"
                },
                "quantity": "5",
                "roles": null,
                "service_level": null,
                "service_type": null,
                "startDate": "01/17/2020",
                "suggested": 1,
                "usage": null
            }
        ],
        "timeout": 1579613054.079684
    }
}
"""

    def setUp(self):
        super(TestAvailableEntitlementsCache, self).setUp()
        self.cache = AvailableEntitlementsCache()

    def test_reading_nonexisting_cache(self):
        """
        Test reading cache, when there is no cache file yet
        """
        data = self.cache.read_cache_only()
        self.assertIsNone(data)

    def test_reading_existing_cache(self):
        """
        Test reading cache from file
        """
        temp_cache_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_cache_dir)
        self.cache.CACHE_FILE = os.path.join(temp_cache_dir, "available_entitlements.json")
        with open(self.cache.CACHE_FILE, "w") as cache_file:
            cache_file.write(self.MOCK_CACHE_FILE_CONTENT)
        data = self.cache.read_cache_only()
        self.assertTrue("b1002709-6d67-443e-808b-a7afcbe5b47e" in data)
        self.assertEqual(data["b1002709-6d67-443e-808b-a7afcbe5b47e"]["timeout"], 1579613054.079684)
        self.assertEqual(
            data["b1002709-6d67-443e-808b-a7afcbe5b47e"]["filter_options"]["matches"], "*fakeos*"
        )
        self.assertEqual(len(data["b1002709-6d67-443e-808b-a7afcbe5b47e"]["pools"]), 1)

    def test_timeout(self):
        """
        Test computing timeout of cache based on smoothed response time (SRT)
        """
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        uep.conn.smoothed_rt = 3.0
        timeout = self.cache.timeout()
        self.assertTrue(timeout >= self.cache.LBOUND)
        self.assertTrue(timeout <= self.cache.UBOUND)

    def test_timeout_no_srt(self):
        """
        Test computing timeout, when there is no SRT yet
        """
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        uep.conn.smoothed_rt = None
        timeout = self.cache.timeout()
        self.assertEqual(timeout, self.cache.LBOUND)

    def test_min_timeout(self):
        """
        Test computing timout, when SRT is smaller than lower bound
        """
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        uep.conn.smoothed_rt = 0.01
        timeout = self.cache.timeout()
        self.assertEqual(timeout, self.cache.LBOUND)

    def test_max_timeout(self):
        """
        Test computing timout, when SRT is bigger than upper bound
        """
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        uep.conn.smoothed_rt = 20.0
        timeout = self.cache.timeout()
        self.assertEqual(timeout, self.cache.UBOUND)


class TestSyspurposeComplianceStatusCache(SubManFixture):
    def setUp(self):
        super(TestSyspurposeComplianceStatusCache, self).setUp()
        self.syspurpose_cache = SyspurposeComplianceStatusCache()

    def test_status_on_failed_load(self):
        uep = StubUEP()
        uep.has_capability = Mock(side_effect=ProxyException("bad-proxy", 1234))
        uuid = "FAKEUUID"
        on_date = datetime.datetime.now()
        self.syspurpose_cache.load_status(uep, uuid, on_date)
        self.assertEqual(self.syspurpose_cache.get_overall_status(), "Unknown")
        self.assertEqual(self.syspurpose_cache.get_overall_status_code(), "unknown")
        self.assertIsNone(self.syspurpose_cache.get_status_reasons())


class TestCloudTokenCache(SubManFixture):
    original_path = None

    @classmethod
    def setUpClass(cls):
        cls.original_path = cache.CloudTokenCache.CACHE_FILE

    @classmethod
    def tearDownClass(cls):
        # Ensure we have cleaned up properly
        assert (
            cls.original_path == cache.CloudTokenCache.CACHE_FILE
        ), f"{cls.__name__} did not clean up after itself"

    def setUp(self):
        self.actual_path: str = cache.CloudTokenCache.CACHE_FILE
        self.test_path = tempfile.NamedTemporaryFile(prefix="cloud_token_cache.", suffix=".json")
        cache.CloudTokenCache.CACHE_FILE = self.test_path.name

    def tearDown(self):
        cache.CloudTokenCache.CACHE_FILE = self.actual_path
        del self.actual_path
        del self.test_path

    @staticmethod
    def _get_uep(jwt_response: dict) -> Mock:
        """Create mock UEPConnection object with custom `getCloudJWT()`."""
        uep = Mock(spec=UEPConnection)
        uep.getCloudJWT.return_value = jwt_response
        return uep

    @staticmethod
    def _create_jwt(expired: bool = False) -> Dict[str, str]:
        """Create fake JWT.

        :param expired: When True, the token will have the expiration date in the past.
        """
        now = int(time.time())
        expiration: int = (now + 60) if not expired else (now - 60)

        jwt_header: str = base64.b64encode(b"{}").decode("utf-8")
        jwt_body: str = base64.b64encode(json.dumps({"exp": expiration}).encode("utf-8")).decode("utf-8")
        jwt_signature: str = base64.b64encode(b"{}").decode("utf-8")

        return {
            "anonymousConsumerUuid": "fake-uuid",
            "token": f"{jwt_header}.{jwt_body}.{jwt_signature}".replace("=", ""),
            "tokenType": "Fake-CP-Cloud-Registration",
            "__is_expired": expired,
        }

    def test_no_cache(self):
        """Call the server if we don't have any cache file. Cache the result."""
        expected = self._create_jwt(expired=False)
        uep = self._get_uep(jwt_response=expected)
        jwt = cache.CloudTokenCache.get(
            uep=uep, cloud_id="fake-cloud", metadata="fake metadata", signature="fake signature"
        )

        # We have called the server
        self.assertTrue(uep.getCloudJWT.called)
        uep.getCloudJWT.assert_called_once_with("fake-cloud", "fake metadata", "fake signature")
        # The cache returned the response
        self.assertIsNotNone(jwt)
        # The response was cached into a file
        self.assertTrue(os.path.isfile(cache.CloudTokenCache.CACHE_FILE))
        with open(cache.CloudTokenCache.CACHE_FILE, "r") as f:
            self.assertEqual(json.load(f), expected)

    def test_is_valid__when_valid(self):
        """Check that cache is reported as valid if the expiration date is in the future."""
        cache.CloudTokenCache._save_to_file(token=self._create_jwt(expired=False))
        self.assertTrue(cache.CloudTokenCache.is_valid())

    def test_is_valid__when_invalid(self):
        """Check that cache is reported as invalid if the expiration date is in the past."""
        cache.CloudTokenCache._save_to_file(token=self._create_jwt(expired=True))
        self.assertFalse(cache.CloudTokenCache.is_valid())

    def test_expired_cache(self):
        """Call the server if we have a cache file, but its content is expired."""
        # Simulate old expired cache
        cache.CloudTokenCache._save_to_file(token=self._create_jwt(expired=True))

        expected = self._create_jwt(expired=False)
        uep = self._get_uep(jwt_response=expected)
        jwt = cache.CloudTokenCache.get(
            uep=uep, cloud_id="fake-cloud", metadata="fake metadata", signature="fake signature"
        )

        # We have called the server
        self.assertTrue(uep.getCloudJWT.called)
        uep.getCloudJWT.assert_called_once_with("fake-cloud", "fake metadata", "fake signature")
        # The cache returned the response
        self.assertIsNotNone(jwt)
        # The response was cached into a file
        self.assertTrue(os.path.isfile(cache.CloudTokenCache.CACHE_FILE))
        with open(cache.CloudTokenCache.CACHE_FILE, "r") as f:
            self.assertEqual(json.load(f), expected)

    def test_valid_cache(self):
        """Return the cached value."""
        expected = self._create_jwt(expired=False)
        # Simulate existing cache
        cache.CloudTokenCache._save_to_file(token=expected)

        uep = self._get_uep(jwt_response={})
        jwt = cache.CloudTokenCache.get(
            uep=uep, cloud_id="fake-cloud", metadata="fake metadata", signature="fake signature"
        )

        # We have not called the server
        self.assertFalse(uep.getCloudJWT.called)
        # The cache returned the response
        self.assertIsNotNone(jwt)
        # The cache file still exists
        self.assertTrue(os.path.isfile(cache.CloudTokenCache.CACHE_FILE))
        with open(cache.CloudTokenCache.CACHE_FILE, "r") as f:
            self.assertEqual(json.load(f), expected)

    def test_delete(self):
        """Delete existing cache file."""
        # Simulate existing cache
        cache.CloudTokenCache._save_to_file(token=self._create_jwt(expired=False))

        cache.CloudTokenCache.delete_cache()

        # The cache file does not exist
        self.assertFalse(os.path.isfile(cache.CloudTokenCache.CACHE_FILE))

    def test_delete_no_cache(self):
        """Try to delete cache file that does not exist."""
        # Delete the empty file
        os.remove(cache.CloudTokenCache.CACHE_FILE)

        cache.CloudTokenCache.delete_cache()
        self.assertFalse(os.path.isfile(cache.CloudTokenCache.CACHE_FILE))
