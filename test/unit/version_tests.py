#
# Copyright (c) 2012 Red Hat, Inc.
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

import rhsm.version
import unittest

NOT_COLLECTED = "non-collected-package"


class VersionTests(unittest.TestCase):
    def test_rpm_version(self):
        self.assertTrue(isinstance(rhsm.version.rpm_version, str))

    def test_rpm_version_no_name(self):
        self.assertFalse('python-rhsm' in rhsm.version.rpm_version)

    def test_rpm_version_at_least_dash(self):
        # just looking for something version number like
        self.assertTrue('-' in rhsm.version.rpm_version)
