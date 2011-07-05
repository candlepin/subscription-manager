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
import os
import gettext
_ = gettext.gettext

from rhsm.profile import get_profile

log = logging.getLogger('rhsm-app.' + __name__)

CACHE_FILE = "/var/lib/rhsm/packages/packages.json"


class ProfileManager(object):
    """
    Manages the profile of packages installed on this system. 
    """

    def __init__(self, current_profile=None, cached_profile=None):

        # If we weren't given a profile, load the current systems packages:
        self.current_profile = current_profile
        if not current_profile:
            self.current_profile = get_profile('rpm')

    def _write_cached_profile(self):
        """ 
        Write the current profile to disk. Should only be done after
        successfully pushing the profile to the server.
        """
        pass

    def _read_cached_profile(self):
        """
        Load the last package profile we sent to the server.
        Returns none if no cache file exists.
        """
        pass

    def _cache_exists(self):
        return os.path.exists(CACHE_FILE)

    def update_check(self, uep, consumer_uuid):
        """
        Check if packages have changed, and push an update if so.
        """
        if self.has_changed():
            log.info("Updating package profile.")
            uep.updatePackageProfile(consumer_uuid, self.current_profile.collect())
            self._write_cached_profile()
        else: 
            log.info("Package profile has not changed, skipping upload.")

    def has_changed(self):
        """
        Check if the current system profile has changed since the last time we
        updated.
        """
        if not self._cache_exists():
            log.info( "Cache exists")
            return True
        cached_profile = self._read_cached_profile()
        return not cached_profile == self.current_profile

