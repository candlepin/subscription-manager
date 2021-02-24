from __future__ import print_function, division, absolute_import

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
import socket
import threading
import time
from rhsm.https import ssl

from rhsm.config import get_config_parser
import rhsm.connection as connection
from rhsm.profile import get_profile
import subscription_manager.injection as inj
from subscription_manager.jsonwrapper import PoolWrapper
from rhsm import ourjson as json
from subscription_manager.isodate import parse_date
from subscription_manager.utils import get_supported_resources
from syspurpose.files import post_process_received_data

from rhsmlib.services import config, syspurpose

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

PACKAGES_RESOURCE = "packages"

conf = config.Config(get_config_parser())


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

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
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
            log.debug("Deleting cache: %s" % cls.CACHE_FILE)
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
            json.dump(self.to_dict(), f, default=json.encode)
            f.close()
            if debug:
                log.debug("Wrote cache: %s" % self.CACHE_FILE)
        except IOError as err:
            log.error("Unable to write cache: %s" % self.CACHE_FILE)
            log.exception(err)

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
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass

    def read_cache_only(self):
        """
        Try to read only cached data. When cache does not exist,
        then None is returned.
        """
        if self._cache_exists():
            return self._read_cache()
        else:
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return None

    def update_check(self, uep, consumer_uuid, force=False):
        """
        Check if data has changed, and push an update if so.
        """

        # The package_upload.py yum plugin from katello-agent will
        # end up calling this with consumer_uuid=None if the system
        # is unregistered.
        if not consumer_uuid:
            msg = _("consumer_uuid=%s is not a valid consumer_uuid. "
                    "Not attempting to sync %s cache with server.") % \
                (consumer_uuid, self.__class__.__name__)
            log.debug(msg)

            # Raising an exception here would be better, but that is just
            # going to cause the package_upload plugin to spam yum
            # output for unregistered systems, and can only be resolved by
            # registering to rhsm.
            return 0

        log.debug("Checking current system info against cache: %s" % self.CACHE_FILE)
        if self.has_changed() or force:
            log.debug("System data has changed, updating server.")
            try:
                self._sync_with_server(uep, consumer_uuid)
                self.write_cache()
                # Return the number of 'updates' we did, assuming updating all
                # packages at once is one update.
                return 1
            except connection.RestlibException as re:
                raise re
            except Exception as e:
                log.error("Error updating system data on the server")
                log.exception(e)
                raise Exception(_("Error updating system data on the server, see /var/log/rhsm/rhsm.log "
                                  "for more details."))
        else:
            log.debug("No changes.")
            return 0  # No updates performed.


class StatusCache(CacheManager):
    """
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """
    def __init__(self):
        self.server_status = None
        self.last_error = None

    def load_status(self, uep, uuid, on_date=None):
        """
        Load status from wherever is appropriate.

        If server is reachable, return it's response
        and cache the results to disk.

        If the server is not reachable, return the latest cache if
        it is still reasonable to use it.

        Returns None if we cannot reach the server, or use the cache.
        """
        try:
            self._sync_with_server(uep, uuid, on_date)
            self.write_cache()
            self.last_error = False
            return self.server_status
        except ssl.SSLError as ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Consumer certificate is invalid")
            return None
        except connection.AuthenticationException as ex:
            log.error("Could not authenticate with server, check registration status.")
            log.exception(ex)
            self.last_error = ex
            return None
        except connection.ExpiredIdentityCertException as ex:
            log.exception(ex)
            self.last_error = ex
            log.error("Bad identity, unable to connect to server")
            return None
        # all of the abover are subclasses of ConnectionException that
        # get handled first
        except (connection.ConnectionException, connection.RateLimitExceededException,
                socket.error, connection.ProxyException) as ex:
            log.error(ex)
            self.last_error = ex
            if not self._cache_exists():
                log.error("Server unreachable, registered, but no cache exists.")
                return None

            log.warn("Unable to reach server, using cached status.")
            return self._read_cache()
        except connection.RestlibException as ex:
            # Indicates we may be talking to a very old candlepin server
            # which does not have the necessary API call.
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
        if self.server_status is None:
            log.debug('Trying to read status from %s file' % self.CACHE_FILE)
            self.server_status = super(StatusCache, self)._read_cache()
        else:
            log.debug('Reading status from in-memory cache of %s file' % self.CACHE_FILE)
        return self.server_status

    def _cache_exists(self):
        """
        If a cache exists in memory, we have written it to the disk
        No need for unnecessary disk io here.
        """
        if self.server_status is not None:
            return True
        return super(StatusCache, self)._cache_exists()

    def read_status(self, uep, uuid, on_date=None):
        """
        Return status, from cache if it exists, otherwise load_status
        and write cache and return it.

        If load_status fails, we return it's return value. For
        a fail with a cache, it will be the cached values. Otherwise
        it will be None.

        Methods calling this should handle the None, likely by
        using a default value instead of calling it again. If there is
        no default, the None likely indicates an error needs to be raised.
        """

        if self.server_status is None:
            self.server_status = self.load_status(uep, uuid, on_date)
        else:
            log.debug('Reading status from in-memory cache of %s file' % self.CACHE_FILE)
        return self.server_status

    def write_cache(self):
        """
        This is threaded because it should never block in runtime.
        Writing to disk means it will be read from memory for the rest of this run.
        """
        threading.Thread(target=super(StatusCache, self).write_cache,
                         args=[True],
                         name="WriteCache%sThread" % self.__class__.__name__).start()
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

    def _sync_with_server(self, uep, uuid, on_date=None, *args, **kwargs):
        self.server_status = uep.getCompliance(uuid, on_date)


class SyspurposeComplianceStatusCache(StatusCache):
    """
    Manages the system cache of system purpose compliance status from the server.
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/syspurpose_compliance_status.json"

    def _sync_with_server(self, uep, uuid, on_date=None, *args, **kwargs):
        self.syspurpose_service = syspurpose.Syspurpose(uep)
        self.server_status = self.syspurpose_service.get_syspurpose_status(on_date)

    def write_cache(self):
        if self.server_status is not None and self.server_status['status'] != 'unknown':
            super(SyspurposeComplianceStatusCache, self).write_cache()

    def get_overall_status(self):
        if self.server_status is not None:
            return self.syspurpose_service.get_overall_status(self.server_status['status'])
        else:
            return self.syspurpose_service.get_overall_status('unknown')

    def get_overall_status_code(self):
        if self.server_status is not None:
            return self.server_status
        else:
            return 'unknown'

    def get_status_reasons(self):
        if self.server_status is not None and 'reasons' in self.server_status:
            return self.server_status['reasons']
        else:
            return None


class ProductStatusCache(StatusCache):
    """
    Manages the system cache of installed product valid date ranges.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/product_status.json"

    def _sync_with_server(self, uep, uuid, *args, **kwargs):
        consumer_data = uep.getConsumer(uuid)

        if 'installedProducts' not in consumer_data:
            log.warning("Server does not support product date ranges.")
        else:
            self.server_status = consumer_data['installedProducts']


class OverrideStatusCache(StatusCache):
    """
    Manages the cache of yum repo overrides set on the server.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/content_overrides.json"

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        self.server_status = uep.getContentOverrides(consumer_uuid)


class ReleaseStatusCache(StatusCache):
    """
    Manages the cache of the consumers 'release' setting applied to yum repos.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/releasever.json"

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        def get_release(uuid):

            # To mimic connection problems you can raise required exception:
            # raise connection.RemoteServerException(500, "GET", "/release")
            return uep.getRelease(uuid)

        self.server_status = get_release(consumer_uuid)

    # our read_status could check for "full_refresh_on_yum", since
    # we are yum specific, and not triggered till late.


# this is injected normally
class ProfileManager(CacheManager):
    """
    Manages profile of installed packages, enabled repositories and plugins
    """

    CACHE_FILE = "/var/lib/rhsm/cache/profile.json"

    def __init__(self):
        # Could be None, we'll read the system's current profile later once
        # we're sure we actually need the data.
        self._current_profile = None
        self.report_package_profile = self.profile_reporting_enabled()

    def profile_reporting_enabled(self):
        # If profile reporting is disabled from the environment, that overrides the setting in the conf file
        # If the environment variable is 0, defer to the setting in the conf file; likewise if the environment
        # variable is completely unset.
        if 'SUBMAN_DISABLE_PROFILE_REPORTING' in os.environ and \
            os.environ['SUBMAN_DISABLE_PROFILE_REPORTING'].lower() in ['true', '1', 'yes', 'on']:
            return False
        return conf['rhsm'].get_int('report_package_profile') == 1

    # give tests a chance to use something other than RPMProfile
    def _get_profile(self, profile_type):
        return get_profile(profile_type)

    @staticmethod
    def _assembly_profile(rpm_profile, enabled_repos_profile, module_profile):
        combined_profile = {
            'rpm': rpm_profile,
            'enabled_repos': enabled_repos_profile,
            'modulemd': module_profile
        }
        return combined_profile

    @property
    def current_profile(self):
        if not self._current_profile:
            rpm_profile = get_profile('rpm').collect()
            enabled_repos = get_profile('enabled_repos').collect()
            module_profile = get_profile('modulemd').collect()
            combined_profile = self._assembly_profile(rpm_profile, enabled_repos, module_profile)
            self._current_profile = combined_profile
        return self._current_profile

    @current_profile.setter
    def current_profile(self, new_profile):
        self._current_profile = new_profile

    def to_dict(self):
        return self.current_profile

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)

    def update_check(self, uep, consumer_uuid, force=False):
        """
        Check if packages have changed, and push an update if so.
        """

        # If the server doesn't support packages, don't try to send the profile:
        supported_resources = get_supported_resources()
        if PACKAGES_RESOURCE not in supported_resources:
            log.warning("Server does not support packages, skipping profile upload.")
            return 0

        if force or self.report_package_profile:
            return CacheManager.update_check(self, uep, consumer_uuid, force)
        elif not self.report_package_profile:
            log.warning("Skipping package profile upload due to report_package_profile setting.")
            return 0
        else:
            return 0

    def has_changed(self):
        if not self._cache_exists():
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return True

        cached_profile = self._read_cache()
        return not cached_profile == self.current_profile

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        """
        This method has to be able to sync combined profile, when server supports this functionality
        and it also has to be able to send only profile containing list of installed RPMs.
        """
        combined_profile = self.current_profile
        if uep.has_capability("combined_reporting"):
            _combined_profile = [
                {
                    "content_type": "rpm",
                    "profile": combined_profile["rpm"]
                },
                {
                    "content_type": "enabled_repos",
                    "profile": combined_profile["enabled_repos"]
                },
                {
                    "content_type": "modulemd",
                    "profile": combined_profile["modulemd"]
                },
            ]
            uep.updateCombinedProfile(
                consumer_uuid,
                _combined_profile
            )
        else:
            uep.updatePackageProfile(
                consumer_uuid,
                combined_profile["rpm"]
            )


class InstalledProductsManager(CacheManager):
    """
    Manages the cache of the products installed on this system, and what we
    last sent to the server.
    """
    CACHE_FILE = "/var/lib/rhsm/cache/installed_products.json"

    def __init__(self):
        self._installed = None
        self.tags = None

        self.product_dir = inj.require(inj.PROD_DIR)

        self._setup_installed()

    def _get_installed(self):
        if self._installed:
            return self._installed

        self._setup_installed()

        return self._installed

    def _set_installed(self, value):
        self._installed = value

    installed = property(_get_installed, _set_installed)

    def to_dict(self):
        return {"products": self.installed, "tags": self.tags}

    def _load_data(self, open_file):
        json_str = open_file.read()
        return json.loads(json_str)

    def has_changed(self):
        if not self._cache_exists():
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return True

        cached = self._read_cache()
        try:
            products = cached['products']
            tags = set(cached['tags'])
        except KeyError:
            # Handle older cache formats
            return True

        self._setup_installed()

        if len(list(products.keys())) != len(list(self.installed.keys())):
            return True

        if products != self.installed:
            return True

        if tags != self.tags:
            return True

        return False

    def _setup_installed(self):
        """
        Format installed product data to match the cache
        and what the server can use.
        """
        self._installed = {}
        self.tags = set()
        for prod_cert in self.product_dir.list():
            prod = prod_cert.products[0]
            self.tags |= set(prod.provided_tags)
            self._installed[prod.id] = {'productId': prod.id,
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
        final = [val for (key, val) in list(self.installed.items())]
        return final

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        uep.updateConsumer(consumer_uuid,
                installed_products=self.format_for_server(),
                content_tags=self.tags)


class PoolStatusCache(StatusCache):
    """
    Manages the system cache of pools
    """
    CACHE_FILE = "/var/lib/rhsm/cache/pool_status.json"

    def _sync_with_server(self, uep, uuid, *args, **kwargs):
        self.server_status = uep.getEntitlementList(uuid)


class PoolTypeCache(object):
    """
    Cache type of pool
    """

    def __init__(self):
        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.ent_dir = inj.require(inj.ENT_DIR)
        self.pool_cache = inj.require(inj.POOL_STATUS_CACHE)
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
            self.pool_cache.load_status(self.cp_provider.get_consumer_auth_cp(),
                                        self.identity.uuid)
            entitlement_list = self.pool_cache.server_status

            if entitlement_list is not None:
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


class ContentAccessCache(object):
    CACHE_FILE = "/var/lib/rhsm/cache/content_access.json"

    def __init__(self):
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.identity = inj.require(inj.IDENTITY)

    def _query_for_update(self, if_modified_since=None):
        uep = self.cp_provider.get_consumer_auth_cp()
        try:
            response = uep.getAccessibleContent(self.identity.uuid, if_modified_since=if_modified_since)
        except connection.RestlibException as err:
            log.warning("Unable to query for content access updates: %s", err)
            return None
        if response is None or "contentListing" not in response:
            return None
        else:
            self._update_cache(response)
            return response

    def exists(self):
        return os.path.exists(self.CACHE_FILE)

    def remove(self):
        return os.remove(self.CACHE_FILE)

    def check_for_update(self):
        if self.exists():
            try:
                data = json.loads(self.read())
                last_update = parse_date(data["lastUpdate"])
            except (ValueError, KeyError) as err:
                log.debug("Cache file {file} is corrupted: {err}".format(
                    file=self.CACHE_FILE,
                    err=err
                ))
                last_update = None
        else:
            last_update = None
        return self._query_for_update(if_modified_since=last_update)

    @staticmethod
    def update_cert(cert, data):
        if data is None:
            return
        if data["contentListing"] is None or str(cert.serial) not in data["contentListing"]:
            log.warning("Cert serial %s not contained in content listing; not updating it." % cert.serial)
            return
        with open(cert.path, "w") as output:
            updated_cert = "".join(data["contentListing"][str(cert.serial)])
            log.debug("Updating certificate %s with new content" % cert.serial)
            output.write(updated_cert)

    def _update_cache(self, data):
        log.debug("Updating content access cache")
        with open(self.CACHE_FILE, "w") as cache:
            cache.write(json.dumps(data))

    def read(self):
        with open(self.CACHE_FILE, "r") as cache:
            return cache.read()


class RhsmIconCache(CacheManager):
    """
    Cache to keep track of last status returned by the StatusCache.
    This cache is specifically used to ensure RHSM icon pops up only
    when the status changes.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/rhsm_icon.json"

    def __init__(self, data=None):
        self.data = data or {}

    def to_dict(self):
        return self.data

    def _load_data(self, open_file):
        try:
            self.data = json.loads(open_file.read()) or {}
            return self.data
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass


class WrittenOverrideCache(CacheManager):
    """
    Cache to keep track of the overrides used last time the a redhat.repo
    was written.  Doesn't track server status, we've got another cache for
    that.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/written_overrides.json"

    def __init__(self, overrides=None):
        self.overrides = overrides or {}

    def to_dict(self):
        return self.overrides

    def _load_data(self, open_file):
        try:
            self.overrides = json.loads(open_file.read()) or {}
            return self.overrides
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass


class ConsumerCache(CacheManager):
    """
    Base class for caching data that gets automatically obsoleted, when consumer uuid
    is changed (when system is unregistered or system is force register). This cache
    is intended for caching information that we try to get from server. This cache should
    avoid calling REST API with same arguments and getting same result.
    """

    # File, when the cache will be saved
    CACHE_FILE = None

    # Default value could be dictionary, list or anything else
    DEFAULT_VALUE = {}

    # Some data should have some timeout of validity, because data can be changed over time
    # on the server, because server could be updated and it can start provide new functionality.
    # E.g. supported resources or available capabilities. Value of timeout is in seconds.
    TIMEOUT = None

    def __init__(self, data=None):
        self.data = data or {}

    def to_dict(self):
        return self.data

    def _load_data(self, open_file):
        try:
            self.data = json.loads(open_file.read()) or {}
            return self.data
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # Ignore json file parse error
            pass

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        """
        This method has to be implemented in sub-classes of this class
        :param uep: object representing connection to candlepin server
        :param consumer_uuid: consumer UUID object
        :param args: other position arguments
        :param kwargs: other keyed arguments
        :return: Subclass method has to return the content that was returned by candlepin server.
        """
        raise NotImplementedError

    def _is_cache_obsoleted(self, uep, identity, *args, **kwargs):
        """
        Another method for checking if cached file is obsoleted
        :param args: positional arguments
        :param kwargs: keyed arguments
        :return: True if the cache is obsoleted; otherwise return False
        """
        return False

    def read_data(self, uep=None, identity=None):
        """
        This function tries to get data from cache or server
        :param uep: connection to candlepin server
        :param identity: current identity of registered system
        :return: information about current owner
        """

        current_data = self.DEFAULT_VALUE

        if identity is None:
            identity = inj.require(inj.IDENTITY)

        # When identity is not known, then system is not registered and
        # data are obsoleted
        if identity.uuid is None:
            self.delete_cache()
            return current_data

        # Try to use class specific test if the cache file is obsoleted
        cache_file_obsoleted = self._is_cache_obsoleted(uep, identity)

        # When timeout for cache is defined, then check if the cache file is not
        # too old. In that case content of the cache file will be overwritten with
        # new content from the server.
        if self.TIMEOUT is not None:
            if os.path.exists(self.CACHE_FILE):
                mod_time = os.path.getmtime(self.CACHE_FILE)
                cur_time = time.time()
                diff = cur_time - mod_time
                if diff > self.TIMEOUT:
                    log.debug('Validity of cache file %s timed out (%d)' % (self.CACHE_FILE, self.TIMEOUT))
                    cache_file_obsoleted = True

        if cache_file_obsoleted is False:
            # Try to read data from cache first
            log.debug('Trying to read %s from cache file %s' % (self.__class__.__name__, self.CACHE_FILE))
            data = self.read_cache_only()
            if data is not None:
                if identity.uuid in data:
                    current_data = data[identity.uuid]
                else:
                    log.debug("Identity of system has changed. The cache file: %s is obsolete" % self.CACHE_FILE)

        # When valid data are not in cached, then try to load it from candlepin server
        if len(current_data) != 0:
            log.debug('Data loaded from cache file: %s' % self.CACHE_FILE)
        else:
            if uep is None:
                cp_provider = inj.require(inj.CP_PROVIDER)
                uep = cp_provider.get_consumer_auth_cp()

            log.debug('Getting data from server for %s' % self.__class__)
            try:
                current_data = self._sync_with_server(uep=uep, consumer_uuid=identity.uuid)
            except connection.RestlibException as rest_err:
                log.warning("Unable to get data for %s using REST API: %s" % (self.__class__, rest_err))
                log.debug("Deleting cache file: %s", self.CACHE_FILE)
                self.delete_cache()
                # Raise exception again to be able to display error message in exception
                raise rest_err
            else:
                # Write data to cache
                data = {identity.uuid: current_data}
                self.data = data
                self.write_cache(debug=True)

        return current_data


class SyspurposeValidFieldsCache(ConsumerCache):
    """
    Cache the valid syspurpose fields for current owner
    """

    CACHE_FILE = "/var/lib/rhsm/cache/valid_fields.json"

    def __init__(self, data=None):
        super(SyspurposeValidFieldsCache, self).__init__(data=data)

    def _sync_with_server(self, uep, *args, **kwargs):
        cache = inj.require(inj.CURRENT_OWNER_CACHE)
        owner = cache.read_data(uep)
        if 'key' in owner:
            data = uep.getOwnerSyspurposeValidFields(owner['key'])
            return post_process_received_data(data)
        else:
            return self.DEFAULT_VALUE


class CurrentOwnerCache(ConsumerCache):
    """
    Cache information about current owner (organization)
    """

    # Grab the current owner at most once per day
    TIMEOUT = 60 * 60 * 24

    CACHE_FILE = "/var/lib/rhsm/cache/current_owner.json"

    def __init__(self, data=None):
        super(CurrentOwnerCache, self).__init__(data=data)

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        return uep.getOwner(consumer_uuid)

    def _is_cache_obsoleted(self, uep, identity, *args, **kwargs):
        """
        We don't know if the cache is valid until we get valid response
        :param uep: object representing connection to candlepin server
        :param identity: consumer identity
        :param args: other arguments
        :param kwargs: other keyed arguments
        :return: True, when cache is obsoleted or validity of cache is unknown.
        """
        if uep is None:
            cp_provider = inj.require(inj.CP_PROVIDER)
            uep = cp_provider.get_consumer_auth_cp()
        if hasattr(uep.conn, 'is_consumer_cert_key_valid') and uep.conn.is_consumer_cert_key_valid is True:
            return False
        else:
            return True


class ContentAccessModeCache(ConsumerCache):
    """
    Cache information about current owner (organization), specifically, the content access mode.
    This value is used independently.
    """

    # Grab the current owner (and hence the content_access_mode of that owner) at most, once per
    # 4 hours
    TIMEOUT = 60 * 60 * 4

    CACHE_FILE = "/var/lib/rhsm/cache/content_access_mode.json"

    def __init__(self, data=None):
        super(ContentAccessModeCache, self).__init__(data=data)

    def _sync_with_server(self, uep, consumer_uuid, *args, **kwargs):
        try:
            current_owner = uep.getOwner(consumer_uuid)
        except Exception:
            log.debug("Error checking for content access mode,"
                      "defaulting to assuming not in Simple Content Access mode")
        else:
            if "contentAccessMode" in current_owner:
                return current_owner["contentAccessMode"]
            else:
                log.debug("The owner returned from the server did not contain a "
                          "'content_access_mode'. Perhaps the connected Entitlement Server doesn't"
                          "support 'content_access_mode'?")
        return "unknown"

    def _is_cache_obsoleted(self, uep, identity, *args, **kwargs):
        """
        We don't know if the cache is valid until we get valid response
        :param uep: object representing connection to candlepin server
        :param identity: consumer identity
        :param args: other arguments
        :param kwargs: other keyed arguments
        :return: True, when cache is obsoleted or validity of cache is unknown.
        """
        if uep is None:
            cp_provider = inj.require(inj.CP_PROVIDER)
            uep = cp_provider.get_consumer_auth_cp()
        if hasattr(uep.conn, 'is_consumer_cert_key_valid') and uep.conn.is_consumer_cert_key_valid is True:
            return False
        else:
            return True


class SupportedResourcesCache(ConsumerCache):
    """
    Cache supported resources of candlepin server for current identity
    """

    CACHE_FILE = "/var/lib/rhsm/cache/supported_resources.json"

    DEFAULT_VALUE = []

    # We will try to get new list of supported resources at leas once a day
    TIMEOUT = 60 * 60 * 24

    def __init__(self, data=None):
        super(SupportedResourcesCache, self).__init__(data=data)

    def _sync_with_server(self, uep, *args, **kwargs):
        return uep.get_supported_resources()


class AvailableEntitlementsCache(CacheManager):
    """
    Cache of available entitlements
    """

    # Coefficient used for computing timeout of cache
    BETA = 2.0
    # Lower bound of cache timeout (seconds)
    LBOUND = 5.0
    # Upper bound of cache timeout (seconds)
    UBOUND = 10.0

    CACHE_FILE = "/var/lib/rhsm/cache/available_entitlements.json"

    def __init__(self, available_entitlements=None):
        self.available_entitlements = available_entitlements or {}

    def to_dict(self):
        return self.available_entitlements

    def timeout(self):
        """
        Compute timeout of cache. Computation of timeout is based on SRT (smoothed response time)
        of connection to candlepin server. This algorithm is inspired by retransmission timeout used
        by TCP connection (see: RFC 793)
        """
        uep = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()

        if uep.conn.smoothed_rt is not None:
            smoothed_rt = uep.conn.smoothed_rt
        else:
            smoothed_rt = 0.0
        return min(self.UBOUND, max(self.LBOUND, self.BETA * smoothed_rt))

    def get_not_obsolete_data(self, identity, filter_options):
        """
        Try to get not obsolete cached data
        :param identity: identity with UUID
        :param filter_options: dictionary with filter option
        :return: When data are not obsoleted, then return cached dictionary of available entitlements.
        Otherwise return empty dictionary.
        """
        data = self.read_cache_only()
        available_pools = {}
        if data is not None:
            if identity.uuid in data:
                cached_data = data[identity.uuid]
                if cached_data['filter_options'] == filter_options:
                    log.debug('timeout: %s, current time: %s' % (cached_data['timeout'], time.time()))
                    if cached_data['timeout'] > time.time():
                        log.debug('Using cached list of available entitlements')
                        available_pools = cached_data['pools']
                    else:
                        log.debug('Cache of available entitlements timed-out')
                else:
                    log.debug('Cache of available entitlements does not contain given filter options')
        return available_pools

    def _load_data(self, open_file):
        try:
            self.available_entitlements = json.loads(open_file.read()) or {}
            return self.available_entitlements
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # Ignore json file parse error
            pass
