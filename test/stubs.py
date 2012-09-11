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
import random
import tempfile


from datetime import datetime, timedelta

from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory
from subscription_manager.certlib import ActionLock
from rhsm.certificate import parse_tags, Content
from rhsm.certificate2 import EntitlementCertificate, ProductCertificate, \
        Product, Content, Order


class MockActionLock(ActionLock):
    PATH = tempfile.mkstemp()[1]

    def __init__(self):
        ActionLock.__init__(self)


class MockStdout:
    def __init__(self):
        self.buffer = ""

    def write(self, buf):
        self.buffer = self.buffer + buf

    @staticmethod
    def isatty(buf):
        return False


MockStderr = MockStdout


class StubProduct(Product):

    def __init__(self, product_id, name=None, version=None, architectures=None,
            provided_tags=None):

        # Initialize some defaults:
        if not name:
            name = product_id

        if not architectures:
            architectures = ["x86_64"]

        if not version:
            version = "1.0"

        # Tests sadly pass these in as a flat string. # TODO
        if provided_tags:
            provided_tags = parse_tags(provided_tags)

        Product.__init__(self, id=product_id, name=name, version=version,
                architectures=architectures, provided_tags=provided_tags)


class StubContent(Content):

    def __init__(self, label, name=None, vendor="",
            url="", gpg="", enabled=1, metadata_expire=None, required_tags=""):
        name = label
        if name:
            name = name
        if required_tags:
            required_tags = parse_tags(required_tags)
        Content.__init__(self, name=name, label=label,
                vendor=vendor, url=url, gpg=gpg, enabled=enabled,
                metadata_expire=metadata_expire, required_tags=required_tags)


class StubProductCertificate(ProductCertificate):

    def __init__(self, product, provided_products=None, start_date=None,
            end_date=None, provided_tags=None):

        products = [product]
        if provided_products:
            products = products + provided_products

        # TODO: product should be a StubProduct, check for strings coming in and error out
        self.product = product
        self.provided_products = []
        if provided_products:
            self.provided_products = provided_products

        self.provided_tags = set()
        if provided_tags:
            self.provided_tags = set(provided_tags)

        if not start_date:
            start_date = datetime.now() - timedelta(days=100)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)

        ProductCertificate.__init__(self, products=products,
                serial=random.randint(1, 10000000),
                start=start_date,
                end=end_date)

    def __str__(self):
        s = []
        s.append('StubProductCertificate:')
        s.append('===================================')
        for p in self.products:
            s.append(str(p))
        return '\n'.join(s)


class StubEntitlementCertificate(EntitlementCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None,
            content=None, quantity=1, stacking_id=None, sockets=2,
            service_level=None):

        products = []
        if product:
            products.append(product)
        if provided_products:
            products = products + provided_products

        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=365)

        # to simulate a cert with no product
        sku = None
        name = None
        if product:
            sku = product.id
            name = product.name
        order = Order(name=name, number="592837", sku=sku,
                    stacking_id=stacking_id, socket_limit=sockets,
                    service_level=service_level, quantity_used=quantity)

        if content is None:
            content = []

        path = "/tmp/fake_ent_cert.pem"
        self.is_deleted = False

        # might as well make this a big num since live serials #'s are already > maxint
        self.serial = random.randint(1000000000000000000, 10000000000000000000000)
        # write these to tmp, could we abuse PATH thing in certs for tests?

        path = "/tmp/fake_ent_cert-%s.pem" % self.serial
        EntitlementCertificate.__init__(self, path=path, products=products,
                order=order, content=content, start=start_date, end=end_date,
                serial=self.serial)

    def delete(self):
        self.is_deleted = True


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    path = "this/is/a/stub/cert/dir"
    expired = False

    def __init__(self, certificates):
        self.certs = certificates
        self.list_called = False

    def list(self):
        self.list_called = True
        return self.certs

    def listExpired(self):
        if self.expired:
            return self.certs
        return []

    def _check_key(self, cert):
        """
        Fake filesystem access here so we don't try to read real keys.
        """
        return True

    def getCerts(self):
        return self.certs

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
    SERIAL = "23234523452345234523453453434534534"

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

    def getSerialNumber(self):
        return StubConsumerIdentity.SERIAL

    @classmethod
    def read(cls):
        return StubConsumerIdentity("", "")

    @classmethod
    def certpath(self):
        return ""

    @classmethod
    def keypath(self):
        return ""


class StubUEP:
    def __init__(self, host=None, ssl_port=None, handler=None,
                 username=None, password=None,
                 proxy_hostname=None, proxy_port=None,
                 proxy_user=None, proxy_password=None,
                 cert_file=None, key_file=None):
            self.registered_consumer_info = {"uuid": 'dummy-consumer-uuid'}
            self.environment_list = []
            self.called_unregister_uuid = None
            self.called_unbind_uuid = None
            self.called_unbind_serial = None
            pass

    def supports_resource(self, resource):
        return False

    def registerConsumer(self, name, type, facts, owner, environment, keys,
                         installed_products):
        return self.registered_consumer_info

    def unregisterConsumer(self, uuid):
        self.called_unregister_uuid = uuid

    def getOwnerList(self, username):
        return [{'key': 'dummyowner'}]

    def updatePackageProfile(self, uuid, pkg_dicts):
        pass

    def getProduct(self):
        return {}

    def getRelease(self, consumerId):
        return {'releaseVer': ''}

    def getServiceLevelList(self, owner):
        return ['Pro', 'Super Pro', 'ProSumer']

    def updateConsumer(self, consumer, service_level=None, release=None):
        return consumer

    def setEnvironmentList(self, env_list):
        self.environment_list = env_list

    def getEnvironmentList(self, owner):
        return self.environment_list

    def setConsumer(self, consumer):
        self.consumer = consumer

    def getConsumer(self, consumerId):
        return self.consumer

    def unbindAll(self, consumer):
        self.called_unbind_uuid = consumer

    def unbindBySerial(self, consumer, serial):
        self.called_unbind_serial = serial

    def getCertificateSerials(self, consumer):
        print "getCertificateSerials"
        return []


class StubBackend:
    def __init__(self, uep=StubUEP()):
        self.uep = uep
        self.entitlement_dir = None
        self.product_dir = None
        self.content_connection = None

    def monitor_certs(self, callback):
        pass

    def monitor_identity(self, callback):
        pass

    def create_admin_uep(self, username, password):
        return StubUEP(username, password)

    def update(self):
        pass


class StubContentConnection:
    def __init__(self):
        pass


class StubFacts(object):
    def __init__(self, fact_dict={}, facts_changed=True):
        self.facts = fact_dict

        self.delta_values = {}
        # Simulate the delta as being the new set of facts provided.
        if facts_changed:
            self.delta_values = self.facts

    def get_facts(self, refresh=True):
        return self.facts

    def refresh_validity_facts(self):
        pass

    def has_changed(self):
        return self.delta_values

    def update_check(self, uep, consumer_uuid, force=False):
        uep.updateConsumerFacts(consumer_uuid, self.facts)

    def get_last_update(self):
        return None


class StubConsumer:
    def __init__(self):
        self.uuid = None

    def is_valid(self):
        return True

    def reload(self):
        pass

    def getConsumerId(self):
        return "12341234234"


class StubCertLib:
    def __init__(self, uep=StubUEP()):
        self.uep = uep

    def update(self):
        pass
