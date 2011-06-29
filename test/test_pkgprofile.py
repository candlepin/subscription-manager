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

import stubs

from subscription_manager.pkgprofile import PackageProfile
from mock import Mock 


class _FACT_MATCHER(object):
    def __eq__(self, other):
        return True


FACT_MATCHER = _FACT_MATCHER()


class TestPackageProfile(unittest.TestCase):

    def setUp(self):
        self.pkg_profile = PackageProfile()

    def test_factlib_updates(self):
        uuid = 'FAKEUUID'
        uep = Mock()
        uep.updatePackageProfile = Mock()

        self.pkg_profile.update_check(uep, uuid)

        uep.updatePackageProfile.assert_called_with(uuid, 
                FACT_MATCHER)

