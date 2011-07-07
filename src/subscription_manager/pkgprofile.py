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
import simplejson as json
import gettext
_ = gettext.gettext

from rhsm.profile import get_profile, RPMProfile
from subscription_manager.certlib import DataLib, ConsumerIdentity

log = logging.getLogger('rhsm-app.' + __name__)

CACHE_FILE = "/var/lib/rhsm/packages/packages.json"


class ProfileLib(DataLib):

    def _do_update(self):
        profile_mgr = ProfileManager()
        consumer = ConsumerIdentity.read()
        consumer_uuid = consumer.getConsumerId()
        return profile_mgr.update_check(self.uep, consumer_uuid)


class ProfileManager(object):
    """
    Manages the profile of packages installed on this system. 
    """

    def __init__(self, current_profile=None):

        # If we weren't given a profile, load the current systems packages:
        self.current_profile = current_profile
        if not current_profile:
            self.current_profile = get_profile('rpm')

    def _write_cached_profile(self):
        """ 
        Write the current profile to disk. Should only be done after
        successfully pushing the profile to the server.
        """
        if not os.access(os.path.dirname(CACHE_FILE), os.R_OK):
            os.makedirs(os.path.dirname(CACHE_FILE))
        try:
            f = open(CACHE_FILE, "w+")
            json.dump(self.current_profile.collect(), f)
            f.close()
        except IOError, e:
            log.error("Unable to write package profile cache to: %s" % 
                    CACHE_FILE)
            log.exception(e)

    def _read_cached_profile(self):
        """
        Load the last package profile we sent to the server.
        Returns none if no cache file exists.
        """
        try:
            f = open(CACHE_FILE)
            profile = RPMProfile(from_file=f)
            f.close()
            return profile
        except IOError:
            log.error("Unable to read package profile: %s" % CACHE_FILE)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
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
            # Return the number of 'updates' we did, assuming updating all 
            # packages at once is one update.
            return 1
        else: 
            log.info("Package profile has not changed, skipping upload.")
            return 0 # No updates performed.

    def has_changed(self):
        """
        Check if the current system profile has changed since the last time we
        updated.
        """
        if not self._cache_exists():
            log.info( "Cache does not exist")
            return True

        log.info("Reading cache.")
        cached_profile = self._read_cached_profile()
        return not cached_profile == self.current_profile

