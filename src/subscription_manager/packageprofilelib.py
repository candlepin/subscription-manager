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

from subscription_manager import injection as inj
from subscription_manager import certlib


class PackageProfileLib(certlib.DataLib):
    """
    Another "Lib" object, used by rhsmcertd to update the profile
    periodically.
    """
    def _do_update(self):
        action = PackageProfileAction(uep=self.uep)
        return action.perform()


class PackageProfileAction(object):
    def __init__(self, uep=None):
        self.report = PackageProfileActionReport()
        self.uep = uep

    def perform(self):
        profile_mgr = inj.require(inj.PROFILE_MANAGER)
        consumer_identity = inj.require(inj.IDENTITY)
        ret = profile_mgr.update_check(self.uep, consumer_identity.uuid)
        self.report._status = ret
        return self.report


class PackageProfileActionReport(certlib.ActionReport):
    name = "Package profile updates"
