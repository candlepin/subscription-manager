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
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from rhsm.connection import UEPConnection
    from subscription_manager.identity import Identity
    from subscription_manager.cache import ProfileManager
    from subscription_manager.cp_provider import CPProvider

from subscription_manager import injection as inj
from subscription_manager import certlib


class PackageProfileActionInvoker(certlib.BaseActionInvoker):
    """Used by rhsmcertd to update the profile
    periodically.
    """

    def _do_update(self) -> "PackageProfileActionReport":
        action = PackageProfileActionCommand()
        return action.perform()


class PackageProfileActionCommand:
    """Action for updating the list of installed packages to RHSM API,

    Returns a PackageProfileActionReport.
    """

    def __init__(self):
        self.report = PackageProfileActionReport()
        self.cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        self.uep: UEPConnection = self.cp_provider.get_consumer_auth_cp()

    def perform(self, force_upload: bool = False) -> "PackageProfileActionReport":
        profile_mgr: ProfileManager = inj.require(inj.PROFILE_MANAGER)
        consumer_identity: Identity = inj.require(inj.IDENTITY)
        ret: Literal[0, 1] = profile_mgr.update_check(self.uep, consumer_identity.uuid, force=force_upload)
        self.report._status = ret
        return self.report


class PackageProfileActionReport(certlib.ActionReport):
    name = "Package profile updates"
