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

"""
Module for managing the cached information about a system.

Classes here track various information last sent to the server, compare
this with the current state, and perform an update on the server if
necessary.
"""

import logging
import os
import simplejson as json
import gettext
_ = gettext.gettext

from rhsm.profile import get_profile, RPMProfile
from subscription_manager.certlib import DataLib, ConsumerIdentity
from subscription_manager.certdirectory import ProductDirectory

log = logging.getLogger('rhsm-app.' + __name__)

PACKAGES_RESOURCE = "packages"


class PackageProfileLib(DataLib):
    """
    Another "Lib" object, used by rhsmcertd to update the profile
    periodically.
    """
    def _do_update(self):
        profile_mgr = ProfileManager()
        try:
            consumer = ConsumerIdentity.read()
        except IOError:
            return 0
        consumer_uuid = consumer.getConsumerId()
        return profile_mgr.update_check(self.uep, consumer_uuid)


class InstalledProductsLib(DataLib):
    """
    Another "Lib" object, used by rhsmcertd to update the installed
    products on this system periodically.
    """
    def _do_update(self):
        mgr = InstalledProductsManager()
        try:
            consumer = ConsumerIdentity.read()
        except IOError:
            return 0
        consumer_uuid = consumer.getConsumerId()
        return mgr.update_check(self.uep, consumer_uuid)


class CacheManager(object):
    """
    Parent class used for common logic in a number of collections
    where we need to push some consumer JSON up to the server,
    maintain a local cache of that data, and check if anything has
    changed on subsequent runs.
    """

    # Fields the subclass must override:
    CACHE_FILE = None

    def to_dict(self):
        """
        Returns the data for this collection as a dict to be serialized
        as JSON.
        """
        raise NotImplementedError

    def _load_data(self, open_file):
        """
        Load the data in whatever format the sub-class uses from
        an already opened file descriptor.
        """
        raise NotImplementedError

    def _update_server(self, uep, consumer_uuid):
        """
        Update the server with latest data.

        This generally completely replaced everything the server had
        stored previously.
        """
        raise NotImplementedError

    def has_changed(self):
        """
        Check if the current system data has changed since the last time we
        updated.
        """
        raise NotImplementedError

    @classmethod
    def delete_cache(self):
        """ Delete the cache for this collection from disk. """
        if os.path.exists(self.CACHE_FILE):
            log.info("Deleting cache: %s" % self.CACHE_FILE)
            os.remove(self.CACHE_FILE)

    def _cache_exists(self):
        return os.path.exists(self.CACHE_FILE)

    def write_cache(self):
        """
        Write the current cache to disk. Should only be done after
        successfully pushing to the server.

        The update_check method will call this for you if an update was
        required, but the method is exposed as some system data can be
        bundled up with the registration request, after which we need to
        manually write to disk.
        """
        try:
            if not os.access(os.path.dirname(self.CACHE_FILE), os.R_OK):
                os.makedirs(os.path.dirname(self.CACHE_FILE))
            f = open(self.CACHE_FILE, "w+")
            json.dump(self.to_dict(), f)
            f.close()
        except IOError, e:
            log.error("Unable to write cache: %s" %
                    self.CACHE_FILE)
            log.exception(e)

    def _read_cache(self):
        """
        Load the last data we sent to the server.
        Returns none if no cache file exists.
        """
        try:
            f = open(self.CACHE_FILE)
            data = self._load_data(f)
            f.close()
            return data
        except IOError:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass

    def update_check(self, uep, consumer_uuid, force=False):
        """
        Check if data has changed, and push an update if so.
        """
        log.info("Checking current system info against cache: %s" % self.CACHE_FILE)
        if self.has_changed() or force:
            log.info("System data has changed, updating server.")
            try:
                self._update_server(uep, consumer_uuid)
                self.write_cache()
                # Return the number of 'updates' we did, assuming updating all
                # packages at once is one update.
                return 1
            except Exception, e:
                log.error("Error updating system data")
                log.exception(e)
                raise Exception(_("Error updating system data, see /var/log/rhsm/rhsm.log "
                        "for more details."))
        else:
            log.info("No changes.")
            return 0  # No updates performed.


class ProfileManager(CacheManager):
    """
    Manages the profile of packages installed on this system.
    """
    CACHE_FILE = "/var/lib/rhsm/packages/packages.json"

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

    def to_dict(self):
        return self.current_profile.collect()

    def _load_data(self, open_file):
        return RPMProfile(from_file=open_file)

    def update_check(self, uep, consumer_uuid, force=False):
        """
        Check if packages have changed, and push an update if so.
        """

        # If the server doesn't support packages, don't try to send the profile:
        if not uep.supports_resource(PACKAGES_RESOURCE):
            log.info("Server does not support packages, skipping profile upload.")
            return 0

        return CacheManager.update_check(self, uep, consumer_uuid, force)

    def has_changed(self):
        if not self._cache_exists():
            log.info("Cache does not exist")
            return True

        cached_profile = self._read_cache()
        return not cached_profile == self.current_profile

    def _update_server(self, uep, consumer_uuid):
        uep.updatePackageProfile(consumer_uuid,
                self.current_profile.collect())


class InstalledProductsManager(CacheManager):
    """
    Manages the cache of the products installed on this system, and what we
    last sent to the server.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/installed_products.json"

    def __init__(self, product_dir=None):

        if not product_dir:
            product_dir = ProductDirectory()

        self.installed = {}
        for prod_cert in product_dir.list():
            prod = prod_cert.getProduct()
            self.installed[prod.getHash()] = prod.getName()

    def to_dict(self):
        return self.installed

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)

    def has_changed(self):
        if not self._cache_exists():
            log.info("Cache does not exist")
            return True

        cached = self._read_cache()

        if len(cached.keys()) != len(self.installed.keys()):
            return True

        for key in self.installed.keys():
            if key not in cached:
                return True
            if self.installed[key] != cached[key]:
                return True

        return False

    def format_for_server(self):
        """
        Convert the format we store in this object (which is a little
        easier to work with) into the format the server expects for the
        consumer.
        """
        final = []
        for key in self.installed.keys():
            final.append({
                    'productId': key,
                    'productName': self.installed[key]
            })
        return final

    def _update_server(self, uep, consumer_uuid):
        uep.updateConsumer(consumer_uuid,
                installed_products=self.format_for_server())
