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
from certificate import Certificate, Product, GMT, DateRange

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


# TODO: inherit from Certificate, will need a refactor:
class StubProductCertificate(object):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None):
        self.product = product
        self.provided_products = provided_products
        if not provided_products:
            self.provided_products = []

    def getProduct(self):
        return self.product

    def getProducts(self):
        prods = [self.product]
        if len(self.provided_products) > 0:
            prods.extend(self.prods)
        return prods

class StubEntitlementCertificate(StubProductCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None):
        StubProductCertificate.__init__(self, product, provided_products)

        self.start_date = start_date
        self.end_date = end_date
        if not start_date:
            self.start_date = datetime.now()
        if not end_date:
            self.end_date = start_date + timedelta(days=365)

    def validRange(self):
        return DateRange(self.start_date, self.end_date)

    def valid(self):
        return self.start_date < datetime.now() < self.end_date


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    def __init__(self, certificates):
        self.certs = certificates

    def list(self):
        return self.certs
