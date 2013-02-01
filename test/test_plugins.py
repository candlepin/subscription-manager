#
# Copyright (c) 2013 Red Hat, Inc.
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


import unittest
from subscription_manager.plugins import api_version_ok, parse_version, \
        PluginManager


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.manager = PluginManager("some/search/path", "some/config/path")

    def test_load_plugin_with_no_api_version(self):
        self.manager._load_plugin("no_api_version.py")


class TestVersionChecks(unittest.TestCase):
    def test_parse_version(self):
        maj, min = parse_version("1.0")
        self.assertEquals(1, maj)
        self.assertEquals(0, min)

    def test_api_versions_equal(self):
        self.assertTrue(api_version_ok("1.0", "1.0"))

    def test_api_version_old_minor(self):
        self.assertTrue(api_version_ok("1.1", "1.0"))

    def test_api_version_old_major(self):
        self.assertFalse(api_version_ok("1.0", "0.9"))

    def test_api_version_new(self):
        self.assertFalse(api_version_ok("1.0", "1.1"))
