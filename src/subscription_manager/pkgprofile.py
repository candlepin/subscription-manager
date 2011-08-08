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

PROFILE_CACHE_FILE = "/var/lib/rhsm/packages/packages.json"
PACKAGES_RESOURCE = "packages"


def delete_profile_cache():
    if os.path.exists(PROFILE_CACHE_FILE):
        log.info("Deleting profile cache: %s" % PROFILE_CACHE_FILE)
        os.remove(PROFILE_CACHE_FILE)


class ProfileLib(DataLib):
    """
    Another "Lib" object, used by rhsmcertd to update the profile
    periodically.
    """

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

        # Could be None, we'll read the system's current profile later once
        # we're sure we actually need the data.
        self._current_profile = current_profile

    def _get_current_profile(self):
        # If we weren't given a profile, load the current systems packages:
        if not self._current_profile:
            self._current_profile = get_profile('rpm')
        return self._current_profile

    def _set_current_profile(self, value):
        self._current_profile = value

    current_profile = property(_get_current_profile, _set_current_profile)

    def _write_cached_profile(self):
        """
        Write the current profile to disk. Should only be done after
        successfully pushing the profile to the server.
        """
        if not os.access(os.path.dirname(PROFILE_CACHE_FILE), os.R_OK):
            os.makedirs(os.path.dirname(PROFILE_CACHE_FILE))
        try:
            f = open(PROFILE_CACHE_FILE, "w+")
            json.dump(self.current_profile.collect(), f)
            f.close()
        except IOError, e:
            log.error("Unable to write package profile cache to: %s" %
                    PROFILE_CACHE_FILE)
            log.exception(e)

    def _read_cached_profile(self):
        """
        Load the last package profile we sent to the server.
        Returns none if no cache file exists.
        """
        try:
            f = open(PROFILE_CACHE_FILE)
            profile = RPMProfile(from_file=f)
            f.close()
            return profile
        except IOError:
            log.error("Unable to read package profile: %s" % PROFILE_CACHE_FILE)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass

    def _cache_exists(self):
        return os.path.exists(PROFILE_CACHE_FILE)

    def update_check(self, uep, consumer_uuid):
        """
        Check if packages have changed, and push an update if so.
        """

        # If the server doesn't support packages, don't try to send the profile:
        if not uep.supports_resource(PACKAGES_RESOURCE):
            log.info("Server does not support packages, skipping profile upload.")
            return 0

        if self.has_changed():
            log.info("Updating package profile.")
            try:
                uep.updatePackageProfile(consumer_uuid, self.current_profile.collect())
                self._write_cached_profile()
                return 1
            except Exception, e:
                log.error("Error updating package profile:")
                log.exception(e)
                raise Exception(_("Error updating package profile, see /var/log/rhsm/rhsm.log "
                        "for more details."))

            # Return the number of 'updates' we did, assuming updating all
            # packages at once is one update.
        else:
            log.info("Package profile has not changed, skipping upload.")
            return 0  # No updates performed.

    def has_changed(self):
        """
        Check if the current system profile has changed since the last time we
        updated.
        """
        if not self._cache_exists():
            log.info("Cache does not exist")
            return True

        log.info("Reading cache.")
        cached_profile = self._read_cached_profile()
        return not cached_profile == self.current_profile
