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

from datetime import datetime, timedelta

from certlib import EntitlementDirectory
from rhsm.certificate import EntitlementCertificate, Product, GMT, DateRange, \
        ProductCertificate

import random

class StubProduct(Product):

    def __init__(self, product_id, name=None, variant=None, arch=None, version=None):
        self.hash = product_id
        self.name = name
        if not name:
            self.name = product_id

        self.variant = variant
        if not variant:
            self.variant = "ALL" # ?

        self.arch = arch
        if not arch:
            self.arch = "x86_64"

        self.version = version
        if not version:
            self.version = "1.0"


class StubOrder(object):

    # Start/end are formatted strings, not actual datetimes.
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.end


class StubProductCertificate(ProductCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None):
        # TODO: product should be a StubProduct, check for strings coming in and error out
        self.product = product
        self.provided_products = provided_products
        if not provided_products:
            self.provided_products = []
        self.serial = random.randint(1, 10000000)

    def getProduct(self):
        return self.product

    def getProducts(self):
        prods = [self.product]
        if len(self.provided_products) > 0:
            prods.extend(self.provided_products)
        return prods


class StubEntitlementCertificate(StubProductCertificate, EntitlementCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None,
            order_end_date=None):
        StubProductCertificate.__init__(self, product, provided_products)

        self.start_date = start_date
        self.end_date = end_date
        if not start_date:
            self.start_date = datetime.now()
        if not end_date:
            self.end_date = self.start_date + timedelta(days=365)

        if not order_end_date:
            order_end_date = self.end_date
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        self.order = StubOrder(self.start_date.strftime(fmt),
                order_end_date.strftime(fmt))

        self.valid_range = DateRange(self.start_date, self.end_date)

    # Need to override this implementation to avoid requirement on X509:
    def validRangeWithGracePeriod(self):
        return DateRange(self.start_date, self.end_date)


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    def __init__(self, certificates):
        self.certs = certificates

    def list(self):
        return self.certs
