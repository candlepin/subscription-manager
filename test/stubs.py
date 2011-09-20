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

import StringIO
from rhsm import config
import random

# config file is root only, so just fill in a stringbuffer
cfg_buf = """
[foo]
bar =
[server]
hostname = server.example.conf
prefix = /candlepin
port = 8443
insecure = 1
ssl_verify_depth = 3
ca_cert_dir = /etc/rhsm/ca/
proxy_hostname =
proxy_port =
proxy_user =
proxy_password =

[rhsm]
baseurl= https://content.example.com
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer

[rhsmcertd]
certFrequency = 240
"""

test_config = StringIO.StringIO(cfg_buf)


class StubConfig(config.RhsmConfigParser):
    def __init__(self, config_file=None, defaults=config.DEFAULTS):
        config.RhsmConfigParser.__init__(self, config_file=config_file, defaults=defaults)
        self.raise_io = None
        self.fileName = config_file

    # isntead of reading a file, let's use the stringio
    def read(self, filename):
        self.readfp(test_config, "foo.conf")

    def set(self, section, key, value):
#        print self.sections()
        pass

    def save(self, config_file=None):
        if self.raise_io:
            raise IOError
        return None

    # replce read with readfp on stringio


def stubInitConfig():
    return StubConfig()

# create a global CFG object,then replace it with out own that candlepin
# read from a stringio
config.initConfig(config_file="test/rhsm.conf")
config.CFG = StubConfig()

# we are not actually reading test/rhsm.conf, it's just a placeholder
config.CFG.read("test/rhsm.conf")

from datetime import datetime, timedelta

from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory
from rhsm.certificate import EntitlementCertificate, Product, DateRange, \
        ProductCertificate, parse_tags, Content


class MockStdout:
    def __init__(self):
        self.buffer = ""

    def write(self, buf):
        self.buffer = self.buffer + buf

MockStderr = MockStdout


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

    def getHash(self):
        return self.hash


class StubOrder(object):

    # Start/end are formatted strings, not actual datetimes.
    def __init__(self, start, end, name="STUB NAME", quantity=None,
                 stacking_id=None, virt_only=None, socket_limit=1, sku=""):
        self.name = name
        self.start = start
        self.end = end
        self.quantity = quantity
        self.stacking_id = stacking_id
        self.virt_only = virt_only
        self.socket_limit = socket_limit
        self.sku = sku

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.end

    def getContract(self):
        return None

    def getAccountNumber(self):
        return None

    def getName(self):
        return self.name

    def getQuantityUsed(self):
        return self.quantity

    def getStackingId(self):
        return self.stacking_id

    def getSocketLimit(self):
        return self.socket_limit

    def getSku(self):
        return self.sku

    def getVirtOnly(self):
        return self.virt_only

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
        self.start_date = start_date
        if not start_date:
            self.start_date = datetime.now() - timedelta(days=100)
        self.end_date = end_date
        if not end_date:
            self.end_date = datetime.now() + timedelta(days=365)

    def getProduct(self):
        return self.product

    def getProducts(self):
        if self.product is None:
            return []
        prods = [self.product]
        if len(self.provided_products) > 0:
            prods.extend(self.provided_products)
        return prods

    def get_provided_tags(self):
        return self.provided_tags

    def validRange(self):
        return DateRange(self.start_date, self.end_date)

    def __str__(self):
        s = []
        s.append('StubCertificate:')
        s.append('===================================')
        for p in self.getProducts():
            s.append(str(p))
        return '\n'.join(s)


class StubEntitlementCertificate(StubProductCertificate, EntitlementCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None,
            order_end_date=None, content=None, quantity=1, stacking_id=None, sockets=2):
        StubProductCertificate.__init__(self, product, provided_products)

        self.start_date = start_date
        self.end_date = end_date
        if not start_date:
            self.start_date = datetime.now()
        if not end_date:
            self.end_date = self.start_date + timedelta(days=365)

        self.order_end_date = order_end_date
        if not order_end_date:
            self.order_end_date = self.end_date
        fmt = "%Y-%m-%dT%H:%M:%SZ"

        # to simulate a cert with no product
        sku = None
        if product:
            sku = product.hash
        self.order = StubOrder(self.start_date.strftime(fmt),
                               self.order_end_date.strftime(fmt), quantity=quantity,
                               stacking_id=stacking_id, socket_limit=sockets, sku=sku)

        self.valid_range = DateRange(self.start_date, self.end_date)
        self.content = []
        if content:
            self.content = content
        self.path = "/tmp/fake_ent_cert.pem"

    # Need to override this implementation to avoid requirement on X509:
    def validRangeWithGracePeriod(self):
        return DateRange(self.start_date, self.end_date)

    def validRange(self):
        return DateRange(self.start_date, self.order_end_date)

    def getContentEntitlements(self):
        return self.content

    def getRoleEntitlements(self):
        return []


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    path = "this/is/a/stub/cert/dir"
    def __init__(self, certificates):
        self.certs = certificates

    def list(self):
        return self.certs

    def _check_key(self, cert):
        """
        Fake filesystem access here so we don't try to read real keys.
        """
        return True

# so we can use a less confusing name when we use this stub
StubEntitlementDirectory = StubCertificateDirectory

class StubProductDirectory(StubCertificateDirectory, ProductDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    path = "this/is/a/stub"
    def __init__(self, certificates):
        StubCertificateDirectory.__init__(self, certificates)


class StubConsumerIdentity:
    CONSUMER_NAME = "John Q Consumer"
    CONSUMER_ID = "211211381984"

    def __init__(self, keystring, certstring):
        self.key = keystring
        self.cert = certstring

    @classmethod
    def existsAndValid(cls):
        return True

    @classmethod
    def exists(cls):
        return False

    def getConsumerName(self):
        return StubConsumerIdentity.CONSUMER_NAME

    def getConsumerId(self):
        return StubConsumerIdentity.CONSUMER_ID

    @classmethod
    def read(cls):
        return StubConsumerIdentity("", "")


class StubUEP:
    def __init__(self, username=None, password=None,
        proxy_hostname=None, proxy_port=None,
        proxy_user=None, proxy_password=None,
        cert_file=None, key_file=None):
            self.registered_consumer_info = {"uuid": 'dummy-consumer-uuid'}
            pass

    def supports_resource(self, resource):
        return False

    def registerConsumer(self, name, type, facts, owner, environment, keys,
            installed_products):
        return self.registered_consumer_info

    def getOwnerList(self, username):
        return [{'key': 'dummyowner'}]

    def updatePackageProfile(self, uuid, pkg_dicts):
        pass

    def getProduct(self):
        return {}


class StubBackend:
    def __init__(self, uep=StubUEP()):
        self.uep = uep
        pass

    def monitor_certs(self, callback):
        pass

    def monitor_identity(self, callback):
        pass

    def create_admin_uep(self, username, password):
        return StubUEP(username, password)


class StubFacts(object):
    def __init__(self, fact_dict, facts_changed=True):
        self.facts = fact_dict

        self.delta_values = {}
        # Simulate the delta as being the new set of facts provided.
        if facts_changed:
            self.delta_values = self.facts

    def get_facts(self):
        return self.facts

    def has_changed(self):
        return self.delta_values

    def update_check(self, uep, consumer_uuid, force=False):
        uep.updateConsumerFacts(consumer_uuid, self.facts)
