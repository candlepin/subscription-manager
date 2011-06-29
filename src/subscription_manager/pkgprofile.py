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

""" Module for managing the package profile for a system. """

import logging
import gettext
_ = gettext.gettext

from rhsm.profile import get_profile

log = logging.getLogger('rhsm-app.' + __name__)


class PackageProfile(object):
    """
    Manages the profile of packages installed on this system. 
    """

    def __init__(self):
        self.profile = get_profile('rpm')
        self.pkg_dicts = self.profile.collect()

    def update_check(self, uep, consumer_uuid):
        """
        Check if packages have changed, and push an update if so.
        """
        log.info("Updating facts.")
        uep.updatePackageProfile(consumer_uuid, self.pkg_dicts)

