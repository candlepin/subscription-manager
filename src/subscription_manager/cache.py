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

import gettext
import logging
import os
import socket
import threading
from M2Crypto import SSL

from rhsm.config import initConfig
import rhsm.connection as connection
from rhsm.profile import get_profile, RPMProfile
import subscription_manager.injection as inj
from rhsm import ourjson as json

_ = gettext.gettext
log = logging.getLogger('rhsm-app.' + __name__)

PACKAGES_RESOURCE = "packages"

cfg = initConfig()


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

    def _sync_with_server(self, uep, consumer_uuid):
        """
        Sync the latest data to/from the server.
        """
        raise NotImplementedError

    def has_changed(self):
        """
        Check if the current system data has changed since the last time we
        updated.
        """
        raise NotImplementedError

    @classmethod
    def delete_cache(cls):
        """ Delete the cache for this collection from disk. """
        if os.path.exists(cls.CACHE_FILE):
            log.info("Deleting cache: %s" % cls.CACHE_FILE)
            os.remove(cls.CACHE_FILE)

    def _cache_exists(self):
        return os.path.exists(self.CACHE_FILE)

    def write_cache(self, debug=True):
        """
        Write the current cache to disk. Should only be done after
        successful communication with the server.

        The update_check method will call this for you if an update was
        required, but the method is exposed as some system data can be
        bundled up with the registration request, after which we need to
        manually write to disk.
        """
        # Logging in this method (when threaded) can cause a segfault, BZ 988861 and 988430
        try:
            if not os.access(os.path.dirname(self.CACHE_FILE), os.R_OK):
                os.makedirs(os.path.dirname(self.CACHE_FILE))
            f = open(self.CACHE_FILE, "w+")
            json.dump(self.to_dict(), f)
            f.close()
            if debug:
                log.debug("Wrote cache: %s" % self.CACHE_FILE)
        except IOError, e:
            if debug:
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
                self._sync_with_server(uep, consumer_uuid)
                self.write_cache()
                # Return the number of 'updates' we did, assuming updating all
                # packages at once is one update.
                return 1
            except connection.RestlibException, re:
                raise re
            except Exception, e:
                log.error("Error updating system data on the server")
                log.exception(e)
                raise Exception(_("Error updating system data on the server, see /var/log/rhsm/rhsm.log "
                        "for more details."))
        else:
            log.info("No changes.")
            return 0  # No updates performed.


class StatusCache(CacheManager):
    """
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """
    def __init__(self):
        self.server_status = None
        self.last_error = None

    def load_status(self, uep, uuid):
        """
        Load status from wherever is appropriate.

        If server is reachable, return it's response
        and cache the results to disk.

        If the server is not reachable, return the latest cache if
        it is still reasonable to use it.

        Returns None if we cannot reach the server, or use the cache.
        """
        try:
            self._sync_with_server(uep, uuid)
            self.write_cache()
            self.last_error = False
            return self.server_status
        except SSL.SSLError, ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Consumer certificate is invalid")
            return None
        except connection.RestlibException, ex:
            # Indicates we may be talking to a very old candlepin server
            # which does not have the necessary API call.
            self.last_error = ex
            return None

        # If we hit a network error, but no cache exists (extremely unlikely)
        # then we are disconnected
        except socket.error, ex:
            log.exception(ex)
            self.last_error = ex
            if not self._cache_exists():
                log.error("Server unreachable, registered, but no cache exists.")
                return None

            log.warn("Unable to reach server, using cached status.")
            return self._read_cache()

        except connection.NetworkException, ex:
            log.exception(ex)
            self.last_error = ex
            if not self._cache_exists():
                log.error("Server unreachable, registered, but no cache exists.")
                raise

            log.warn("Unable to reach server, using cached status.")
            return self._read_cache()
        except connection.ExpiredIdentityCertException, ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Bad identity, unable to connect to server")
            return None
        except connection.AuthenticationException, ex:
            log.error("Could not authenticate with server, check registration status.")
            log.exception(ex)
            self.last_error = ex
            return None

    def to_dict(self):
        return self.server_status

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)

    def _read_cache(self):
        """
        Prefer in memory cache to avoid io.  If it doesn't exist, save
        the disk cache to the in-memory cache to avoid reading again.
        """
        if not self.server_status:
            self.server_status = super(StatusCache, self)._read_cache()
        return self.server_status

    def _cache_exists(self):
        """
        If a cache exists in memory, we have written it to the disk
        No need for unnecessary disk io here.
        """
        if self.server_status:
            return True
        return super(StatusCache, self)._cache_exists()

    def write_cache(self):
        """
        This is threaded because it should never block in runtime.
        Writing to disk means it will be read from memory for the rest of this run.
        """
        threading.Thread(target=super(StatusCache, self).write_cache, args=[False], name="WriteCache%s" % self.__class__.__name__).start()
        log.debug("Started thread to write cache: %s" % self.CACHE_FILE)

    # we override a @classmethod with an instance method in the sub class?
    def delete_cache(self):
        super(StatusCache, self).delete_cache()
        self.server_status = None


class EntitlementStatusCache(StatusCache):
    """
    Manages the system cache of entitlement status from the server.
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/entitlement_status.json"

    def _sync_with_server(self, uep, uuid):
        self.server_status = uep.getCompliance(uuid)


class ProductStatusCache(StatusCache):
    """
    Manages the system cache of installed product valid date ranges.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/product_status.json"

    def _sync_with_server(self, uep, uuid):
        consumer_data = uep.getConsumer(uuid)

        if 'installedProducts' not in consumer_data:
            log.warn("Server does not support product date ranges.")
        else:
            self.server_status = consumer_data['installedProducts']



class OverrideStatusCache(StatusCache):
    """
    Manages the cache of yum repo overrides set on the server.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/content_overrides.json"

    def _sync_with_server(self, uep, consumer_uuid):
        self.server_status = uep.getContentOverrides(consumer_uuid)



# this is injected normally
class ProfileManager(CacheManager):
    """
    Manages the profile of packages installed on this system.
    """
    CACHE_FILE = "/var/lib/rhsm/packages/packages.json"

    def __init__(self, current_profile=None):

        # Could be None, we'll read the system's current profile later once
        # we're sure we actually need the data.
        self._current_profile = current_profile
        self._report_package_profile = cfg.get_int('rhsm', 'report_package_profile')

    # give tests a chance to use something other than RPMProfile
    def _get_profile(self, profile_type):
        return get_profile(profile_type)

    def _get_current_profile(self):
        # If we weren't given a profile, load the current systems packages:
        if not self._current_profile:
            self._current_profile = self._get_profile('rpm')
        return self._current_profile

    def _set_current_profile(self, value):
        self._current_profile = value

    def _set_report_package_profile(self, value):
        self._report_package_profile = value

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

        if not self._report_package_profile:
            log.info("Skipping package profile upload due to report_package_profile setting.")
            return 0

        return CacheManager.update_check(self, uep, consumer_uuid, force)

    def has_changed(self):
        if not self._cache_exists():
            log.info("Cache does not exist")
            return True

        cached_profile = self._read_cache()
        return not cached_profile == self.current_profile

    def _sync_with_server(self, uep, consumer_uuid):
        uep.updatePackageProfile(consumer_uuid,
                self.current_profile.collect())


class InstalledProductsManager(CacheManager):
    """
    Manages the cache of the products installed on this system, and what we
    last sent to the server.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/installed_products.json"

    def __init__(self):
        self._installed = None

    def _get_installed(self):
        if self._installed:
            return self._installed

        self.product_dir = product_dir
        if not product_dir:
            self.product_dir = inj.require(inj.PROD_DIR)

        self._setup_installed()
        return self._installed

    def _set_installed(self, value):
        self._installed = value

    installed = property(_get_installed, _set_installed)

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

        self._setup_installed()

        if len(cached.keys()) != len(self.installed.keys()):
            return True

        if cached != self.installed:
            return True
        return False

    def _setup_installed(self):
        """
        Format installed product data to match the cache
        and what the server can use.
        """
        self.installed = {}
        for prod_cert in self.product_dir.list():
            prod = prod_cert.products[0]
            self.installed[prod.id] = {'productId': prod.id,
                    'productName': prod.name,
                    'version': prod.version,
                    'arch': ','.join(prod.architectures)
                    }

    def format_for_server(self):
        """
        Convert the format we store in this object (which is a little
        easier to work with) into the format the server expects for the
        consumer.
        """
        self._setup_installed()
        final = [val for (key, val) in self.installed.items()]
        return final

    def _sync_with_server(self, uep, consumer_uuid):
        uep.updateConsumer(consumer_uuid,
                installed_products=self.format_for_server())


class PoolTypeCache(object):

    def __init__(self):
        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.ent_dir = inj.require(inj.ENT_DIR)
        self.pooltype_map = {}
        self.update()

    def get(self, pool_id):
        return self.pooltype_map.get(pool_id, '')

    def update(self):
        if self.requires_update():
            self._do_update()

    def requires_update(self):
        attached_pool_ids = set([ent.pool.id for ent in self.ent_dir.list()
            if ent.pool and ent.pool.id])
        missing_types = attached_pool_ids - set(self.pooltype_map)
        return bool(missing_types)

    def _do_update(self):
        result = {}
        if self.identity.is_valid():
            cp = self.cp_provider.get_consumer_auth_cp()
            entitlement_list = []
            try:
                entitlement_list = cp.getEntitlementList(self.identity.uuid)
            except Exception, e:
                # In this case, return an empty map.  We just won't populate the field
                log.debug('Problem attmepting to get entitlements from the server')
                log.debug(e)

            for ent in entitlement_list:
                pool = PoolWrapper(ent.get('pool', {}))
                pool_type = pool.get_pool_type()
                result[pool.get_id()] = pool_type

        self.pooltype_map.update(result)

    def update_from_pools(self, pool_map):
        # pool_map maps pool ids to pool json
        for pool_id in pool_map:
            self.pooltype_map[pool_id] = PoolWrapper(pool_map[pool_id]).get_pool_type()

    def clear(self):
        self.pooltype_map = {}
