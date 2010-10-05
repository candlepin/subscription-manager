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
from datetime import datetime
from certlib import CertLib, ConsumerIdentity, \
                    ProductDirectory, EntitlementDirectory
from logutil import getLogger
from facts import getFacts
from config import initConfig

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


def getMatchedSubscriptions(poollist):
    """
    Gets the list of products that matched the list of installed products.

    Returns a list of product info _and_ pool info (the id is actually pool id)
    """
    installedProducts = ProductDirectory().list()
    matched_data_dict = {}
    for d in poollist:
        for installedProduct in installedProducts:
            productid = installedProduct.getProduct().getHash()
            # we only need one matched item per pool id, so add to dict to uniq
            if str(productid) in d['providedProductIds'] or str(productid) == d['productId']:
                matched_data_dict[d['id']] = d
    return matched_data_dict.values()


def getAvailableEntitlements(cpserver, consumer, all=False):
    """
     Gets the available Entitlements from the server
    """
    columns = ['id', 'quantity', 'consumed', 'endDate', 'productName',
            'providedProductIds', 'productId']
    facts = getFacts()
    if facts.delta():
        cpserver.updateConsumerFacts(consumer, facts.get_facts())
    
    dlist = cpserver.getPoolsList(consumer, all)
    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        if int(d['quantity']) < 0:
            d['quantity'] = 'unlimited'
        else:
            d['quantity'] = str(int(d['quantity']) - int(d['consumed']))

        d['endDate'] = formatDate(d['endDate'])
        del d['consumed']
    return data


def _sub_dict(datadict, subkeys, default=None):
    return dict([(k, datadict.get(k, default)) for k in subkeys])


def formatDate(date):
    tf = xml.utils.iso8601.parse(date)
    return datetime.fromtimestamp(tf).date()


def unregister(uep, consumer_uuid, force=True):
    """ 
    Shared logic for un-registration. 
    
    If an unregistration fails, we always clean up locally, but allow the 
    exception to be thrown so the caller can decide how to handle it.
    """
    try:
        uep.unregisterConsumer(consumer_uuid)
    finally:
        if force:
            # Clean up certificates, these are no longer valid:
            shutil.rmtree(cfg.get('rhsm', 'consumerCertDir'), ignore_errors=True)
            shutil.rmtree(cfg.get('rhsm', 'entitlementCertDir'), ignore_errors=True)
            log.info("Successfully un-registered.")

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
