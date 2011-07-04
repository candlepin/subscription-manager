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

from rhsm.profile import *
from mock import Mock
import simplejson as json

class ProfileTests(unittest.TestCase):

    def test_get_rpm_profile(self):
        # This will fail if you're running tests on non-rpm based distros:
        profile = get_profile("rpm")
        pkg_dicts = profile.collect()
        self.assertEquals(len(profile.packages), len(pkg_dicts))

        # Everybody's gotta have at least 10 packages right?
        self.assertTrue(len(pkg_dicts) > 10)

        for pkg in pkg_dicts:
            self.assertTrue(pkg.has_key('name'))
            self.assertTrue(pkg.has_key('version'))
            self.assertTrue(pkg.has_key('version'))
            self.assertTrue(pkg.has_key('release'))
            self.assertTrue(pkg.has_key('epoch'))
            self.assertTrue(pkg.has_key('arch'))
            self.assertTrue(pkg.has_key('vendor'))

    def test_package_objects(self):
        profile = get_profile("rpm")
        for pkg in profile.packages:
            self.assertTrue(isinstance(pkg, Package))

    def test_get_profile_bad_type(self):
        self.assertRaises(InvalidProfileType, get_profile, "notreal")

    def test_load_profile_from_file(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        dummy_profile_json = self._packages_to_json(dummy_pkgs)
        mock_file = Mock()
        mock_file.read = Mock(return_value=dummy_profile_json)

        profile = RPMProfile(from_file=mock_file)
        self.assertEquals(2, len(profile.packages))

    def _packages_to_json(self, package_list):
        new_list = []
        for pkg in package_list:
            new_list.append(pkg.to_dict())
        return json.dumps(new_list)
