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
import os
import stat
import sys
import constants
import shutil
import xml.utils.iso8601
from datetime import datetime, date
from certlib import CertLib, ConsumerIdentity, \
                    ProductDirectory, EntitlementDirectory
from logutil import getLogger
from config import initConfig
from xml.utils.iso8601 import parse

log = getLogger(__name__)

import gettext
_ = gettext.gettext

cfg = initConfig()

# Localization domain:
APP = 'rhsm'
# Directory where translations are deployed:
DIR = '/usr/share/locale/'

# Expected permissions for identity certificates:
ID_CERT_PERMS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP

def configure_i18n():
    """
    Configure internationalization for the application. Should only be
    called once per invocation. (once for CLI, once for GUI)
    """
    import locale
    import gettext
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APP, DIR)
    gettext.textdomain(APP)


def persist_consumer_cert(consumerinfo):
    """
     Calls the consumerIdentity, persists and gets consumer info
    """
    cert_dir = cfg.get('rhsm', 'consumerCertDir')
    if not os.path.isdir(cert_dir):
        os.mkdir(cert_dir)
    consumer = ConsumerIdentity(consumerinfo['idCert']['key'], \
                                  consumerinfo['idCert']['cert'])
    consumer.write()
    print consumer.getConsumerId(), consumer.getConsumerName()
    consumer_info = {"consumer_name": consumer.getConsumerName(),
                     "uuid": consumer.getConsumerId()}
    log.info("Consumer created: %s" % consumer_info)
    return consumer_info


def map_status(status):
    smap = {True: _("Subscribed"), False: _("Expired"), None: _("Not Subscribed")}
    return smap[status]


def getInstalledProductStatus():
    """
     Returns the Installed products and their subscription states
    """
    products = ProductDirectory().list()
    entcerts = EntitlementDirectory().list()
    entdict = {}
    for cert in entcerts:
        ents = cert.getEntitlements()
        eproducts = cert.getProducts()
        for product in eproducts:
            entdict[product.getName()] = {'Entitlements': ents,
                                          'valid': cert.valid(),
                                          'expires': formatDate(cert.validRange().end().isoformat()),
                                          'serial': cert.serialNumber(),
                                          'contract': cert.getOrder().getContract()}
    product_status = []
    for product in products:
        pname = product.getProduct().getName()
        if entdict.has_key(pname):
            data = (pname, map_status(entdict[pname]['valid']), str(entdict[pname]['expires']), entdict[pname]['serial'], entdict[pname]['contract'])
            product_status.append(data)
        else:
            product_status.append((pname, map_status(None), "", "", ""))

    # Include entitled but not installed products
    psnames = [prod[0] for prod in product_status]
    for cert in EntitlementDirectory().list():
        for product in cert.getProducts():
            if product.getName() not in psnames:
                psname = product.getName()
                data = (psname, _('Not Installed'), str(entdict[psname]['expires']), entdict[psname]['serial'], entdict[psname]['contract'])
                product_status.append(data)
    return product_status


def getEntitlementsForProduct(product_name):
    entitlements = []
    for cert in EntitlementDirectory().list():
        for cert_product in cert.getProducts():
            if product_name == cert_product.getName():
                entitlements.append(cert)
    return entitlements


def getInstalledProductHashMap():
    products = ProductDirectory().list()
    phash = {}
    for product in products:
        phash[product.getProduct().getName()] = product.getProduct().getHash()
    return phash


def getConsumedProductEntitlements():
    """
     Gets the list of available products with entitlements based on
      its subscription cert
    """
    entdir = EntitlementDirectory()
    consumed_products = []
    for cert in entdir.listValid():
        eproducts = cert.getProducts()
        for product in eproducts:
            data = (product.getName(), cert.getOrder().getContract(), cert.serialNumber(), cert.valid(), formatDate(cert.validRange().begin().isoformat()), \
                    formatDate(cert.validRange().end().isoformat()))
            consumed_products.append(data)
    return consumed_products


def getProductDescription(qproduct):
    """
     Utility method to construct description info based on the state per product
    """
    entcerts = EntitlementDirectory().list()
    products = ProductDirectory().list()
    product_status = getInstalledProductStatus()
    data = ""
    for pst in product_status:
        if qproduct == pst[0]:
            if pst[1] == "Subscribed":
                data = constants.subscribed_status % (pst[0], pst[2])
            if pst[1] == "Not Subscribed":
                data = constants.unsubscribed_status % (pst[0], pst[0], pst[0])
            if pst[1] == "Expired":
                data = constants.expired_status % (pst[0], pst[2], pst[0], pst[0])
            if pst[1] == "Not Installed":
                data = constants.not_installed_status % (pst[0], pst[0], pst[0])

    for product in products:
        if qproduct == product.getProduct().getName():
            product = product.getProduct()
            data += constants.product_describe % (product.getName(),
                                       product.getVariant(),
                                       product.getArch(),
                                       product.getVersion())
    for cert in entcerts:
        eproducts = cert.getProducts()
        for product in eproducts:
            if qproduct == product.getName():
                ents = cert.getContentEntitlements()
                if not len(ents):
                    continue
                data += """ CONTENT ENTITLEMENTS \n"""
                data += """======================="""
                for ent in ents:
                    data += constants.content_entitlement_describe % (\
                                                ent.getName(),
                                                str(ent.getLabel()),
                                                ent.getQuantity(),
                                                ent.getFlexQuantity(),
                                                ent.getVendor(),
                                                str(ent.getUrl()),
                                                ent.getEnabled())
                ents = cert.getRoleEntitlements()
                data += """ ROLE ENTITLEMENTS \n"""
                data += """======================="""
                for ent in ents:
                    data += constants.role_entitlement_describe % (ent.getName(),
                                                    ent.getDescription())
    return data


class PoolFilter(object):
    """
    Helper to filter a list of pools.
    """
    def __init__(self):
        self.product_directory = ProductDirectory()

    def filter_uninstalled(self, pools):
        """
        Filter the given list of pools, removing those which do not provide
        a product installed on this system.
        """
        installed_products = self.product_directory.list()
        matched_data_dict = {}
        for d in pools:
            for product in installed_products:
                productid = product.getProduct().getHash()
                # we only need one matched item per pool id, so add to dict to keep unique:
                if str(productid) in d['providedProductIds'] or \
                        str(productid) == d['productId']:
                    matched_data_dict[d['id']] = d

        return matched_data_dict.values()

    def filter_product_name(self, pools, contains_text):
        """
        Filter the given list of pools, removing those whose product name
        does not contain the given text.
        """
        filtered_pools = []
        for pool in pools:
            if contains_text.lower() in pool['productName'].lower():
                filtered_pools.append(pool)
        return filtered_pools

    def filter_active_on(self, pools, date):
        """
        Filter out pools which will not be active on the given date.
        """
        filtered_pools = []
        for pool in pools:
            start_date = formatDate(pool['startDate'])
            end_date = formatDate(pool['endDate'])
            if start_date <= date <= end_date:
                filtered_pools.append(pool)
        return filtered_pools


def list_pools(uep, consumer_uuid, facts, all=False):
    """
    Wrapper around the UEP call to fetch pools, which forces a facts update
    if anything has changed before making the request. This ensures the
    rule checks server side will have the most up to date info about the
    consumer possible.
    """
    if facts.delta():
        uep.updateConsumerFacts(consumer_uuid, facts.get_facts())
    return uep.getPoolsList(consumer_uuid, all)

# TODO: This method is morphing the actual pool json and returning a new 
# dict which does not contain all the pool info. Not sure if this is really
# necessary. Also some "view" specific things going on in here.
def getAvailableEntitlements(cpserver, consumer_uuid, facts, all=False):
    """
    Returns a list of entitlement pools from the server.

    Facts will be updated if appropriate before making the request, to ensure
    the rules on the server will pass if appropriate.

    The 'all' setting can be used to return all pools, even if the rules do
    not pass. (i.e. show pools that are incompatible for your hardware)
    """
    columns = ['id', 'quantity', 'consumed', 'endDate', 'productName',
            'providedProductIds', 'productId']
    
    dlist = list_pools(cpserver, consumer_uuid, facts, all)

    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        if int(d['quantity']) < 0:
            d['quantity'] = 'unlimited'
        else:
            d['quantity'] = str(int(d['quantity']) - int(d['consumed']))

        d['endDate'] = formatDate(d['endDate'])
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
        self.quantity = 0 # how many entitlements were purchased
        self.consumed = 0 # how many are in use
        self.pools = []

    def add_pool(self, pool):
        # TODO: check if product id and name match?

        self.consumed += pool['consumed']
        self.quantity += pool['quantity']
        self.pools.append(pool)

        # This is a little tricky, technically speaking, subscriptions
        # decide what products they provide, so it *could* vary in some
        # edge cases from one sub to another even though they are for the
        # same product. For now we'll just set this value each time a pool
        # is added and hope they are consistent.
        self.bundled_products = len(pool['providedProductIds'])


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
        if not merged_pools.has_key(pool['productId']):
            merged_pools[pool['productId']] = MergedPools(pool['productId'],
                    pool['productName'])
        merged_pools[pool['productId']].add_pool(pool)

    # Just return a list of the MergedPools objects, without the product ID
    # key hashing:
    return merged_pools


class PoolStash(object):
    """
    Object used to fetch pools from the server, sort them into compatible,
    incompatible, and installed lists. Also does filtering based on name.
    """
    def __init__(self, backend, consumer, facts):
        self.backend = backend
        self.consumer = consumer
        self.facts = facts
        self.compatible_pools = {}
        self.incompatible_pools = {}

    def refresh(self):
        """
        Refresh the list of pools from the server.
        """
        self.compatible_pools = {}
        for pool in list_pools(self.backend.uep,
                self.consumer.uuid, self.facts):
            self.compatible_pools[pool['id']] = pool

        # Filter the list of all pools, removing those we know are compatible.
        # Sadly this currently requires a second query to the server.
        self.incompatible_pools = {}
        for pool in list_pools(self.backend.uep,
                self.consumer.uuid, self.facts, all=True):
            if not pool['id'] in self.compatible_pools:
                self.incompatible_pools[pool['id']] = pool

    def get_pools(self, incompatible=False, uninstalled=False, text=None,
            active_on=None):
        """
        Return a list of pool hashes, filtered according to the given options.

        This method does not actually hit the server, filtering is done in
        memory.
        """
        pools = self.compatible_pools.values()
        if incompatible:
            pools = pools + self.incompatible_pools.values()

        pool_filter = PoolFilter()

        # Filter out products that are not installed if necessary:
        if not uninstalled:
            pools = pool_filter.filter_uninstalled(pools)

        # Filter by product name if necessary:
        if text:
            pools = pool_filter.filter_product_name(pools, text)

        if active_on:
            pools = pool_filter.filter_active_on(pools, active_on)

        return pools

    def get_merged_pools(self, incompatible=False, uninstalled=False, text=None, active_on=None):
        """
        Return a merged view of pools filtered according to the given options.
        Pools for the same product will be merged into a MergedPool object.
        """
        pools = self.get_pools(incompatible, uninstalled, text, active_on)
        merged_pools = merge_pools(pools)
        return merged_pools


def _sub_dict(datadict, subkeys, default=None):
    return dict([(k, datadict.get(k, default)) for k in subkeys])


def formatDate(date):
    tf = xml.utils.iso8601.parse(date)
    return datetime.fromtimestamp(tf).date()

def delete_consumer_certs():
    shutil.rmtree(cfg.get('rhsm', 'consumerCertDir'), ignore_errors=True)
    shutil.rmtree(cfg.get('rhsm', 'entitlementCertDir'), ignore_errors=True)


def unregister(uep, consumer_uuid, force=True):
    """ 
    Shared logic for un-registration. 
    
    If an unregistration fails, we always clean up locally, but allow the 
    exception to be thrown so the caller can decide how to handle it.
    """
    try:
        uep.unregisterConsumer(consumer_uuid)
        log.info("Successfully un-registered.")
        force=True
    finally:
        if force:
            # Clean up certificates, these are no longer valid:
            delete_consumer_certs()

def check_identity_cert_perms():
    """
    Ensure the identity certs on this system have the correct permissions, and
    fix them if not.
    """
    certs = [ConsumerIdentity.keypath(), ConsumerIdentity.certpath()]
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

if __name__ == '__main__':
    print("\nInstalled Product Status:\n")
    print getInstalledProductStatus()
    print("\nConsumed Product Status:\n")
    getConsumedProductEntitlements()
    getInstalledProductHashMap()
