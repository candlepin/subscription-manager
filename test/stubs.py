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

from subscription_manager.certlib import EntitlementDirectory, ProductDirectory
from rhsm.certificate import EntitlementCertificate, Product, GMT, DateRange, \
        ProductCertificate, parse_tags, Content

import random

class StubProduct(Product):

    def __init__(self, product_id, name=None, version=None, arch=None, 
            provided_tags=None):
        """
        provided_tags - Comma separated list of tags this product (cert) 
            provides.
        """
        self.hash = product_id
        self.name = name
        if not name:
            self.name = product_id

        self.arch = arch
        if not arch:
            self.arch = "x86_64"

        self.provided_tags = parse_tags(provided_tags)

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

    def getContract(self):
        return None

    def getAccountNumber(self):
        return None


class StubContent(Content):

    def __init__(self, label, name=None, quantity=1, flex_quantity=1, vendor="", 
            url="", gpg="", enabled=1, metadata_expire=None, required_tags=""):
        self.label = label
        self.name = label
        if name:
            self.name = name
        self.quantity = quantity
        self.flex_quantity = flex_quantity
        self.vendor = vendor
        self.url = url
        self.gpg = gpg
        self.enabled = enabled
        self.metadata_expire = metadata_expire
        self.required_tags = parse_tags(required_tags)


class StubProductCertificate(ProductCertificate):

    def __init__(self, product, provided_products=None, start_date=None, 
            end_date=None, provided_tags=None):
        # TODO: product should be a StubProduct, check for strings coming in and error out
        self.product = product
        self.provided_products = []
        if provided_products:
            self.provided_products = provided_products

        self.provided_tags = set()
        if provided_tags:
            self.provided_tags = set(provided_tags)
        self.serial = random.randint(1, 10000000)

    def getProduct(self):
        return self.product

    def getProducts(self):
        prods = [self.product]
        if len(self.provided_products) > 0:
            prods.extend(self.provided_products)
        return prods

    def get_provided_tags(self):
        return self.provided_tags


class StubEntitlementCertificate(StubProductCertificate, EntitlementCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None,
            order_end_date=None, content=None):
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
        self.content = []
        if content:
            self.content = content
        self.path = "/tmp/fake_ent_cert.pem"

    # Need to override this implementation to avoid requirement on X509:
    def validRangeWithGracePeriod(self):
        return DateRange(self.start_date, self.end_date)

    def getContentEntitlements(self):
        return self.content

    def getRoleEntitlements(self):
        return []


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    def __init__(self, certificates):
        self.certs = certificates

    def list(self):
        return self.certs

    def listValid(self, grace_period=True):
        return self.certs


class StubProductDirectory(StubCertificateDirectory, ProductDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    def __init__(self, certificates):
        StubCertificateDirectory.__init__(self, certificates)


