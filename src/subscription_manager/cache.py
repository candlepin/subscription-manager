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
import base64
import datetime
import logging
import os
import socket
import threading
import time
from typing import Dict, TextIO, Literal, Optional, List, Any, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from rhsm.certificate2 import EntitlementCertificate, Product
    from rhsm.connection import UEPConnection
    from subscription_manager.certdirectory import ProductDirectory, EntitlementDirectory
    from subscription_manager.cp_provider import CPProvider
    from subscription_manager.identity import Identity

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


class CacheManager:
    """
    Parent class used for common logic in a number of collections
    where we need to push some consumer JSON up to the server,
    maintain a local cache of that data, and check if anything has
    changed on subsequent runs.
    """

    # Fields the subclass must override:
    CACHE_FILE: str = None

    def to_dict(self) -> Dict:
        """
        Returns the data for this collection as a dict to be serialized
        as JSON.
        """
        raise NotImplementedError

    def _load_data(self, open_file: TextIO) -> Optional[Dict]:
        """
        Load the data in whatever format the subclass uses from
        an already opened file descriptor.
        """
        raise NotImplementedError

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        """
        Sync the latest data to/from the server.
        """
        raise NotImplementedError

    def has_changed(self) -> bool:
        """
        Check if the current system data has changed since the last time we updated.
        """
        raise NotImplementedError

    @classmethod
    def delete_cache(cls) -> None:
        """Delete the cache for this collection from disk."""
        if os.path.exists(cls.CACHE_FILE):
            log.debug("Deleting cache: %s" % cls.CACHE_FILE)
            os.remove(cls.CACHE_FILE)

    def _cache_exists(self) -> bool:
        return os.path.exists(self.CACHE_FILE)

    def exists(self) -> bool:
        return self._cache_exists()

    def write_cache(self, debug: bool = True) -> None:
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
            f: TextIO = open(self.CACHE_FILE, "w+")
            json.dump(self.to_dict(), f, default=json.encode)
            f.close()
            if debug:
                log.debug("Wrote cache: %s" % self.CACHE_FILE)
        except IOError as err:
            log.error("Unable to write cache: %s" % self.CACHE_FILE)
            log.exception(err)

    def _read_cache(self) -> Optional[Dict]:
        """
        Load the last data we sent to the server.
        Returns none if no cache file exists.
        """

        try:
            f = open(self.CACHE_FILE)
            data: dict = self._load_data(f)
            f.close()
            return data
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass

    def read_cache_only(self) -> Optional[Dict]:
        """
        Try to read only cached data. When cache does not exist,
        then None is returned.
        """
        if self._cache_exists():
            return self._read_cache()
        else:
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return None

    def update_check(
        self, uep: connection.UEPConnection, consumer_uuid: str, force: bool = False
    ) -> Literal[0, 1]:
        """
        Check if data has changed, and push an update if so.

        :return: 1 if the cache was updated, 0 otherwise.
        """

        # The package_upload.py yum plugin from katello-agent will
        # end up calling this with consumer_uuid=None if the system
        # is unregistered.
        if not consumer_uuid:
            msg = _(
                "consumer_uuid={consumer_uuid} is not a valid consumer_uuid. "
                "Not attempting to sync {class_name} cache with server."
            ).format(consumer_uuid=consumer_uuid, class_name=self.__class__.__name__)
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
            except connection.ProxyException as pe:
                raise pe
            except Exception as e:
                log.error("Error updating system data on the server")
                log.exception(e)
                raise e
        else:
            log.debug("No changes.")
            return 0  # No updates performed.


class StatusCache(CacheManager):
    """
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """

    def __init__(self):
        self.server_status: Optional[Dict] = None
        self.last_error: Optional[Exception] = None

    def load_status(
        self, uep: connection.UEPConnection, uuid: Optional[str], on_date: Optional[datetime.datetime] = None
    ) -> Optional[Dict]:
        """
        Load status from wherever is appropriate.

        If server is reachable, return its response and cache the results to disk.

        If the server is not reachable, return the latest cache if
        it is still reasonable to use it.

        Returns None if we cannot reach the server, or use the cache.
        """
        try:
            # If UUID is None, then we cannot get anything from server
            # and None has to be returned
            if uuid is None:
                return None
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
        # all of the above are subclasses of ConnectionException that
        # get handled first
        except (
            connection.ConnectionException,
            connection.RateLimitExceededException,
            socket.error,
            connection.ProxyException,
        ) as ex:
            log.error(ex)
            self.last_error = ex
            if not self._cache_exists():
                log.error("Server unreachable, registered, but no cache exists.")
                return None

            log.warning("Unable to reach server, using cached status.")
            return self._read_cache()
        except connection.RestlibException as ex:
            # Indicates we may be talking to a very old candlepin server
            # which does not have the necessary API call.
            log.exception(ex)
            self.last_error = ex
            return None

    def to_dict(self) -> Dict:
        return self.server_status

    def _load_data(self, open_file: TextIO) -> Dict:
        json_str: str = open_file.read()
        return json.loads(json_str)

    def _sync_with_server(
        self,
        uep: connection.UEPConnection,
        consumer_uuid: str,
        _: Optional[datetime.datetime] = None,
    ) -> None:
        """
        Sync the latest data to/from the server.
        """
        raise NotImplementedError

    def _read_cache(self) -> Optional[Dict]:
        """
        Prefer in memory cache to avoid io.  If it doesn't exist, save
        the disk cache to the in-memory cache to avoid reading again.
        """
        if self.server_status is None:
            if self._cache_exists():
                log.debug("Trying to read status from %s file" % self.CACHE_FILE)
                self.server_status = super(StatusCache, self)._read_cache()
        else:
            log.debug("Reading status from in-memory cache of %s file" % self.CACHE_FILE)
        return self.server_status

    def _cache_exists(self) -> bool:
        """
        If a cache exists in memory, we have written it to the disk
        No need for unnecessary disk io here.
        """
        if self.server_status is not None:
            return True
        return super(StatusCache, self)._cache_exists()

    def read_status(
        self, uep: connection.UEPConnection, uuid: str, on_date: Optional[datetime.datetime] = None
    ) -> Optional[dict]:
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
            self.server_status = self._read_cache()
            if self.server_status is None:
                self.server_status = self.load_status(uep, uuid, on_date)
        else:
            log.debug("Reading status from in-memory cache of %s file" % self.CACHE_FILE)
        return self.server_status

    def write_cache(self):
        """
        This is threaded because it should never block in runtime.
        Writing to disk means it will be read from memory for the rest of this run.
        """
        threading.Thread(
            target=super(StatusCache, self).write_cache,
            args=[True],
            name="WriteCache%sThread" % self.__class__.__name__,
        ).start()
        log.debug("Started thread to write cache: %s" % self.CACHE_FILE)

    # we override a @classmethod with an instance method in the sub class?
    def delete_cache(self) -> None:
        super(StatusCache, self).delete_cache()
        self.server_status = None


class EntitlementStatusCache(StatusCache):
    """
    Manages the system cache of entitlement status from the server.
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/entitlement_status.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, on_date: Optional[datetime.datetime] = None
    ) -> None:
        self.server_status = uep.getCompliance(consumer_uuid, on_date)


class SyspurposeComplianceStatusCache(StatusCache):
    """
    Manages the system cache of system purpose compliance status from the server.
    Unlike other cache managers, this one gets info from the server rather
    than sending it.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/syspurpose_compliance_status.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, on_date: Optional[datetime.datetime] = None
    ) -> None:
        self.syspurpose_service = syspurpose.Syspurpose(uep)
        self.server_status: Dict = self.syspurpose_service.get_syspurpose_status(on_date)

    def write_cache(self):
        if self.server_status is not None and self.server_status["status"] != "unknown":
            super(SyspurposeComplianceStatusCache, self).write_cache()

    def get_overall_status(self) -> str:
        if self.server_status is not None:
            return syspurpose.Syspurpose.get_overall_status(self.server_status["status"])
        else:
            return syspurpose.Syspurpose.get_overall_status("unknown")

    def get_overall_status_code(self) -> str:
        if self.server_status is not None:
            return self.server_status.get("status", "unknown")
        else:
            return "unknown"

    def get_status_reasons(self) -> Optional[str]:
        if self.server_status is not None:
            return self.server_status.get("reasons", None)
        else:
            return None


class ProductStatusCache(StatusCache):
    """
    Manages the system cache of installed product valid date ranges.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/product_status.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        consumer_data: Dict = uep.getConsumer(consumer_uuid)

        if "installedProducts" not in consumer_data:
            log.warning("Server does not support product date ranges.")
        else:
            self.server_status = consumer_data["installedProducts"]


class OverrideStatusCache(StatusCache):
    """
    Manages the cache of yum repo overrides set on the server.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/content_overrides.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        self.server_status = uep.getContentOverrides(consumer_uuid)


class ReleaseStatusCache(StatusCache):
    """
    Manages the cache of the consumers 'release' setting applied to yum repos.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/releasever.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        def get_release(uuid: str) -> Dict:
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
        self.identity = inj.require(inj.IDENTITY)

    def profile_reporting_enabled(self):
        # If profile reporting is disabled from the environment, that overrides the setting in the conf file
        # If the environment variable is 0, defer to the setting in the conf file; likewise if the environment
        # variable is completely unset.
        if os.environ.get("SUBMAN_DISABLE_PROFILE_REPORTING", "").lower() in ["true", "1", "yes", "on"]:
            return False
        return conf["rhsm"].get_int("report_package_profile") == 1

    # give tests a chance to use something other than RPMProfile
    def _get_profile(self, profile_type):
        return get_profile(profile_type)

    @staticmethod
    def _assembly_profile(rpm_profile, enabled_repos_profile, module_profile) -> Dict[str, List[Dict]]:
        combined_profile = {
            "rpm": rpm_profile,
            "enabled_repos": enabled_repos_profile,
            "modulemd": module_profile,
        }
        return combined_profile

    @property
    def current_profile(self) -> Dict[str, List[Dict]]:
        if not self._current_profile:
            rpm_profile: List[Dict] = get_profile("rpm").collect()
            enabled_repos: List[Dict] = get_profile("enabled_repos").collect()
            module_profile: List[Dict] = get_profile("modulemd").collect()
            combined_profile: Dict[str, List[Dict]] = self._assembly_profile(
                rpm_profile, enabled_repos, module_profile
            )
            self._current_profile = combined_profile
        return self._current_profile

    @current_profile.setter
    def current_profile(self, new_profile: Dict[str, List[Dict]]):
        self._current_profile = new_profile

    def to_dict(self) -> Dict[str, List[Dict]]:
        return self.current_profile

    def _load_data(self, open_file: TextIO) -> Dict:
        json_str: str = open_file.read()
        return json.loads(json_str)

    def update_check(
        self, uep: connection.UEPConnection, consumer_uuid: str, force: bool = False
    ) -> Literal[0, 1]:
        """
        Check if packages have changed, and push an update if so.
        """

        # If the server doesn't support packages, don't try to send the profile:
        supported_resources: Dict = get_supported_resources(uep=None, identity=self.identity)
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

    def has_changed(self) -> bool:
        if not self._cache_exists():
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return True

        cached_profile: Optional[str] = self._read_cache()
        return not cached_profile == self.current_profile

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        """
        This method has to be able to sync combined profile, when server supports this functionality
        and it also has to be able to send only profile containing list of installed RPMs.
        """
        combined_profile: Dict = self.current_profile
        if uep.has_capability("combined_reporting"):
            _combined_profile: List[Dict] = [
                {"content_type": "rpm", "profile": combined_profile["rpm"]},
                {"content_type": "enabled_repos", "profile": combined_profile["enabled_repos"]},
                {"content_type": "modulemd", "profile": combined_profile["modulemd"]},
            ]
            uep.updateCombinedProfile(consumer_uuid, _combined_profile)
        else:
            uep.updatePackageProfile(consumer_uuid, combined_profile["rpm"])


class InstalledProductsManager(CacheManager):
    """
    Manages the cache of the products installed on this system, and what we
    last sent to the server.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/installed_products.json"

    _installed: Dict[str, dict]
    tags: Set[str]

    def __init__(self):
        self.product_dir: ProductDirectory = inj.require(inj.PROD_DIR)
        self._setup_installed()

    @property
    def installed(self) -> Dict:
        if not self._installed:
            self._setup_installed()
        return self._installed

    @installed.setter
    def installed(self, value: Dict) -> None:
        self._installed = value

    def to_dict(self) -> Dict:
        return {"products": self.installed, "tags": self.tags}

    def _load_data(self, open_file: TextIO) -> Dict:
        json_str = open_file.read()
        return json.loads(json_str)

    def has_changed(self) -> bool:
        if not self._cache_exists():
            log.debug("Cache file %s does not exist" % self.CACHE_FILE)
            return True

        cached: Dict = self._read_cache()
        try:
            products = cached["products"]
            tags = set(cached["tags"])
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

    def _setup_installed(self) -> None:
        """
        Format installed product data to match the cache
        and what the server can use.
        """
        self._installed: Dict[str, Dict] = {}
        self.tags = set()
        prod_cert: EntitlementCertificate
        for prod_cert in self.product_dir.list():
            prod: Product = prod_cert.products[0]
            self.tags |= set(prod.provided_tags)
            self._installed[prod.id] = {
                "productId": prod.id,
                "productName": prod.name,
                "version": prod.version,
                "arch": ",".join(prod.architectures),
            }

    def format_for_server(self) -> List[Dict]:
        """
        Convert the format we store in this object (which is a little
        easier to work with) into the format the server expects for the
        consumer.
        """
        self._setup_installed()
        final: List[Dict] = [val for (key, val) in list(self.installed.items())]
        return final

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        uep.updateConsumer(
            consumer_uuid,
            installed_products=self.format_for_server(),
            content_tags=self.tags,
        )


class PoolStatusCache(StatusCache):
    """
    Manages the system cache of pools
    """

    CACHE_FILE = "/var/lib/rhsm/cache/pool_status.json"

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> None:
        self.server_status = uep.getEntitlementList(consumer_uuid)


class PoolTypeCache:
    """
    Cache type of pool
    """

    def __init__(self):
        self.identity: Identity = inj.require(inj.IDENTITY)
        self.cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        self.ent_dir: EntitlementDirectory = inj.require(inj.ENT_DIR)
        self.pool_cache: PoolStatusCache = inj.require(inj.POOL_STATUS_CACHE)
        self.pooltype_map: Dict[str, str] = {}
        self.update()

    def get(self, pool_id: str):
        return self.pooltype_map.get(pool_id, "")

    def update(self) -> None:
        if self.requires_update():
            self._do_update()

    def requires_update(self) -> bool:
        attached_pool_ids: Set[str] = set(
            [ent.pool.id for ent in self.ent_dir.list() if ent.pool and ent.pool.id]
        )
        missing_types: Set[str] = attached_pool_ids - set(self.pooltype_map)
        return bool(missing_types)

    def _do_update(self) -> None:
        result: Dict[str, str] = {}
        if self.identity.is_valid():
            self.pool_cache.load_status(self.cp_provider.get_consumer_auth_cp(), self.identity.uuid)
            entitlement_list: List[Dict] = self.pool_cache.server_status

            if entitlement_list is not None:
                for ent in entitlement_list:
                    pool = PoolWrapper(ent.get("pool", {}))
                    pool_type: str = pool.get_pool_type()
                    result[pool.get_id()] = pool_type

        self.pooltype_map.update(result)

    def update_from_pools(self, pool_map: Dict) -> None:
        # pool_map maps pool ids to pool json
        for pool_id in pool_map:
            self.pooltype_map[pool_id] = PoolWrapper(pool_map[pool_id]).get_pool_type()

    def clear(self) -> None:
        self.pooltype_map = {}


class ContentAccessCache:
    CACHE_FILE = "/var/lib/rhsm/cache/content_access.json"

    def __init__(self):
        self.cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
        self.identity: Identity = inj.require(inj.IDENTITY)

    def _query_for_update(self, if_modified_since: Optional[datetime.datetime] = None):
        uep: connection.UEPConnection = self.cp_provider.get_consumer_auth_cp()
        try:
            response: Dict = uep.getAccessibleContent(self.identity.uuid, if_modified_since=if_modified_since)
        except connection.RestlibException as err:
            log.warning("Unable to query for content access updates: %s", err)
            return None
        if response is None or "contentListing" not in response:
            return None
        else:
            self._update_cache(response)
            return response

    def exists(self) -> bool:
        return os.path.exists(self.CACHE_FILE)

    def remove(self):
        return os.remove(self.CACHE_FILE)

    def check_for_update(self) -> Optional[Dict]:
        data: Optional[Dict] = None
        last_update: Optional[datetime.datetime]
        if self.exists():
            try:
                data: Dict = json.loads(self.read())
                last_update = parse_date(data["lastUpdate"])
            except (ValueError, KeyError) as err:
                log.debug("Cache file {file} is corrupted: {err}".format(file=self.CACHE_FILE, err=err))
                last_update = None
        else:
            last_update = None

        response: Optional[Dict] = self._query_for_update(if_modified_since=last_update)
        # Candlepin 4 bug 2010251. if_modified_since is not reliable so
        # we double checks whether or not the sca certificate is changed.
        if data is not None and data == response:
            log.debug("Content access certificate is up-to-date.")
            return None
        return response

    @staticmethod
    def update_cert(cert: "EntitlementCertificate", data: Optional[Dict]) -> None:
        if data is None:
            return
        if data["contentListing"] is None or str(cert.serial) not in data["contentListing"]:
            log.warning("Cert serial %s not contained in content listing; not updating it." % cert.serial)
            return
        with open(cert.path, "w") as output:
            updated_cert: str = "".join(data["contentListing"][str(cert.serial)])
            log.debug("Updating certificate %s with new content" % cert.serial)
            output.write(updated_cert)

    def _update_cache(self, data: Dict) -> None:
        log.debug("Updating content access cache")
        with open(self.CACHE_FILE, "w") as cache:
            cache.write(json.dumps(data))

    def read(self) -> str:
        with open(self.CACHE_FILE, "r") as cache:
            return cache.read()


class WrittenOverrideCache(CacheManager):
    """
    Cache to keep track of the overrides used last time the a redhat.repo
    was written.  Doesn't track server status, we've got another cache for
    that.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/written_overrides.json"

    def __init__(self, overrides: Optional[Dict] = None):
        self.overrides = overrides or {}

    def to_dict(self) -> Dict:
        return self.overrides

    def _load_data(self, open_file: TextIO) -> Optional[Dict]:
        try:
            self.overrides: Dict = json.loads(open_file.read()) or {}
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
    TIMEOUT: Optional[int] = None

    def __init__(self, data: Any = None):
        self.data = data or {}

    def to_dict(self) -> Dict:
        return self.data

    def _load_data(self, open_file: TextIO) -> Optional[Dict]:
        try:
            self.data: Dict = json.loads(open_file.read()) or {}
            return self.data
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # Ignore json file parse error
            pass

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> dict:
        """
        This method has to be implemented in subclasses of this class
        :param uep: object representing connection to candlepin server
        :param consumer_uuid: consumer UUID object
        :return: Subclass method has to return the content that was returned by candlepin server.
        """
        raise NotImplementedError

    def _is_cache_obsoleted(self, uep: connection.UEPConnection, identity: "Identity") -> bool:
        """
        Another method for checking if cached file is obsoleted
        :return: True if the cache is obsoleted; otherwise return False
        """
        return False

    def set_data(self, current_data: Any, identity: Optional["Identity"] = None):
        """
        Set data into internal cache
        :param current_data: data to set
        :param identity: object of identity
        :return: None
        """

        if identity is None:
            identity = inj.require(inj.IDENTITY)

        self.data: Dict[str, Any] = {identity.uuid: current_data}

    def read_data(
        self, uep: Optional[connection.UEPConnection] = None, identity: Optional["Identity"] = None
    ) -> Dict:
        """
        This function tries to get data from cache or server
        :param uep: connection to candlepin server
        :param identity: current identity of registered system
        :return: information about current owner
        """

        current_data: Dict = self.DEFAULT_VALUE

        if identity is None:
            identity: Identity = inj.require(inj.IDENTITY)

        # When identity is not known, then system is not registered and
        # data are obsoleted
        if identity.uuid is None:
            self.delete_cache()
            return current_data

        # Try to use class specific test if the cache file is obsoleted
        cache_file_obsoleted: bool = self._is_cache_obsoleted(uep, identity)

        # When timeout for cache is defined, then check if the cache file is not
        # too old. In that case content of the cache file will be overwritten with
        # new content from the server.
        if self.TIMEOUT is not None:
            if os.path.exists(self.CACHE_FILE):
                mod_time: float = os.path.getmtime(self.CACHE_FILE)
                cur_time: float = time.time()
                diff: float = cur_time - mod_time
                if diff > self.TIMEOUT:
                    log.debug("Validity of cache file %s timed out (%d)" % (self.CACHE_FILE, self.TIMEOUT))
                    cache_file_obsoleted = True

        if cache_file_obsoleted is False:
            # Try to read data from cache first
            log.debug("Trying to read %s from cache file %s" % (self.__class__.__name__, self.CACHE_FILE))
            data: Optional[Dict] = self.read_cache_only()
            if data is not None:
                if identity.uuid in data:
                    current_data = data[identity.uuid]
                else:
                    log.debug(
                        "Identity of system has changed. The cache file: %s is obsolete" % self.CACHE_FILE
                    )

        # When valid data are not in cached, then try to load it from candlepin server
        if len(current_data) != 0:
            log.debug("Data loaded from cache file: %s" % self.CACHE_FILE)
        else:
            if uep is None:
                cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
                uep = cp_provider.get_consumer_auth_cp()

            log.debug("Getting data from server for %s" % self.__class__)
            try:
                current_data: Dict = self._sync_with_server(uep=uep, consumer_uuid=identity.uuid)
            except connection.RestlibException as rest_err:
                log.warning("Unable to get data for %s using REST API: %s" % (self.__class__, rest_err))
                log.debug("Deleting cache file: %s", self.CACHE_FILE)
                self.delete_cache()
                # Raise exception again to be able to display error message in exception
                raise rest_err
            else:
                # Write data to cache
                self.set_data(current_data, identity)
                self.write_cache(debug=True)

        return current_data


class SyspurposeValidFieldsCache(ConsumerCache):
    """
    Cache the valid syspurpose fields for current owner
    """

    CACHE_FILE = "/var/lib/rhsm/cache/valid_fields.json"

    def __init__(self, data: Any = None):
        super(SyspurposeValidFieldsCache, self).__init__(data=data)

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> dict:
        cache: CurrentOwnerCache = inj.require(inj.CURRENT_OWNER_CACHE)
        owner: Dict = cache.read_data(uep)
        if "key" in owner:
            data: Dict = uep.getOwnerSyspurposeValidFields(owner["key"])
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

    def __init__(self, data: Any = None):
        super(CurrentOwnerCache, self).__init__(data=data)

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> dict:
        return uep.getOwner(consumer_uuid)

    def _is_cache_obsoleted(self, uep: connection.UEPConnection, identity: "Identity") -> bool:
        """
        We don't know if the cache is valid until we get valid response
        :param uep: object representing connection to candlepin server
        :param identity: consumer identity
        :return: True, when cache is obsoleted or validity of cache is unknown.
        """
        if uep is None:
            cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
            uep: connection.UEPConnection = cp_provider.get_consumer_auth_cp()
        if hasattr(uep.conn, "is_consumer_cert_key_valid") and uep.conn.is_consumer_cert_key_valid is True:
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

    def __init__(self, data: Any = None):
        super(ContentAccessModeCache, self).__init__(data=data)

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str, _: Optional[datetime.datetime] = None
    ) -> str:
        try:
            current_owner: Dict = uep.getOwner(consumer_uuid)
        except Exception:
            log.debug(
                "Error checking for content access mode,"
                "defaulting to assuming not in Simple Content Access mode"
            )
        else:
            if "contentAccessMode" in current_owner:
                return current_owner["contentAccessMode"]
            else:
                log.debug(
                    "The owner returned from the server did not contain a "
                    "'content_access_mode'. Perhaps the connected Entitlement Server doesn't"
                    "support 'content_access_mode'?"
                )
        return "unknown"

    def _is_cache_obsoleted(self, uep: connection.UEPConnection, identity: "Identity"):
        """
        We don't know if the cache is valid until we get valid response
        :param uep: object representing connection to candlepin server
        :param identity: consumer identity
        :return: True, when cache is obsoleted or validity of cache is unknown.
        """
        if uep is None:
            cp_provider: CPProvider = inj.require(inj.CP_PROVIDER)
            uep: connection.UEPConnection = cp_provider.get_consumer_auth_cp()

        if hasattr(uep.conn, "is_consumer_cert_key_valid"):
            if uep.conn.is_consumer_cert_key_valid is None:
                log.debug(
                    f"Cache file {self.CACHE_FILE} cannot be considered as valid, because no connection has "
                    "been created yet"
                )
                return True
            elif uep.conn.is_consumer_cert_key_valid is True:
                return False
            else:
                log.debug(
                    f"Cache file {self.CACHE_FILE} cannot be considered as valid, "
                    "because consumer certificate probably is not valid"
                )
                return True
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

    def __init__(self, data: Any = None):
        super(SupportedResourcesCache, self).__init__(data=data)

    def _sync_with_server(
        self, uep: connection.UEPConnection, consumer_uuid: str = None, _: Optional[datetime.datetime] = None
    ) -> dict:
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

    def timeout(self) -> float:
        """
        Compute timeout of cache. Computation of timeout is based on SRT (smoothed response time)
        of connection to candlepin server. This algorithm is inspired by retransmission timeout used
        by TCP connection (see: RFC 793)
        """
        uep: connection.UEPConnection = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        smoothed_rt: float

        if uep.conn.smoothed_rt is not None:
            smoothed_rt = uep.conn.smoothed_rt
        else:
            smoothed_rt = 0.0
        return min(self.UBOUND, max(self.LBOUND, self.BETA * smoothed_rt))

    def get_not_obsolete_data(self, identity: "Identity", filter_options: Dict) -> Dict:
        """
        Try to get not obsolete cached data
        :param identity: identity with UUID
        :param filter_options: dictionary with filter option
        :return: When data are not obsoleted, then return cached dictionary of available entitlements.
        Otherwise return empty dictionary.
        """
        data: Optional[Dict] = self.read_cache_only()
        available_pools: Dict = {}
        if data is not None:
            if identity.uuid in data:
                cached_data: Dict = data[identity.uuid]
                if cached_data["filter_options"] == filter_options:
                    log.debug("timeout: %s, current time: %s" % (cached_data["timeout"], time.time()))
                    if cached_data["timeout"] > time.time():
                        log.debug("Using cached list of available entitlements")
                        available_pools = cached_data["pools"]
                    else:
                        log.debug("Cache of available entitlements timed-out")
                else:
                    log.debug("Cache of available entitlements does not contain given filter options")
        return available_pools

    def _load_data(self, open_file: TextIO) -> Optional[Dict]:
        try:
            self.available_entitlements = json.loads(open_file.read()) or {}
            return self.available_entitlements
        except IOError as err:
            log.error("Unable to read cache: %s" % self.CACHE_FILE)
            log.exception(err)
        except ValueError:
            # Ignore json file parse error
            pass


class CloudTokenCache:
    """A cache for Candlepin's JWT used during automatic registration.

    This is used by rhsmcertd worker.
    """

    CACHE_FILE = "/var/lib/rhsm/cache/cloud_token_cache.json"

    @classmethod
    def get(cls, uep: "UEPConnection", cloud_id: str, metadata: str, signature: str) -> Dict[str, str]:
        """Get a JWT from the Candlepin server.

        If cached token already exists and is still valid, it will be used
        without contacting the server.
        """
        try:
            token: Dict[str, str] = cls._get_from_file()
            log.debug("JWT cache contains valid token, no need to contact the server.")
            return token
        except LookupError as exc:
            log.debug(f"JWT cache doesn't contain valid token, contacting the server ({exc}).")
        except Exception as exc:
            log.debug(f"JWT cache couldn't be read (got {type(exc).__name__}), contacting the server.")

        token: Dict[str, str] = cls._get_from_server(uep, cloud_id, metadata, signature)
        cls._save_to_file(token)
        return token

    @classmethod
    def is_valid(cls) -> bool:
        """Check if the cached JWT is valid.

        :returns:
            `True` if the locally cached JWT is valid,
            `False` if the locally cached JWT is expired or does not exist.
        """
        # 'exp' key: https://www.rfc-editor.org/rfc/rfc7519#section-4.1.4
        expiration: int = cls._get_payload()["exp"]

        now = int(time.time())
        return expiration > now

    @classmethod
    def _get_payload(cls) -> Dict:
        """Get the body of the JWT.

        :returns: The body of the JWT as a dictionary.
        :raises Exception: The file is missing or malformed.
        """
        with open(cls.CACHE_FILE, "r") as f:
            content: Dict[str, str] = json.load(f)

        payload: str = content["token"].split(".")[1]
        # JWT does not use the padding, base64.b64decode requires it.
        payload = f"{payload}==="

        return json.loads(base64.b64decode(payload).decode("utf-8"))

    @classmethod
    def _get_from_file(cls) -> Dict[str, str]:
        """Get a JWT from a cache file.

        :raises LookupError: The token is expired.
        :raises Exception: The file is missing or malformed.
        """
        if not cls.is_valid():
            cls.delete_cache()
            raise LookupError("Candlepin JWT is expired.")

        with open(cls.CACHE_FILE, "r") as f:
            return json.load(f)

    @classmethod
    def _get_from_server(
        cls, uep: "UEPConnection", cloud_id: str, metadata: str, signature: str
    ) -> Dict[str, str]:
        """Get a JWT from the Candlepin server."""
        log.debug("Obtaining Candlepin JWT.")
        result: Dict[str, str] = uep.getCloudJWT(cloud_id, metadata, signature)
        return result

    @classmethod
    def delete_cache(cls):
        if os.path.exists(cls.CACHE_FILE):
            os.remove(cls.CACHE_FILE)
            log.debug(f"Candlepin JWT cache file ({cls.CACHE_FILE}) was deleted.")

    @classmethod
    def _save_to_file(cls, token: Dict[str, str]) -> None:
        with open(cls.CACHE_FILE, "w") as f:
            json.dump(token, f)
        log.debug(f"Candlepin JWT was saved to a cache file ({cls.CACHE_FILE}).")
