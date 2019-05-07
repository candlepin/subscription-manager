# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2019 Red Hat, Inc.
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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import tempfile
import os
import mock

from . import stubs

from subscription_manager.capabilities import ServerCache

SUBMAN_VERSION = "1.25.1-1.el7"
CONSUMER_UUID = "84cf4ee1-9b72-4ebd-8647-056d2fc36898"
SUPPORTED_RESOURCES_SERVER = {
    "": "/",
    "guestids": "/consumers/{consumer_uuid}/guestids",
    "cdn": "/cdn",
    "content_overrides": "/consumers/{consumer_uuid}/content_overrides",
    "hypervisors": "/hypervisors",
    "serials": "/serials",
    "deleted_consumers": "/deleted_consumers",
    "consumers": "/consumers",
    "content": "/content",
    "entitlements": "/entitlements",
    "events": "/events",
    "status": "/status",
    "jobs": "/jobs",
    "users": "/users",
    "subscriptions": "/subscriptions",
    "rules": "/rules",
    "distributor_versions": "/distributor_versions",
    "consumertypes": "/consumertypes",
    "pools": "/pools",
    "atom": "/atom",
    "owners": "/owners",
    "roles": "/roles",
    "admin": "/admin",
    "products": "/products",
    "activation_keys": "/activation_keys",
    "crl": "/crl",
    "foo": "/foo"
}

CACHE_FILE = """
{
    "version": "%s",
    "%s": {
        "supported_resources": {
            "": "/",
            "guestids": "/consumers/{consumer_uuid}/guestids",
            "cdn": "/cdn",
            "content_overrides": "/consumers/{consumer_uuid}/content_overrides",
            "hypervisors": "/hypervisors",
            "serials": "/serials",
            "deleted_consumers": "/deleted_consumers",
            "consumers": "/consumers",
            "content": "/content",
            "entitlements": "/entitlements",
            "events": "/events",
            "status": "/status",
            "jobs": "/jobs",
            "users": "/users",
            "subscriptions": "/subscriptions",
            "rules": "/rules",
            "distributor_versions": "/distributor_versions",
            "consumertypes": "/consumertypes",
            "pools": "/pools",
            "atom": "/atom",
            "owners": "/owners",
            "roles": "/roles",
            "admin": "/admin",
            "products": "/products",
            "activation_keys": "/activation_keys",
            "crl": "/crl",
            "bar": "/bar"
        }
    }
}""" % (SUBMAN_VERSION, CONSUMER_UUID)


class TestServerCache(unittest.TestCase):
    """
    Class for testing ServerChache
    """

    def setUp(self):
        """
        Set up testing environment before each test
        """
        temp_repo_dir = tempfile.mkdtemp()
        cache_file = os.path.join(temp_repo_dir, 'server_capabilities.json')
        with open(cache_file, 'w') as repo_file:
            repo_file.write(CACHE_FILE)
        self.ServerCache = ServerCache
        self.ServerCache.CACHE_FILE = cache_file
        self.consumer_uuid = "84cf4ee1-9b72-4ebd-8647-056d2fc36898"
        self.version_patcher = mock.patch('subscription_manager.capabilities.version')
        self.version_mock = self.version_patcher.start()
        self.version_mock.rpm_version = SUBMAN_VERSION
        self.uep = stubs.StubUEP()
        self.uep._resources = SUPPORTED_RESOURCES_SERVER

    def tearDown(self):
        """
        Tear down test environment
        """
        self.version_patcher.stop()

    def test_loading_cached_data(self):
        """
        Test loading cached data form file
        """
        resources = self.ServerCache.get_supported_resources(self.consumer_uuid, self.uep)
        self.assertTrue("bar" in resources)

    def test_changed_consumer_uuid(self):
        """
        Test that resources are loaded from server, when consumer UUID was changed
        """
        consumer_uuid = "84cf4ee1-9b72-4ebd-8647-aaaaaaaaaaaa"
        resources = self.ServerCache.get_supported_resources(consumer_uuid, self.uep)
        self.assertTrue("foo" in resources)

    def test_changed_subman_version(self):
        """
        Test that resources are loaded from server, when version of subscription-manager was changed
        """
        self.version_mock.rpm_version = "1.36.1-1.el9"
        resources = self.ServerCache.get_supported_resources(self.consumer_uuid, self.uep)
        self.assertTrue("foo" in resources)
