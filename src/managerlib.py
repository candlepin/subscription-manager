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

from certlib import CertLib, ConsumerIdentity, \
                    ProductDirectory, EntitlementDirectory

def getInstalledProductStatus():
    products = ProductDirectory().list()
    entcerts = EntitlementDirectory().listValid()
    entdict = {}
    for cert in entcerts:
        ents = cert.getEntitlements()
        entdict[cert.getProduct().getName()] = {'Entitlements' : ents, 
                                                'valid': cert.valid(), 
                                                'expires' : cert.validRange().end()}
    product_status = []
    columns = ("Product Installed", "Status", "Expires")
    print("\t%-25s \t%-20s \t%-10s" % columns)
    print "%s" % "--" * len('\t\t'.join(columns))
    for product in products:
        pname = product.getProduct().getName()
        if entdict.has_key(pname):
            data = (pname, entdict[pname]['valid'], entdict[pname]['expires'])
            print("\t%-25s \t%-20s \t%-10s" % data)
            product_status.append(data)
    return product_status

def getConsumedProductEntitlements():
    entdir = EntitlementDirectory()
    columns = ("SerialNumber", "Product Consumed", "Expires")
    print("\t%-10s \t%-25s \t%-10s" % columns)
    print "%s" % "--" * len('\t\t'.join(columns))
    consumed_products = []
    for cert in entdir.listValid():
        data = (cert.serialNumber(), cert.getProduct().getName(), cert.validRange().end())
        print("\t%-10s \t%-25s \t%-10s" % data)
        consumed_products.append(data)
    return consumed_products

if __name__=='__main__':
    print("\nInstalled Product Status:\n")
    getInstalledProductStatus()
    print("\nConsumed Product Status:\n")
    getConsumedProductEntitlements()
