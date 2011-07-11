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

import stubs

from subscription_manager.pkgprofile import *
from rhsm.profile import *


class _FACT_MATCHER(object):
    def __eq__(self, other):
        return True


FACT_MATCHER = _FACT_MATCHER()


class TestProfileManager(unittest.TestCase):

    def setUp(self):
        self.pkg_profile = ProfileManager()

    def test_update_check_no_change(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updatePackageProfile = Mock()

        self.pkg_profile.has_changed = Mock(return_value=False)
        self.pkg_profile._write_cached_profile = Mock()
        self.pkg_profile.update_check(uep, uuid)

        self.assertEquals(0, uep.updatePackageProfile.call_count)
        self.assertEquals(0, self.pkg_profile._write_cached_profile.call_count)

    def test_update_check_has_changed(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updatePackageProfile = Mock()

        self.pkg_profile.has_changed = Mock(return_value=True)
        self.pkg_profile._write_cached_profile = Mock()
        self.pkg_profile.update_check(uep, uuid)

        uep.updatePackageProfile.assert_called_with(uuid, 
                FACT_MATCHER)
        self.assertEquals(1, self.pkg_profile._write_cached_profile.call_count)

    def test_update_check_error_uploading(self):
        uuid = 'FAKEUUID'
        uep = Mock()

        self.pkg_profile.has_changed = Mock(return_value=True)
        self.pkg_profile._write_cached_profile = Mock()
        # Throw an exception when trying to upload:
        uep.updatePackageProfile = Mock(side_effect=Exception('BOOM!'))

        self.assertRaises(Exception, self.pkg_profile.update_check, uep, uuid)
        uep.updatePackageProfile.assert_called_with(uuid, 
                FACT_MATCHER)
        self.assertEquals(0, self.pkg_profile._write_cached_profile.call_count)

    def test_has_changed_no_cache(self):
        self.pkg_profile._cache_exists = Mock(return_value=False)
        self.assertTrue(self.pkg_profile.has_changed())

    def test_has_changed_no_changes(self):
        current_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        current_profile = self._mock_pkg_profile(current_pkgs)
        manager = ProfileManager(current_profile=current_profile)

        cached_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        cached_profile = self._mock_pkg_profile(cached_pkgs)

        manager._cache_exists = Mock(return_value=True)
        manager._read_cached_profile = Mock(return_value=cached_profile)

        self.assertFalse(manager.has_changed())
        manager._read_cached_profile.assert_called_with()

    def test_has_changed(self):
        current_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        current_profile = self._mock_pkg_profile(current_pkgs)
        manager = ProfileManager(current_profile=current_profile)

        cached_pkgs = [
                Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                Package(name="package3", version="3.0.0", release=3, arch="x86_64")]
        cached_profile = self._mock_pkg_profile(cached_pkgs)

        manager._cache_exists = Mock(return_value=True)
        manager._read_cached_profile = Mock(return_value=cached_profile)

        self.assertTrue(manager.has_changed())
        manager._read_cached_profile.assert_called_with()

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


