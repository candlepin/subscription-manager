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

class ProfileTests(unittest.TestCase):

    def test_get_rpm_profile(self):
        # This will fail if you're running tests on non-rpm based distros:
        profile = get_profile("rpm").collect()

        # Everybody's gotta have at least 10 packages right?
        self.assertTrue(len(profile) > 10)

        for pkg in profile:
            self.assertTrue(pkg.has_key('name'))
            self.assertTrue(pkg.has_key('version'))
            self.assertTrue(pkg.has_key('version'))
            self.assertTrue(pkg.has_key('release'))
            self.assertTrue(pkg.has_key('epoch'))
            self.assertTrue(pkg.has_key('arch'))
            self.assertTrue(pkg.has_key('vendor'))

    def test_get_profile_bad_type(self):
        self.assertRaises(InvalidProfileType, get_profile, "notreal")
