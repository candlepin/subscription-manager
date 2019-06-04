from __future__ import print_function, division, absolute_import

#
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
import glob
import logging
import os
import re
import shutil
import stat
import syslog

from rhsm.config import initConfig
from rhsm.certificate import Key, CertificateException, create_from_pem

import subscription_manager.cache as cache
from subscription_manager.cert_sorter import StackingGroupSorter, ComplianceManager
from subscription_manager import identity
from subscription_manager.injection import require, CERT_SORTER, \
        IDENTITY, ENTITLEMENT_STATUS_CACHE, SYSTEMPURPOSE_COMPLIANCE_STATUS_CACHE, \
        PROD_STATUS_CACHE, ENT_DIR, PROD_DIR, CP_PROVIDER, OVERRIDE_STATUS_CACHE, \
        POOLTYPE_CACHE, RELEASE_STATUS_CACHE, FACTS, POOL_STATUS_CACHE
from subscription_manager import isodate
from subscription_manager.jsonwrapper import PoolWrapper
from subscription_manager.repolib import RepoActionInvoker
from subscription_manager.syspurposelib import SyncedStore
from subscription_manager import utils

# FIXME FIXME
from subscription_manager.identity import ConsumerIdentity
from dateutil.tz import tzlocal

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

cfg = initConfig()
ENT_CONFIG_DIR = cfg.get('rhsm', 'entitlementCertDir')

# Expected permissions for identity certificates:
ID_CERT_PERMS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP


def system_log(message, priority=syslog.LOG_NOTICE):
    utils.system_log(message, priority)


# FIXME: move me to identity.py
def persist_consumer_cert(consumerinfo):
    """
     Calls the consumerIdentity, persists and gets consumer info
    """
    cert_dir = cfg.get('rhsm', 'consumerCertDir')
    if not os.path.isdir(cert_dir):
        os.mkdir(cert_dir)
    consumer = identity.ConsumerIdentity(consumerinfo['idCert']['key'], consumerinfo['idCert']['cert'])
    consumer.write()
    log.debug("Consumer created: %s (%s)" % (consumer.getConsumerName(), consumer.getConsumerId()))
    system_log("Registered system with identity: %s" % consumer.getConsumerId())


class CertificateFetchError(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self, reason=""):
        msg = 'Entitlement Certificate(s) update failed due to the following reasons:\n' + '\n'.join(self.errors)
        return msg


def fetch_certificates(certlib):
    # Force fetch all certs
    result = certlib.update()
    exceptions = result.exceptions()
    if exceptions:
        raise CertificateFetchError(exceptions)

    return True


class PoolFilter(object):
    """
    Helper to filter a list of pools.
    """
    # Although sorter isn't necessarily required, when present it allows
    # us to not filter out yellow packages when "has no overlap" is selected
    def __init__(self, product_dir, entitlement_dir, sorter=None):

        self.product_directory = product_dir
        self.entitlement_directory = entitlement_dir
        self.sorter = sorter

    def filter_product_ids(self, pools, product_ids):
        """
        Filter a list of pools and return just those that provide products
        in the requested list of product ids. Both the top level product
        and all provided products will be checked.
        """
        matched_pools = []
        for pool in pools:
            if pool['productId'] in product_ids:
                log.debug("pool matches: %s" % pool['productId'])
                matched_pools.append(pool)
                continue

            for provided in pool['providedProducts']:
                if provided['productId'] in product_ids:
                    log.debug("pool provides: %s" % provided['productId'])
                    matched_pools.append(pool)
                    break
        return matched_pools

    def filter_out_uninstalled(self, pools):
        """
        Filter the given list of pools, return only those which provide
        a product installed on this system.
        """
        installed_products = self.product_directory.list()
        matched_data_dict = {}
        for d in pools:
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                # Build a list of provided product IDs for comparison:
                provided_ids = [p['productId'] for p in d['providedProducts']]

                if str(productid) in provided_ids or \
                        str(productid) == d['productId']:
                    matched_data_dict[d['id']] = d

        return list(matched_data_dict.values())

    def filter_out_installed(self, pools):
        """
        Filter the given list of pools, return only those which do not provide
        a product installed on this system.
        """
        installed_products = self.product_directory.list()
        matched_data_dict = {}
        for d in pools:
            matched_data_dict[d['id']] = d
            provided_ids = [p['productId'] for p in d['providedProducts']]
            for product in installed_products:
                productid = product.products[0].id
                # we only need one matched item per pool id, so add to dict to keep unique:
                if str(productid) in provided_ids or \
                        str(productid) == d['productId']:
                    del matched_data_dict[d['id']]
                    break

        return list(matched_data_dict.values())

    def filter_product_name(self, pools, contains_text):
        """
        Filter the given list of pools, removing those whose product name
        does not contain the given text.
        """
        lowered = contains_text.lower()
        filtered_pools = []
        for pool in pools:
            if lowered in pool['productName'].lower():
                filtered_pools.append(pool)
            else:
                for provided in pool['providedProducts']:
                    if lowered in provided['productName'].lower():
                        filtered_pools.append(pool)
                        break
        return filtered_pools

    def _get_entitled_product_ids(self):
        entitled_products = []
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                entitled_products.append(product.id)
        return entitled_products

    def _get_entitled_product_to_cert_map(self):
        entitled_products_to_certs = {}
        for cert in self.entitlement_directory.list():
            for product in cert.products:
                prod_id = product.id
                if prod_id not in entitled_products_to_certs:
                    entitled_products_to_certs[prod_id] = set()
                entitled_products_to_certs[prod_id].add(cert)
        return entitled_products_to_certs

    def _dates_overlap(self, pool, certs):
        pool_start = isodate.parse_date(pool['startDate'])
        pool_end = isodate.parse_date(pool['endDate'])

        for cert in certs:
            cert_range = cert.valid_range
            if cert_range.has_date(pool_start) or cert_range.has_date(pool_end):
                return True
        return False

    def filter_out_overlapping(self, pools):
        entitled_product_ids_to_certs = self._get_entitled_product_to_cert_map()
        filtered_pools = []
        for pool in pools:
            provided_ids = set([p['productId'] for p in pool['providedProducts']])
            wrapped_pool = PoolWrapper(pool)
            # NOTE: We may have to check for other types or handle the case of a product with no type in the future
            if wrapped_pool.get_product_attributes('type')['type'] == 'SVC':
                provided_ids.add(pool['productId'])
            overlap = 0
            possible_overlap_pids = provided_ids.intersection(list(entitled_product_ids_to_certs.keys()))
            for productid in possible_overlap_pids:
                if self._dates_overlap(pool, entitled_product_ids_to_certs[productid]) \
                        and productid not in self.sorter.partially_valid_products:
                    overlap += 1
                else:
                    break
            if overlap != len(provided_ids) or wrapped_pool.get_stacking_id() in self.sorter.partial_stacks:
                filtered_pools.append(pool)

        return filtered_pools

    def filter_out_non_overlapping(self, pools):
        not_overlapping = self.filter_out_overlapping(pools)
        return [pool for pool in pools if pool not in not_overlapping]

    def filter_subscribed_pools(self, pools, subscribed_pool_ids,
            compatible_pools):
        """
        Filter the given list of pools, removing those for which the system
        already has a subscription, unless the pool can be subscribed to again
        (ie has multi-entitle).
        """
        resubscribeable_pool_ids = [pool['id'] for pool in
                                    list(compatible_pools.values())]

        filtered_pools = []
        for pool in pools:
            if (pool['id'] not in subscribed_pool_ids) or \
                    (pool['id'] in resubscribeable_pool_ids):
                filtered_pools.append(pool)
        return filtered_pools


def list_pools(uep, consumer_uuid, list_all=False, active_on=None, filter_string=None, future=None,
               after_date=None):
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

    owner = uep.getOwner(consumer_uuid)
    ownerid = owner['key']

    return uep.getPoolsList(consumer=consumer_uuid, listAll=list_all,
            active_on=active_on, owner=ownerid, filter_string=filter_string, future=future,
                            after_date=after_date)


# TODO: This method is morphing the actual pool json and returning a new
# dict which does not contain all the pool info. Not sure if this is really
# necessary. Also some "view" specific things going on in here.
def get_available_entitlements(get_all=False, active_on=None, overlapping=False,
                               uninstalled=False, text=None, filter_string=None,
                               future=None, after_date=None):
    """
    Returns a list of entitlement pools from the server.

    The 'all' setting can be used to return all pools, even if the rules do
    not pass. (i.e. show pools that are incompatible for your hardware)
    """
    columns = [
        'id',
        'quantity',
        'consumed',
        'startDate',
        'endDate',
        'productName',
        'providedProducts',
        'productId',
        'roles',
        'attributes',
        'pool_type',
        'service_level',
        'service_type',
        'usage',
        'addons',
        'suggested',
        'contractNumber',
        'management_enabled'
    ]

    pool_stash = PoolStash()
    dlist = pool_stash.get_filtered_pools_list(active_on, not get_all,
           overlapping, uninstalled, text, filter_string, future=future, after_date=after_date)

    for pool in dlist:
        pool_wrapper = PoolWrapper(pool)
        pool['providedProducts'] = pool_wrapper.get_provided_products()
        if allows_multi_entitlement(pool):
            pool['multi-entitlement'] = "Yes"
        else:
            pool['multi-entitlement'] = "No"

        support_attrs = pool_wrapper.get_product_attributes("support_level",
                                                            "support_type",
                                                            "roles",
                                                            "usage",
                                                            "addons")
        pool['service_level'] = support_attrs['support_level']
        pool['service_type'] = support_attrs['support_type']
        pool['roles'] = support_attrs['roles']
        pool['usage'] = support_attrs['usage']
        pool['addons'] = support_attrs['addons']
        pool['suggested'] = pool_wrapper.get_suggested_quantity()
        pool['pool_type'] = pool_wrapper.get_pool_type()
        pool['management_enabled'] = pool_wrapper.management_enabled()

        if pool['suggested'] is None:
            pool['suggested'] = ""

    # no default, so default is None if key not found
    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        if int(d['quantity']) < 0:
            d['quantity'] = _('Unlimited')
        else:
            d['quantity'] = str(int(d['quantity']) - int(d['consumed']))

        d['startDate'] = format_date(isodate.parse_date(d['startDate']))
        d['endDate'] = format_date(isodate.parse_date(d['endDate']))
        del d['consumed']

    return data


class MergedPools(object):
    """
    Class to track the view of merged pools for the same product.
    Used to view total entitlement information across all pools for a
    particular product.
    """
    def __init__(self, product_id, product_name):
        self.product_id = product_id
        self.product_name = product_name
        self.bundled_products = 0
        self.quantity = 0  # how many entitlements were purchased
        self.consumed = 0  # how many are in use
        self.pools = []

    def add_pool(self, pool):
        # TODO: check if product id and name match?
        self.consumed += pool['consumed']
        # we want to add the quantity for this pool
        #  the total. if the pool is unlimited, the
        #  resulting quantity will be set to -1 and
        #  subsequent added pools will not change that.
        if pool['quantity'] == -1:
            self.quantity = -1
        elif self.quantity != -1:
            self.quantity += pool['quantity']
        self.pools.append(pool)

        # This is a little tricky, technically speaking, subscriptions
        # decide what products they provide, so it *could* vary in some
        # edge cases from one sub to another even though they are for the
        # same product. For now we'll just set this value each time a pool
        # is added and hope they are consistent.
        self.bundled_products = len(pool['providedProducts'])

    def _virt_physical_sorter(self, pool):
        """
        Used to sort the pools, return Physical or Virt depending on
        the value or existence of the virt_only attribute.

        Returning numeric values to simulate the behavior we want.
        """
        for attr in pool['attributes']:
            if attr['name'] == 'virt_only' and attr['value'] == 'true':
                return 1
        return 2

    def sort_virt_to_top(self):
        """
        Prioritizes virt pools to the front of the list, if any are present.

        Used by contract selector to show these first in the list.
        """
        self.pools.sort(key=self._virt_physical_sorter)


def merge_pools(pools):
    """
    Merges the given pools into a data structure representing the totals
    for a particular product, across all pools for that product.

    This provides an overview for a given product, how many total entitlements
    you have available and in use across all subscriptions for that product.

    Returns a dict mapping product ID to MergedPools object.
    """
    # Map product ID to MergedPools object:
    merged_pools = {}

    for pool in pools:
        if not pool['productId'] in merged_pools:
            merged_pools[pool['productId']] = MergedPools(pool['productId'],
                    pool['productName'])
        merged_pools[pool['productId']].add_pool(pool)

    # Just return a list of the MergedPools objects, without the product ID
    # key hashing:
    return merged_pools


class MergedPoolsStackingGroupSorter(StackingGroupSorter):
    """
    Sorts a list of MergedPool objects by stacking_id.
    """
    def __init__(self, merged_pools):
        StackingGroupSorter.__init__(self, merged_pools)

    def _get_stacking_id(self, merged_pool):
        return PoolWrapper(merged_pool.pools[0]).get_stacking_id()

    def _get_identity_name(self, merged_pool):
        return merged_pool.pools[0]['productName']


class PoolStash(object):
    """
    Object used to fetch pools from the server, sort them into compatible,
    incompatible, and installed lists. Also does filtering based on name.
    """
    def __init__(self):
        self.identity = require(IDENTITY)
        self.sorter = None

        # Pools which passed rules server side for this consumer:
        self.compatible_pools = {}

        # Pools which failed a rule check server side:
        self.incompatible_pools = {}

        # Pools for which we already have an entitlement:
        self.subscribed_pool_ids = []

        # All pools:
        self.all_pools = {}

    def all_pools_size(self):
        return len(self.all_pools)

    def refresh(self, active_on):
        """
        Refresh the list of pools from the server, active on the given date.
        """

        if active_on:
            self.sorter = ComplianceManager(active_on)
        else:
            self.sorter = require(CERT_SORTER)
        self.all_pools = {}
        self.compatible_pools = {}
        log.debug("Refreshing pools from server...")
        for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, active_on=active_on):
            self.compatible_pools[pool['id']] = pool
            self.all_pools[pool['id']] = pool

        # Filter the list of all pools, removing those we know are compatible.
        # Sadly this currently requires a second query to the server.
        self.incompatible_pools = {}
        for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, list_all=True, active_on=active_on):
            if not pool['id'] in self.compatible_pools:
                self.incompatible_pools[pool['id']] = pool
                self.all_pools[pool['id']] = pool

        self.subscribed_pool_ids = self._get_subscribed_pool_ids()

        # In the gui, cache all pool types so when we attach new ones
        # we can avoid more api calls
        require(POOLTYPE_CACHE).update_from_pools(self.all_pools)

        log.debug("found %s pools:" % len(self.all_pools))
        log.debug("   %s compatible" % len(self.compatible_pools))
        log.debug("   %s incompatible" % len(self.incompatible_pools))
        log.debug("   %s already subscribed" % len(self.subscribed_pool_ids))

    def get_filtered_pools_list(self, active_on, incompatible,
            overlapping, uninstalled, text, filter_string, future=None, after_date=None):
        """
        Used for CLI --available filtering
        cuts down on api calls
        """
        self.all_pools = {}
        self.compatible_pools = {}
        if active_on and overlapping:
            self.sorter = ComplianceManager(active_on)
        elif not active_on and overlapping:
            self.sorter = require(CERT_SORTER)

        if incompatible:
            for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, active_on=active_on,
                filter_string=filter_string, future=future, after_date=after_date):
                self.compatible_pools[pool['id']] = pool
        else:  # --all has been used
            for pool in list_pools(require(CP_PROVIDER).get_consumer_auth_cp(),
                self.identity.uuid, list_all=True, active_on=active_on,
                filter_string=filter_string, future=future, after_date=after_date):
                self.all_pools[pool['id']] = pool

        return self._filter_pools(incompatible, overlapping, uninstalled, False, text)

    def _get_subscribed_pool_ids(self):
        return [ent.pool.id for ent in require(ENT_DIR).list()]

    def _filter_pools(self, incompatible, overlapping, uninstalled, subscribed,
            text):
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
            log.debug("\tRemoved %d incompatible pools" %
                       len(self.incompatible_pools))

        pool_filter = PoolFilter(require(PROD_DIR),
                require(ENT_DIR), self.sorter)

        # Filter out products that are not installed if necessary:
        if uninstalled:
            prev_length = len(pools)
            pools = pool_filter.filter_out_uninstalled(pools)
            log.debug("\tRemoved %d pools for not installed products" %
                       (prev_length - len(pools)))

        if overlapping:
            prev_length = len(pools)
            pools = pool_filter.filter_out_overlapping(pools)
            log.debug("\tRemoved %d pools overlapping existing entitlements" %
                      (prev_length - len(pools)))

        # Filter by product name if necessary:
        if text:
            prev_length = len(pools)
            pools = pool_filter.filter_product_name(pools, text)
            log.debug("\tRemoved %d pools not matching the search string" %
                      (prev_length - len(pools)))

        if subscribed:
            prev_length = len(pools)
            pools = pool_filter.filter_subscribed_pools(pools,
                    self.subscribed_pool_ids, self.compatible_pools)
            log.debug("\tRemoved %d pools that we're already subscribed to" %
                      (prev_length - len(pools)))

        log.debug("\t%d pools to display, %d filtered out" % (len(pools),
            len(self.all_pools) - len(pools)))

        return pools

    def merge_pools(self, incompatible=False, overlapping=False,
            uninstalled=False, subscribed=False, text=None):
        """
        Return a merged view of pools filtered according to the given options.
        Pools for the same product will be merged into a MergedPool object.

        Arguments turn on filters, so setting one to True will reduce the
        number of results.
        """
        pools = self._filter_pools(incompatible, overlapping, uninstalled,
                subscribed, text)
        merged_pools = merge_pools(pools)
        return merged_pools

    def lookup_provided_products(self, pool_id):
        """
        Return a list of tuples (product name, product id) for all products
        provided for a given pool. If we do not actually have any info on this
        pool, return None.
        """
        pool = self.all_pools.get(pool_id)
        if pool is None:
            log.debug("pool id %s not found in all_pools", pool_id)
            return None

        provided_products = []
        for product in pool['providedProducts']:
            provided_products.append((product['productName'], product['productId']))
        return provided_products


class ImportFileExtractor(object):
    """
    Responsible for checking an import file and pulling cert and key from it.
    An import file may include only the certificate, but may also include its
    key.

    An import file is processed looking for:

    -----BEGIN <TAG>-----
    <CONTENT>
    ..
    -----END <TAG>-----

    and will only process if it finds CERTIFICATE or KEY in the <TAG> text.

    For example the following would locate a key and cert.

    -----BEGIN CERTIFICATE-----
    <CERT_CONTENT>
    -----END CERTIFICATE-----
    -----BEGIN PUBLIC KEY-----
    <KEY_CONTENT>
    -----END PUBLIC KEY-----

    """
    _REGEX_START_GROUP = "start"
    _REGEX_CONTENT_GROUP = "content"
    _REGEX_END_GROUP = "end"
    _REGEX = "(?P<%s>[-]*BEGIN[\w\ ]*[-]*)(?P<%s>[^-]*)(?P<%s>[-]*END[\w\ ]*[-]*)" % \
                (_REGEX_START_GROUP, _REGEX_CONTENT_GROUP, _REGEX_END_GROUP)
    _PATTERN = re.compile(_REGEX)

    _CERT_DICT_TAG = "CERTIFICATE"
    _KEY_DICT_TAG = "KEY"
    _ENT_DICT_TAG = "ENTITLEMENT"
    _SIG_DICT_TAG = "RSA SIGNATURE"

    def __init__(self, cert_file_path):
        self.path = cert_file_path
        self.file_name = os.path.basename(cert_file_path)

        content = self._read(cert_file_path)
        self.parts = self._process_content(content)

    def _read(self, file_path):
        fd = open(file_path, "r")
        file_content = fd.read()
        fd.close()
        return file_content

    def _process_content(self, content):
        part_dict = {}
        matches = self._PATTERN.finditer(content)
        for match in matches:
            start = match.group(self._REGEX_START_GROUP)
            meat = match.group(self._REGEX_CONTENT_GROUP)
            end = match.group(self._REGEX_END_GROUP)

            dict_key = None
            if not start.find(self._KEY_DICT_TAG) < 0:
                dict_key = self._KEY_DICT_TAG
            elif not start.find(self._CERT_DICT_TAG) < 0:
                dict_key = self._CERT_DICT_TAG
            elif not start.find(self._ENT_DICT_TAG) < 0:
                dict_key = self._ENT_DICT_TAG
            elif not start.find(self._SIG_DICT_TAG) < 0:
                dict_key = self._SIG_DICT_TAG

            if dict_key is None:
                continue

            part_dict[dict_key] = start + meat + end
        return part_dict

    def contains_key_content(self):
        return self._KEY_DICT_TAG in self.parts

    def get_key_content(self):
        key_content = None
        if self._KEY_DICT_TAG in self.parts:
            key_content = self.parts[self._KEY_DICT_TAG]
        return key_content

    def get_cert_content(self):
        cert_content = ''
        if self._CERT_DICT_TAG in self.parts:
            cert_content = self.parts[self._CERT_DICT_TAG]
        if self._ENT_DICT_TAG in self.parts:
            cert_content = cert_content + os.linesep + self.parts[self._ENT_DICT_TAG]
        if self._SIG_DICT_TAG in self.parts:
            cert_content = cert_content + os.linesep + self.parts[self._SIG_DICT_TAG]
        return cert_content

    def verify_valid_entitlement(self):
        """
        Verify that a valid entitlement was processed.

        @return: True if valid, False otherwise.
        """
        try:
            cert = self.get_cert()
            # Don't want to check class explicitly, instead we'll look for
            # order info, which only an entitlement cert could have:
            if not hasattr(cert, 'order'):
                return False
        except CertificateException:
            return False
        ent_key = Key(self.get_key_content())
        if ent_key.bogus():
            return False
        return True

    # TODO: rewrite to use certlib.EntitlementCertBundleInstall?
    def write_to_disk(self):
        """
        Write/copy cert to the entitlement cert dir.
        """
        self._ensure_entitlement_dir_exists()
        dest_file_path = os.path.join(ENT_CONFIG_DIR,
                                      self._create_filename_from_cert_serial_number())

        # Write the key/cert content to new files
        log.debug("Writing certificate file: %s" % (dest_file_path))
        cert_content = self.get_cert_content()
        self._write_file(dest_file_path, cert_content)

        if self.contains_key_content():
            dest_key_file_path = self._get_key_path_from_dest_cert_path(dest_file_path)
            log.debug("Writing key file: %s" % (dest_key_file_path))
            self._write_file(dest_key_file_path, self.get_key_content())

    def _write_file(self, target_path, content):
        new_file = open(target_path, "w")
        try:
            new_file.write(content)
        finally:
            new_file.close()

    def _ensure_entitlement_dir_exists(self):
        if not os.access(ENT_CONFIG_DIR, os.R_OK):
            os.mkdir(ENT_CONFIG_DIR)

    def _get_key_path_from_dest_cert_path(self, dest_cert_path):
        file_parts = os.path.splitext(dest_cert_path)
        return file_parts[0] + "-key" + file_parts[1]

    def _create_filename_from_cert_serial_number(self):
        "create from serial"
        ent_cert = self.get_cert()
        return "%s.pem" % (ent_cert.serial)

    def get_cert(self):
        cert_content = self.get_cert_content()
        ent_cert = create_from_pem(cert_content)
        return ent_cert


def _sub_dict(datadict, subkeys, default=None):
    """Return a dict that is a subset of datadict matching only the keys in subkeys"""
    return dict([(k, datadict.get(k, default)) for k in subkeys])


def format_date(dt):
    if dt:
        try:
            return dt.astimezone(tzlocal()).strftime("%x")
        except ValueError:
            log.warn("Datetime does not contain timezone information")
            return dt.strftime("%x")
    else:
        return ""


# FIXME: move me to identity.py
def check_identity_cert_perms():
    """
    Ensure the identity certs on this system have the correct permissions, and
    fix them if not.
    """
    certs = [identity.ConsumerIdentity.keypath(), identity.ConsumerIdentity.certpath()]
    for cert in certs:
        if not os.path.exists(cert):
            # Only relevant if these files exist.
            continue
        statinfo = os.stat(cert)
        if statinfo[stat.ST_UID] != 0 or statinfo[stat.ST_GID] != 0:
            os.chown(cert, 0, 0)
            log.warn("Corrected incorrect ownership of %s." % cert)

        mode = stat.S_IMODE(statinfo[stat.ST_MODE])
        if mode != ID_CERT_PERMS:
            os.chmod(cert, ID_CERT_PERMS)
            log.warn("Corrected incorrect permissions on %s." % cert)


def clean_all_data(backup=True):
    consumer_dir = cfg.get('rhsm', 'consumerCertDir')
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
        if (os.path.exists(path)):
            log.debug("Removing identity cert: %s" % path)
            os.remove(path)

    require(IDENTITY).reload()

    # Delete all entitlement certs rather than the directory itself:
    ent_cert_dir = cfg.get('rhsm', 'entitlementCertDir')
    if os.path.exists(ent_cert_dir):

        for f in glob.glob("%s/*.pem" % ent_cert_dir):
            certpath = os.path.join(ent_cert_dir, f)
            log.debug("Removing entitlement cert: %s" % f)
            os.remove(certpath)
    else:
        log.warn("Entitlement cert directory does not exist: %s" % ent_cert_dir)

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

    RepoActionInvoker.delete_repo_file()
    log.debug("Cleaned local data")


def valid_quantity(quantity):
    if not quantity:
        return False

    try:
        return int(quantity) > 0
    except ValueError:
        return False


def allows_multi_entitlement(pool):
    """
    Determine if this pool allows multi-entitlement based on the pool's
    top-level product's multi-entitlement attribute.
    """
    for attribute in pool['productAttributes']:
        if attribute['name'] == "multi-entitlement" and \
            utils.is_true_value(attribute['value']):
            return True
    return False
