from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 - 2012 Red Hat, Inc.
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

from rhsm.profile import Package, RPMProfile, get_profile, InvalidProfileType
from rhsm import ourjson as json
from mock import Mock

from nose.plugins.attrib import attr


@attr('functional')
class ProfileTests(unittest.TestCase):

    def test_get_rpm_profile(self):
        # This will fail if you're running tests on non-rpm based distros:
        profile = get_profile("rpm")
        pkg_dicts = profile.collect()
        self.assertEqual(len(profile.packages), len(pkg_dicts))

        # Everybody's gotta have at least 10 packages right?
        self.assertTrue(len(pkg_dicts) > 10)

        for pkg in pkg_dicts:
            self.assertTrue('name' in pkg)
            self.assertTrue('version' in pkg)
            self.assertTrue('version' in pkg)
            self.assertTrue('release' in pkg)
            self.assertTrue('epoch' in pkg)
            self.assertTrue('arch' in pkg)
            self.assertTrue('vendor' in pkg)

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
        profile = self._mock_pkg_profile(dummy_pkgs)
        self.assertEqual(2, len(profile.packages))

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

    def test_equality_different_object_type(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)
        self.assertFalse(profile == "hello")

    def test_equality_no_change(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)

        other = self._mock_pkg_profile(dummy_pkgs)
        self.assertTrue(profile == other)

    def test_equality_packages_added(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)

        dummy_pkgs.append(Package(name="package3", version="3.0.0", release=2,
            arch="x86_64"))
        other = self._mock_pkg_profile(dummy_pkgs)
        self.assertFalse(profile == other)

    def test_equality_packages_removed(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)

        dummy_pkgs.pop()
        other = self._mock_pkg_profile(dummy_pkgs)
        self.assertFalse(profile == other)

    def test_equality_packages_updated(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)

        # "Upgrade" package2:
        dummy_pkgs[1].version = "3.1.5"
        other = self._mock_pkg_profile(dummy_pkgs)
        self.assertFalse(profile == other)

    def test_equality_packages_replaced(self):
        dummy_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        profile = self._mock_pkg_profile(dummy_pkgs)

        # Remove package2, add package3:
        dummy_pkgs.pop()
        dummy_pkgs.append(Package(name="package3", version="3.0.0", release=2,
            arch="x86_64"))
        other = self._mock_pkg_profile(dummy_pkgs)
        self.assertFalse(profile == other)
