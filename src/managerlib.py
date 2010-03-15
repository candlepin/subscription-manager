#!/usr/bin/python
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
import sys
from certlib import CertLib, ConsumerIdentity, \
                    ProductDirectory, EntitlementDirectory

def check_registration():
    if not os.access("/etc/pki/consumer/cert.uuid", os.F_OK):
        needToRegister = \
            _("Error: You need to register this system by running " \
            "`register` command before using this option.")
        print needToRegister
        sys.exit(1)
    return open("/etc/pki/consumer/cert.uuid").read()

def map_status(status):
    smap = {True : "Subscribed", False : "Expired", None : "Not Subscribed"}
    return smap[status]

def getInstalledProductStatus():
    products = ProductDirectory().list()
    entcerts = EntitlementDirectory().list()
    entdict = {}
    for cert in entcerts:
        ents = cert.getEntitlements()
        entdict[cert.getProduct().getName()] = {'Entitlements' : ents, 
                                                'valid': cert.valid(), 
                                                'expires' : cert.validRange().end()}
    product_status = []
    for product in products:
        pname = product.getProduct().getName()
        if entdict.has_key(pname):
            data = (pname, map_status(entdict[pname]['valid']), str(entdict[pname]['expires']))
            product_status.append(data)
        else:
            product_status.append((pname, map_status(None), ""))
    return product_status

def getConsumedProductEntitlements():
    entdir = EntitlementDirectory()
    consumed_products = []
    for cert in entdir.listValid():
        data = (cert.getProduct().getName(), cert.valid(), cert.validRange().begin(), cert.validRange().end())
        consumed_products.append(data)
    return consumed_products

def getAvailableEntitlements(cpserver, consumer):
    columns  = ['quantity', 'consumed', 'endDate', 'productId']
    dlist = cpserver.getPoolsList(consumer)['pool']
    data = [_sub_dict(pool, columns) for pool in dlist]
    for d in data:
        d['quantity'] = int(d['quantity']) - int(d['consumed'])
        del d['consumed']
    print data
    return data

def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )

if __name__=='__main__':
    print("\nInstalled Product Status:\n")
    getInstalledProductStatus()
    print("\nConsumed Product Status:\n")
    getConsumedProductEntitlements()
    
