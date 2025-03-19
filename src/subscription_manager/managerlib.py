# common calls to get product and entitlemnt info for gui/tui
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import datetime
import glob
import logging
import os
import grp
import shutil
import stat
import syslog
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union, TYPE_CHECKING


from rhsm.config import get_config_parser

import subscription_manager.cache as cache
from subscription_manager.cert_sorter import StackingGroupSorter
from subscription_manager import identity
from subscription_manager.injection import (
    require,
    IDENTITY,
    ENTITLEMENT_STATUS_CACHE,
    SYSTEMPURPOSE_COMPLIANCE_STATUS_CACHE,
    PROD_STATUS_CACHE,
    ENT_DIR,
    PROD_DIR,
    CP_PROVIDER,
    OVERRIDE_STATUS_CACHE,
    POOLTYPE_CACHE,
    RELEASE_STATUS_CACHE,
    FACTS,
    POOL_STATUS_CACHE,
)
from subscription_manager import isodate
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.syspurposelib import SyncedStore
from subscription_manager import utils

# FIXME FIXME
from subscription_manager.identity import ConsumerIdentity
from dateutil.tz import tzlocal

from subscription_manager.i18n import ugettext as _

if TYPE_CHECKING:
    from rhsm.connection import UEPConnection
    from rhsm.certificate2 import EntitlementCertificate, DateRange
    from rhsm.config import RhsmConfigParser
    from subscription_manager.identity import Identity
    from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory
    from subscription_manager.cp_provider import CPProvider


log = logging.getLogger(__name__)

cfg: "RhsmConfigParser" = get_config_parser()
ENT_CONFIG_DIR: str = cfg.get("rhsm", "entitlementCertDir")

# Expected permissions for identity certificates:
ID_CERT_PERMS: int = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
RHSM_GROUP_NAME: str = "rhsm"


def system_log(message: str, priority: int = syslog.LOG_NOTICE) -> None:
    utils.system_log(message, priority)


def close_all_connections() -> None:
    """
    Close all connections
    :return: None
    """
    cpp_provider: CPProvider = require(CP_PROVIDER)
    cpp_provider.close_all_connections()


# FIXME: move me to identity.py
def persist_consumer_cert(consumerinfo: dict) -> None:
    """
    Calls the consumerIdentity, persists and gets consumer info
    """
    cert_dir: str = cfg.get("rhsm", "consumerCertDir")
    if not os.path.isdir(cert_dir):
        os.mkdir(cert_dir)
    consumer = identity.ConsumerIdentity(consumerinfo["idCert"]["key"], consumerinfo["idCert"]["cert"])
    consumer.write()
    log.info("Consumer created: %s (%s)" % (consumer.getConsumerName(), consumer.getConsumerId()))
    system_log("Registered system with identity: %s" % consumer.getConsumerId())


class CertificateFetchError(Exception):
    def __init__(self, errors: Iterable[Exception]):
        self.errors = errors

    def __str__(self, reason: str = "") -> str:
        # FIXME Explicitly convert errors to strings
        msg = "Entitlement Certificate(s) update failed due to the following reasons:\n" + "\n".join(
            self.errors
        )
        return msg


class PoolFilter:
    """
    Helper to filter a list of pools.
    """

    # Although sorter isn't necessarily required, when present it allows
    # us to not filter out yellow packages when "has no overlap" is selected
    def __init__(
        self,
        product_dir: "ProductDirectory",
        entitlement_dir: "EntitlementDirectory",
    ):
        self.product_directory: ProductDirectory = product_dir
        self.entitlement_directory: EntitlementDirectory = entitlement_dir

    def filter_product_ids(self, pools: Iterable[dict], product_ids: Iterable[str]) -> List[dict]:
        """
        Filter a list of pools and return just those that provide products
        in the requested list of product ids. Both the top level product
        and all provided products will be checked.
        """
        matched_pools: List[dict] = []
        for pool in pools:
            if pool["productId"] in product_ids:
                log.debug("pool matches: %s" % pool["productId"])
                matched_pools.append(pool)
                continue

            for provided in pool["providedProducts"]:
                if provided["productId"] in product_ids:
                    log.debug("pool provides: %s" % provided["productId"])
                    matched_pools.append(pool)
                    break
        return matched_pools

    def filter_out_uninstalled(self, pools: Iterable[dict]) -> List[dict]:
        """
        Filter the given list of pools, return only those which provide
        a product installed on this system.
        """
        installed_products: List[EntitlementCertificate] = self.product_directory.list()
        matched_data_dict: Dict[str, dict] = {}
        for d in pools:
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                # Build a list of provided product IDs for comparison:
                provided_ids: List[str] = [p["productId"] for p in d["providedProducts"]]

                if str(productid) in provided_ids or str(productid) == d["productId"]:
                    matched_data_dict[d["id"]] = d

        return list(matched_data_dict.values())

    def filter_out_installed(self, pools: Iterable[dict]) -> List[dict]:
        """
        Filter the given list of pools, return only those which do not provide
        a product installed on this system.
        """
        installed_products: List[EntitlementCertificate] = self.product_directory.list()
        matched_data_dict: Dict[str, dict] = {}
        for d in pools:
            matched_data_dict[d["id"]] = d
            provided_ids = [p["productId"] for p in d["providedProducts"]]
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                if str(productid) in provided_ids or str(productid) == d["productId"]:
                    del matched_data_dict[d["id"]]
                    break

        return list(matched_data_dict.values())

    def filter_product_name(self, pools: Iterable[dict], contains_text: str) -> List[dict]:
        """
        Filter the given list of pools, removing those whose product name
        does not contain the given text.
        """
        lowered: str = contains_text.lower()
        filtered_pools: List[dict] = []
        for pool in pools:
            if lowered in pool["productName"].lower():
                filtered_pools.append(pool)
            else:
                for provided in pool["providedProducts"]:
                    if lowered in provided["productName"].lower():
                        filtered_pools.append(pool)
                        break
        return filtered_pools

    def _get_entitled_product_ids(self) -> List[dict]:
        entitled_products: List[dict] = []
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                entitled_products.append(product.id)
        return entitled_products

    def _get_entitled_product_to_cert_map(self) -> Dict[str, set]:
        entitled_products_to_certs: Dict[str, set] = {}
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                prod_id = product.id
                if prod_id not in entitled_products_to_certs:
                    entitled_products_to_certs[prod_id] = set()
                entitled_products_to_certs[prod_id].add(cert)
        return entitled_products_to_certs

    def _dates_overlap(self, pool: dict, certs: Iterable["EntitlementCertificate"]) -> bool:
        pool_start = isodate.parse_date(pool["startDate"])
        pool_end = isodate.parse_date(pool["endDate"])

        for cert in certs:
            cert_range: DateRange = cert.valid_range
            if cert_range.has_date(pool_start) or cert_range.has_date(pool_end):
                return True
        return False

    def filter_out_overlapping(self, pools: Iterable[dict]) -> List[dict]:
        entitled_product_ids_to_certs: Dict[str, set] = self._get_entitled_product_to_cert_map()
        filtered_pools: List[dict] = []
        for pool in pools:
            provided_ids = set([p["productId"] for p in pool["providedProducts"]])
            wrapped_pool = PoolWrapper(pool)
            # NOTE: We may have to check for other types
            # or handle the case of a product with no type in the future
            if wrapped_pool.get_product_attributes("type")["type"] == "SVC":
                provided_ids.add(pool["productId"])
            overlap: int = 0
            possible_overlap_pids = provided_ids.intersection(list(entitled_product_ids_to_certs.keys()))
            for productid in possible_overlap_pids:
                if self._dates_overlap(pool, entitled_product_ids_to_certs[productid]):
                    overlap += 1
                else:
                    break
            if overlap != len(provided_ids):
                filtered_pools.append(pool)

        return filtered_pools

    def filter_out_non_overlapping(self, pools: Iterable[dict]) -> List[dict]:
        not_overlapping = self.filter_out_overlapping(pools)
        return [pool for pool in pools if pool not in not_overlapping]

    def filter_subscribed_pools(
        self,
        pools: Iterable[dict],
        subscribed_pool_ids: Iterable[str],
        compatible_pools: Dict[str, dict],
    ) -> List[dict]:
        """
        Filter the given list of pools, removing those for which the system
        already has a subscription, unless the pool can be subscribed to again
        (ie has multi-entitle).
        """
        resubscribeable_pool_ids: List[str] = [pool["id"] for pool in list(compatible_pools.values())]

        filtered_pools: List[dict] = []
        for pool in pools:
            if (pool["id"] not in subscribed_pool_ids) or (pool["id"] in resubscribeable_pool_ids):
                filtered_pools.append(pool)
        return filtered_pools


def list_pools(
    uep: "UEPConnection",
    consumer_uuid: str,
    list_all: bool = False,
    active_on: Optional[datetime.datetime] = None,
    filter_string: Optional[str] = None,
    future: Optional[str] = None,
    after_date: Optional[datetime.datetime] = None,
    page: int = 0,
    items_per_page: int = 0,
):
    """
    Wrapper around the UEP call to fetch pools, which forces a facts update
    if anything has changed before making the request. This ensures the
    rule checks server side will have the most up to date info about the
    consumer possible.
    """

    # client tells service 'look for facts again'
    # if service finds new facts:
    #     -emit a signal?
    #     - or just update properties
    #       - and set a 'been_synced' property to False
    # client waits for facts check to finish
    # if no changes or been_synced=True, continue
    # if changes or unsynced:
    #    subman updates candlepin with the latest version of services GetFacts() [blocking]
    #    when finished, subman emit's 'factsSyncFinished'
    #        - then service flops 'been_synced' property
    #    -or- subman calls 'here_are_the_latest_facts_to_the_server()' on service
    #         then service flops 'been_synced' property
    # subman gets signal that props changed, and that been_synced is now true
    # since it's been synced, then subman continues
    require(FACTS).update_check(uep, consumer_uuid)

    profile_mgr = cache.ProfileManager()
    profile_mgr.update_check(uep, consumer_uuid)

    owner: dict = uep.getOwner(consumer_uuid)
    ownerid: str = owner["key"]

    return uep.getPoolsList(
        consumer=consumer_uuid,
        listAll=list_all,
        active_on=active_on,
        owner=ownerid,
        filter_string=filter_string,
        future=future,
        after_date=after_date,
        page=page,
        items_per_page=items_per_page,
    )


# TODO: This method is morphing the actual pool json and returning a new
# dict which does not contain all the pool info. Not sure if this is really
# necessary. Also some "view" specific things going on in here.
def get_available_entitlements(
    get_all: bool = False,
    active_on: Optional[datetime.datetime] = None,
    overlapping: bool = False,
    uninstalled: bool = False,
    text: Optional[str] = None,
    filter_string: Optional[str] = None,
    future: Optional[str] = None,
    after_date: Optional[datetime.datetime] = None,
    page: int = 0,
    items_per_page: int = 0,
    iso_dates: bool = False,
) -> List[dict]:
    """
    Returns a list of entitlement pools from the server.

    The 'all' setting can be used to return all pools, even if the rules do
    not pass. (i.e. show pools that are incompatible for your hardware)
    """
    columns: List[str] = [
        "id",
        "quantity",
        "consumed",
        "startDate",
        "endDate",
        "productName",
        "providedProducts",
        "productId",
        "roles",
        "attributes",
        "pool_type",
        "service_level",
        "service_type",
        "usage",
        "addons",
        "suggested",
        "contractNumber",
        "management_enabled",
    ]

    pool_stash = PoolStash()
    dlist: List[dict] = pool_stash.get_filtered_pools_list(
        active_on,
        not get_all,
        overlapping,
        uninstalled,
        text,
        filter_string,
        future=future,
        after_date=after_date,
        page=page,
        items_per_page=items_per_page,
    )

    date_formatter: Callable
    if iso_dates:
        date_formatter = format_iso8601_date
    else:
        date_formatter = format_date

    for pool in dlist:
        pool_wrapper = PoolWrapper(pool)
        pool["providedProducts"] = pool_wrapper.get_provided_products()
        if allows_multi_entitlement(pool):
            pool["multi-entitlement"] = "Yes"
        else:
            pool["multi-entitlement"] = "No"

        support_attrs = pool_wrapper.get_product_attributes(
            "support_level", "support_type", "roles", "usage", "addons"
        )
        pool["service_level"] = support_attrs["support_level"]
        pool["service_type"] = support_attrs["support_type"]
        pool["roles"] = support_attrs["roles"]
        pool["usage"] = support_attrs["usage"]
        pool["addons"] = support_attrs["addons"]
        pool["suggested"] = pool_wrapper.get_suggested_quantity()
        pool["pool_type"] = pool_wrapper.get_pool_type()
        pool["management_enabled"] = pool_wrapper.management_enabled()

        if pool["suggested"] is None:
            pool["suggested"] = ""

    # no default, so default is None if key not found
    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        if int(d["quantity"]) < 0:
            d["quantity"] = _("Unlimited")
        else:
            d["quantity"] = str(int(d["quantity"]) - int(d["consumed"]))

        d["startDate"] = date_formatter(isodate.parse_date(d["startDate"]))
        d["endDate"] = date_formatter(isodate.parse_date(d["endDate"]))
        del d["consumed"]

    return data


class MergedPools:
    """
    Class to track the view of merged pools for the same product.
    Used to view total entitlement information across all pools for a
    particular product.
    """

    def __init__(self, product_id: str, product_name: str):
        self.product_id: str = product_id
        self.product_name: str = product_name
        self.bundled_products: int = 0
        self.quantity: int = 0  # how many entitlements were purchased
        self.consumed: int = 0  # how many are in use
        self.pools: List[dict] = []

    def add_pool(self, pool: dict) -> None:
        # TODO: check if product id and name match?
        self.consumed += pool["consumed"]
        # we want to add the quantity for this pool
        #  the total. if the pool is unlimited, the
        #  resulting quantity will be set to -1 and
        #  subsequent added pools will not change that.
        if pool["quantity"] == -1:
            self.quantity = -1
        elif self.quantity != -1:
            self.quantity += pool["quantity"]
        self.pools.append(pool)

        # This is a little tricky, technically speaking, subscriptions
        # decide what products they provide, so it *could* vary in some
        # edge cases from one sub to another even though they are for the
        # same product. For now we'll just set this value each time a pool
        # is added and hope they are consistent.
        self.bundled_products = len(pool["providedProducts"])

    def _virt_physical_sorter(self, pool: dict) -> int:
        """
        Used to sort the pools, return Physical or Virt depending on
        the value or existence of the virt_only attribute.

        Returning numeric values to simulate the behavior we want.
        """
        for attr in pool["attributes"]:
            if attr["name"] == "virt_only" and attr["value"] == "true":
                return 1
        return 2

    def sort_virt_to_top(self) -> None:
        """
        Prioritizes virt pools to the front of the list, if any are present.

        Used by contract selector to show these first in the list.
        """
        self.pools.sort(key=self._virt_physical_sorter)


def merge_pools(pools: List[dict]) -> Dict:
    """
    Merges the given pools into a data structure representing the totals
    for a particular product, across all pools for that product.

    This provides an overview for a given product, how many total entitlements
    you have available and in use across all subscriptions for that product.

    Returns a dict mapping product ID to MergedPools object.
    """
    # Map product ID to MergedPools object:
    merged_pools: dict = {}

    for pool in pools:
        if not pool["productId"] in merged_pools:
            merged_pools[pool["productId"]] = MergedPools(pool["productId"], pool["productName"])
        merged_pools[pool["productId"]].add_pool(pool)

    # Just return a list of the MergedPools objects, without the product ID
    # key hashing:
    return merged_pools


class MergedPoolsStackingGroupSorter(StackingGroupSorter):
    """
    Sorts a list of MergedPool objects by stacking_id.
    """

    def __init__(self, merged_pools: List["EntitlementCertificate"]):
        StackingGroupSorter.__init__(self, merged_pools)

    def _get_stacking_id(self, merged_pool):
        return PoolWrapper(merged_pool.pools[0]).get_stacking_id()

    def _get_identity_name(self, merged_pool):
        return merged_pool.pools[0]["productName"]


class PoolStash:
    """
    Object used to fetch pools from the server, sort them into compatible,
    incompatible, and installed lists. Also does filtering based on name.
    """

    def __init__(self):
        self.identity: Identity = require(IDENTITY)

        # Pools which passed rules server side for this consumer:
        self.compatible_pools = {}

        # Pools which failed a rule check server side:
        self.incompatible_pools = {}

        # Pools for which we already have an entitlement:
        self.subscribed_pool_ids = []

        # All pools:
        self.all_pools = {}

    def all_pools_size(self) -> int:
        return len(self.all_pools)

    def refresh(self, active_on: Optional[datetime.datetime]) -> None:
        """
        Refresh the list of pools from the server, active on the given date.
        """

        self.all_pools = {}
        self.compatible_pools = {}
        log.debug("Refreshing pools from server...")
        for pool in list_pools(
            require(CP_PROVIDER).get_consumer_auth_cp(), self.identity.uuid, active_on=active_on
        ):
            self.compatible_pools[pool["id"]] = pool
            self.all_pools[pool["id"]] = pool

        # Filter the list of all pools, removing those we know are compatible.
        # Sadly this currently requires a second query to the server.
        self.incompatible_pools = {}
        for pool in list_pools(
            require(CP_PROVIDER).get_consumer_auth_cp(),
            self.identity.uuid,
            list_all=True,
            active_on=active_on,
        ):
            if not pool["id"] in self.compatible_pools:
                self.incompatible_pools[pool["id"]] = pool
                self.all_pools[pool["id"]] = pool

        self.subscribed_pool_ids = self._get_subscribed_pool_ids()

        # In the gui, cache all pool types so when we attach new ones
        # we can avoid more api calls
        require(POOLTYPE_CACHE).update_from_pools(self.all_pools)

        log.debug("found %s pools:" % len(self.all_pools))
        log.debug("   %s compatible" % len(self.compatible_pools))
        log.debug("   %s incompatible" % len(self.incompatible_pools))
        log.debug("   %s already subscribed" % len(self.subscribed_pool_ids))

    def get_filtered_pools_list(
        self,
        active_on: Optional[datetime.datetime],
        incompatible: bool,
        overlapping: bool,
        uninstalled: bool,
        text: Optional[str],
        filter_string: Optional[str],
        future: Optional[str] = None,
        after_date: Optional[datetime.datetime] = None,
        page: int = 0,
        items_per_page: int = 0,
    ) -> List[dict]:
        """
        Used for CLI --available filtering
        cuts down on api calls
        """
        self.all_pools: Dict[str, dict] = {}
        self.compatible_pools: Dict[str, dict] = {}

        if incompatible:
            pools = list_pools(
                require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid,
                active_on=active_on,
                filter_string=filter_string,
                future=future,
                after_date=after_date,
                page=page,
                items_per_page=items_per_page,
            )
            for pool in pools:
                self.compatible_pools[pool["id"]] = pool
        else:  # --all has been used
            pools = list_pools(
                require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid,
                list_all=True,
                active_on=active_on,
                filter_string=filter_string,
                future=future,
                after_date=after_date,
                page=page,
                items_per_page=items_per_page,
            )
            for pool in pools:
                self.all_pools[pool["id"]] = pool

        return self._filter_pools(incompatible, overlapping, uninstalled, False, text)

    def _get_subscribed_pool_ids(self) -> List[str]:
        return [ent.pool.id for ent in require(ENT_DIR).list()]

    def _filter_pools(
        self,
        incompatible: bool,
        overlapping: bool,
        uninstalled: bool,
        subscribed: bool,
        text: Optional[str],
    ):
        """
        Return a list of pool hashes, filtered according to the given options.

        This method does not actually hit the server, filtering is done in
        memory.
        """

        log.debug("Filtering %d total pools" % len(self.all_pools))
        if not incompatible:
            pools = list(self.all_pools.values())
        else:
            pools = list(self.compatible_pools.values())
            log.debug("\tRemoved %d incompatible pools" % len(self.incompatible_pools))

        pool_filter = PoolFilter(require(PROD_DIR), require(ENT_DIR))

        # Filter out products that are not installed if necessary:
        if uninstalled:
            prev_length = len(pools)
            pools = pool_filter.filter_out_uninstalled(pools)
            log.debug("\tRemoved %d pools for not installed products" % (prev_length - len(pools)))

        if overlapping:
            prev_length = len(pools)
            pools = pool_filter.filter_out_overlapping(pools)
            log.debug("\tRemoved %d pools overlapping existing entitlements" % (prev_length - len(pools)))

        # Filter by product name if necessary:
        if text:
            prev_length = len(pools)
            pools = pool_filter.filter_product_name(pools, text)
            log.debug("\tRemoved %d pools not matching the search string" % (prev_length - len(pools)))

        if subscribed:
            prev_length = len(pools)
            pools = pool_filter.filter_subscribed_pools(
                pools, self.subscribed_pool_ids, self.compatible_pools
            )
            log.debug("\tRemoved %d pools that we're already subscribed to" % (prev_length - len(pools)))

        log.debug(
            "\t%d pools to display, %d filtered out" % (len(pools), max(0, len(self.all_pools) - len(pools)))
        )

        return pools

    def merge_pools(
        self,
        incompatible: bool = False,
        overlapping: bool = False,
        uninstalled: bool = False,
        subscribed: bool = False,
        text: Optional[str] = None,
    ) -> dict:
        """
        Return a merged view of pools filtered according to the given options.
        Pools for the same product will be merged into a MergedPool object.

        Arguments turn on filters, so setting one to True will reduce the
        number of results.
        """
        pools = self._filter_pools(incompatible, overlapping, uninstalled, subscribed, text)
        merged_pools = merge_pools(pools)
        return merged_pools

    def lookup_provided_products(self, pool_id: str) -> Optional[List[Tuple[str, str]]]:
        """
        Return a list of tuples (product name, product id) for all products
        provided for a given pool. If we do not actually have any info on this
        pool, return None.
        """
        pool = self.all_pools.get(pool_id)
        if pool is None:
            log.debug("pool id %s not found in all_pools", pool_id)
            return None

        provided_products: List[Tuple[str, str]] = []
        for product in pool["providedProducts"]:
            provided_products.append((product["productName"], product["productId"]))
        return provided_products


def _sub_dict(datadict: dict, subkeys: Iterable[str], default: Optional[object] = None) -> dict:
    """Return a dict that is a subset of datadict matching only the keys in subkeys"""
    return dict([(k, datadict.get(k, default)) for k in subkeys])


def format_date(dt: datetime.datetime) -> str:
    if dt:
        try:
            return dt.astimezone(tzlocal()).strftime("%x")
        except ValueError:
            log.warning("Datetime does not contain timezone information")
            return dt.strftime("%x")
    else:
        return ""


def format_iso8601_date(dateobj: Optional[datetime.datetime]) -> str:
    """
    Format the specified datetime.date dateobj as ISO 8601, i.e. YYYY-MM-DD.

    Return an empty string for an invalid object.
    """
    if dateobj:
        return dateobj.strftime("%Y-%m-%d")
    return ""


def get_rhsm_group() -> Optional[grp.struct_group]:
    """
    Try to get GUID about rhsm group
    """
    rhsm_group = None
    try:
        rhsm_group = grp.getgrnam(RHSM_GROUP_NAME)
    except KeyError:
        log.error(f"Unable to get information about {RHSM_GROUP_NAME}")
    return rhsm_group


# FIXME: move me to identity.py
def check_identity_cert_perms() -> None:
    """
    Ensure the identity certs on this system have the correct permissions, and
    fix them if not.
    """
    certs: List[str] = [identity.ConsumerIdentity.keypath(), identity.ConsumerIdentity.certpath()]
    rhsm_group = get_rhsm_group()
    cert_guid = 0
    if rhsm_group is not None:
        cert_guid = rhsm_group.gr_gid
    for cert in certs:
        if not os.path.exists(cert):
            # Only relevant if these files exist.
            continue
        statinfo: os.stat_result = os.stat(cert)
        if statinfo[stat.ST_UID] != 0 or statinfo[stat.ST_GID] != cert_guid:
            os.chown(cert, 0, cert_guid)
            log.warning("Corrected incorrect ownership of %s." % cert)

        mode: int = stat.S_IMODE(statinfo[stat.ST_MODE])
        if mode != ID_CERT_PERMS:
            os.chmod(cert, ID_CERT_PERMS)
            log.warning("Corrected incorrect permissions on %s." % cert)


def clean_all_data(backup: bool = True) -> None:
    consumer_dir: str = cfg.get("rhsm", "consumerCertDir")
    if backup:
        if consumer_dir[-1] == "/":
            consumer_dir_backup = consumer_dir[0:-1] + ".old"
        else:
            consumer_dir_backup = consumer_dir + ".old"

        # Delete backup dir if it exists:
        shutil.rmtree(consumer_dir_backup, ignore_errors=True)

        # Copy current consumer dir:
        log.debug("Backing up %s to %s.", consumer_dir, consumer_dir_backup)
        shutil.copytree(consumer_dir, consumer_dir_backup)

    # FIXME FIXME
    # Delete current consumer certs:
    for path in [ConsumerIdentity.keypath(), ConsumerIdentity.certpath()]:
        if os.path.exists(path):
            log.debug("Removing identity cert: %s" % path)
            os.remove(path)

    require(IDENTITY).reload()

    # Close all connections, when consumer certificate was just removed
    close_all_connections()

    # Delete all entitlement certs rather than the directory itself:
    ent_cert_dir = cfg.get("rhsm", "entitlementCertDir")
    if os.path.exists(ent_cert_dir):
        for f in glob.glob("%s/*.pem" % ent_cert_dir):
            certpath = os.path.join(ent_cert_dir, f)
            log.debug("Removing entitlement cert: %s" % f)
            os.remove(certpath)
    else:
        log.warning("Entitlement cert directory does not exist: %s" % ent_cert_dir)

    # Subclasses of cache.CacheManager have a @classmethod delete_cache
    # for deleting persistent caches
    cache.ProfileManager.delete_cache()
    cache.InstalledProductsManager.delete_cache()
    if SyncedStore is not None:
        SyncedStore(None).update_cache({})
    # FIXME: implement as dbus client to facts service DeleteCache() once implemented
    # Facts.delete_cache()
    # WrittenOverridesCache is also a subclass of cache.CacheManager, but
    # it is deleted in RepoActionInvoker.delete_repo_file() below.
    # StatusCache subclasses have a a per instance cache varable
    # and delete_cache is an instance method, so we need to call
    # the delete_cache on the instances created in injectioninit.
    require(ENTITLEMENT_STATUS_CACHE).delete_cache()
    require(SYSTEMPURPOSE_COMPLIANCE_STATUS_CACHE).delete_cache()
    require(PROD_STATUS_CACHE).delete_cache()
    require(POOL_STATUS_CACHE).delete_cache()
    require(OVERRIDE_STATUS_CACHE).delete_cache()
    require(RELEASE_STATUS_CACHE).delete_cache()
    cache.CloudTokenCache.delete_cache()

    RepoActionInvoker.delete_repo_file()
    log.debug("Cleaned local data")


def valid_quantity(quantity: Union[int, str, None]) -> bool:
    if not quantity:
        return False

    try:
        return int(quantity) > 0
    except ValueError:
        return False


def allows_multi_entitlement(pool: dict) -> bool:
    """
    Determine if this pool allows multi-entitlement based on the pool's
    top-level product's multi-entitlement attribute.
    """
    for attribute in pool["productAttributes"]:
        if attribute["name"] == "multi-entitlement" and utils.is_true_value(attribute["value"]):
            return True
    return False
