from __future__ import print_function, division, absolute_import

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

from collections import defaultdict
from datetime import datetime, timedelta
import six
import mock
import random
import tempfile

from rhsm import config
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.cache import EntitlementStatusCache, ProductStatusCache, \
        OverrideStatusCache, ProfileManager, InstalledProductsManager, ReleaseStatusCache, \
        PoolStatusCache
from subscription_manager.facts import Facts
from subscription_manager.lock import ActionLock
from rhsm.certificate import GMT
from subscription_manager.gui.utils import AsyncWidgetUpdater, handle_gui_exception
from rhsm.certificate2 import Version
from subscription_manager.certdirectory import EntitlementDirectory, ProductDirectory

from rhsm.certificate import parse_tags
from rhsm.certificate2 import EntitlementCertificate, ProductCertificate, \
        Product, Content, Order
from rhsm import profile
from rhsm import ourjson as json
from rhsm.certificate2 import CONTENT_ACCESS_CERT_TYPE

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
proxy_hostname = notaproxy.grimlock.usersys.redhat.com
proxy_port = 4567
proxy_user = proxy_user
proxy_password = proxy_password
no_proxy =

[rhsm]
baseurl = https://content.example.com
repomd_gpg_url =
repo_ca_cert = %(ca_cert_dir)sredhat-uep.pem
productCertDir = /etc/pki/product
entitlementCertDir = /etc/pki/entitlement
consumerCertDir = /etc/pki/consumer
ca_cert_dir = /etc/rhsm/ca/

[rhsmcertd]
certCheckInterval = 240

[logging]
default_log_level = DEBUG
"""


class StubConfig(config.RhsmConfigParser):
    def __init__(self, config_file=None, defaults=None):
        defaults = defaults or config.DEFAULTS
        config.RhsmConfigParser.__init__(self, config_file=config_file, defaults=defaults)
        self.raise_io = None
        self.fileName = config_file
        self.store = defaultdict(dict)

    # instead of reading a file, let's use the stringio
    def read(self, filename):
        self.readfp(six.StringIO(cfg_buf), "foo.conf")

    # this way our test can put some values in and have them used during the run
    def get(self, section, key):
        # print self.sections()
        value = super(StubConfig, self).get(section, key)
        test_value = None
        try:
            test_value = self.store[section][key]
        except KeyError:
            test_value = None

        if test_value:
            return test_value
        else:
            return value

    def set(self, section, key, value):
        # print self.sections()
        self.store[section][key] = value

    def items(self, section):
        # Attempt to return the items from the store for the given section.
        # This allows tests using this stub to set arbitrary keys in a given
        # section and iterate over them with their values.
        items_from_store = self.store[section]
        if len(items_from_store) > 0:
            return list(items_from_store.items())
        return config.RhsmConfigParser.items(self, section)

    def save(self, config_file=None):
        if self.raise_io:
            raise IOError
        return None


def stubInitConfig():
    return StubConfig()


# create a global CFG object,then replace it with our own that candlepin
# read from a stringio
config.initConfig(config_file="test/rhsm.conf")
config.CFG = StubConfig()

# we are not actually reading test/rhsm.conf, it's just a placeholder
config.CFG.read("test/rhsm.conf")


class MockActionLock(ActionLock):
    PATH = tempfile.mkstemp()[1]


class StubProduct(Product):

    def __init__(self, product_id, name=None, version=None,
                 architectures=None, provided_tags=None,
                 os=None, brand_name=None):

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

        super(StubProduct, self).__init__(id=product_id, name=name, version=version,
                                          architectures=architectures,
                                          provided_tags=provided_tags,
                                          brand_type=os, brand_name=brand_name)


class StubContent(Content):

    def __init__(self, label, name=None, vendor="",
            url="", gpg="", enabled=1, metadata_expire=None, required_tags="",
            content_type="yum"):
        name = label
        if name:
            name = name
        if required_tags:
            required_tags = parse_tags(required_tags)
        super(StubContent, self).__init__(content_type=content_type, name=name, label=label,
                                          vendor=vendor, url=url, gpg=gpg, enabled=enabled,
                                          metadata_expire=metadata_expire,
                                          required_tags=required_tags)


class StubProductCertificate(ProductCertificate):

    def __init__(self, product, provided_products=None, start_date=None,
            end_date=None, provided_tags=None):

        products = [product]
        if provided_products:
            products = products + provided_products

        self.name = product.name

        # product certs are all version 1.0
        version = Version("1.0")

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

        path = "/path/to/fake_product.pem"

        super(StubProductCertificate, self).__init__(products=products,
                                                     serial=random.randint(1, 10000000),
                                                     start=start_date, end=end_date,
                                                     version=version, path=path)

    def __str__(self):
        s = []
        s.append('StubProductCertificate:')
        s.append('===================================')
        for p in self.products:
            s.append(str(p))
        return '\n'.join(s)


class StubEntitlementCertificate(EntitlementCertificate):

    def __init__(self, product, provided_products=None, start_date=None, end_date=None,
            content=None, quantity=1, stacking_id=None, sockets=2, service_level=None,
            ram=None, pool=None, ent_id=None, entitlement_type=None):

        # If we're given strings, create stub products for them:
        if isinstance(product, str):
            product = StubProduct(product)
        if provided_products:
            temp = []
            for p in provided_products:
                temp.append(StubProduct(p))
            provided_products = temp

        products = []
        if product:
            products.append(product)
        if provided_products:
            products = products + provided_products

        if not start_date:
            start_date = datetime.utcnow()
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
                    service_level=service_level, quantity_used=quantity,
                    ram_limit=ram)
        order.warning_period = 42

        if content is None:
            content = []

        path = "/tmp/fake_ent_cert.pem"
        self.is_deleted = False

        # might as well make this a big num since live serials #'s are already > maxint
        self.serial = random.randint(1000000000000000000, 10000000000000000000000)
        # write these to tmp, could we abuse PATH thing in certs for tests?

        path = "/tmp/fake_ent_cert-%s.pem" % self.serial
        super(StubEntitlementCertificate, self).__init__(path=path, products=products, order=order,
                                                         content=content, pool=pool, start=start_date,
                                                         end=end_date, serial=self.serial)
        if ent_id:
            self.subject = {'CN': ent_id}

        self._entitlement_type = entitlement_type or 'Basic'

    @property
    def entitlement_type(self):
        return self._entitlement_type

    def delete(self):
        self.is_deleted = True

    def is_expiring(self, on_date=None):
        gmt = datetime.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        warning_time = timedelta(days=int(self.order.warning_period))
        return self.valid_range.end() - warning_time < gmt


class StubCertificateDirectory(EntitlementDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    path = "this/is/a/stub/cert/dir"
    expired = False

    def __init__(self, certificates=None):
        self.certs = certificates
        if certificates is None:
            self.certs = []
        self.list_called = False

    def list(self):
        self.list_called = True
        return self.certs

    def _check_key(self, cert):
        """
        Fake filesystem access here so we don't try to read real keys.
        """
        return True

    def getCerts(self):
        return self.certs


# so we can use a less confusing name when we use this stub
class StubEntitlementDirectory(StubCertificateDirectory):
    path = "this/is/a/stub/ent/cert/dir"

    def list_valid_with_content_access(self):
        return [x for x in self.list_with_content_access() if self._check_key(x) and x.is_valid()]

    def list(self):
        certs = super(StubEntitlementDirectory, self).list()
        return [cert for cert in certs if cert.entitlement_type != CONTENT_ACCESS_CERT_TYPE]

    def list_with_content_access(self):
        return super(StubEntitlementDirectory, self).list()


class StubProductDirectory(StubCertificateDirectory, ProductDirectory):
    """
    Stub for mimicing behavior of an on-disk certificate directory.
    Can be used for both entitlement and product directories as needed.
    """

    path = "this/is/a/stub/product/cert/dir"

    def __init__(self, certificates=None, pids=None):
        """
        Pass list of product ID strings instead of certificates to have
        stub product certs created for you.
        """
        if pids is not None:
            certificates = []
            for pid in pids:
                certificates.append(StubProductCertificate(StubProduct(pid)))
        super(StubProductDirectory, self).__init__(certificates)

    # real version just calls refresh on it's set of ProductDirs, that don't
    # exist here, so this needs to be stubbed.
    def refresh(self):
        pass


class StubConsumerIdentity(object):
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
    def certpath(cls):
        return ""

    @classmethod
    def keypath(cls):
        return ""


class StubUEP(object):
    def __init__(self, host=None, ssl_port=None, handler=None,
                 username=None, password=None,
                 proxy_hostname=None, proxy_port=None,
                 proxy_user=None, proxy_password=None,
                 cert_file=None, key_file=None, restlib_class=None):
        self.registered_consumer_info = {"uuid": 'dummy-consumer-uuid'}
        self.environment_list = []
        self.called_unregister_uuid = None
        self.called_unbind_uuid = None
        self.called_unbind_serial = []
        self.called_unbind_pool_id = []
        self.username = username
        self.password = password
        self._resources = []
        self._capabilities = []

    def reset(self):
        self.called_unregister_uuid = None
        self.called_unbind_uuid = None
        self.called_unbind_serial = []
        self.called_unbind_pool_id = []

    def has_capability(self, capability):
        return capability in self._capabilities

    def supports_resource(self, resource):
        return resource in self._resources

    def get_supported_resources(self):
        return self._resources

    def registerConsumer(self, name, type, facts, owner, environment, keys,
                         installed_products, content_tags):
        return self.registered_consumer_info

    def unregisterConsumer(self, uuid):
        self.called_unregister_uuid = uuid

    def getOwnerList(self, username):
        return [{'key': 'dummyowner'}]

    def getOwner(self, consumer_uuid):
        return {'key': 'dummyowner'}

    def updatePackageProfile(self, uuid, pkg_dicts):
        pass

    def getProduct(self):
        return {}

    def getRelease(self, consumerId):
        return {'releaseVer': ''}

    def getServiceLevelList(self, owner):
        return ['Pro', 'Super Pro', 'ProSumer']

    def updateConsumer(self, consumer, facts=None, installed_products=None,
                       guest_uuids=None, service_level=None, release=None, autoheal=None,
                       content_tags=None, addons=None, role=None, usage=None):
        return consumer

    def setEnvironmentList(self, env_list):
        self.environment_list = env_list

    def getEnvironmentList(self, owner):
        return self.environment_list

    def setConsumer(self, consumer):
        self.consumer = consumer

    def getConsumer(self, consumerId, username=None, password=None):
        if hasattr(self, 'consumer') and self.consumer:
            return self.consumer
        if six.callable(self.registered_consumer_info):
            return self.registered_consumer_info()
        return self.registered_consumer_info

    def unbindAll(self, consumer):
        self.called_unbind_uuid = consumer

    def unbindBySerial(self, consumer, serial):
        self.called_unbind_serial.append(serial)

    def unbindByPoolId(self, consumer_uuid, pool_id):
        self.called_unbind_pool_id.append(pool_id)

    def getCertificateSerials(self, consumer):
        return []

    def getCompliance(self, uuid, on_data=None):
        return {}

    def getSyspurposeCompliance(self, uuid, on_date=None):
        return self.syspurpose_compliance_status

    def setSyspurposeCompliance(self, status):
        self.syspurpose_compliance_status = status

    def getEntitlementList(self, uuid):
        return [{'id': 'ent1'}, {'id': 'ent2'}]

    def getPoolsList(self, uuid, listAll, active_on, owner):
        return [{'id': 'pool1'}, {'id': 'pool2'}]

    def getSubscriptionList(self, owner):
        return [{'id': 'sub1'}, {'id': 'sub2'}]

    def getContentOverrides(self, uuid):
        return []


class StubBackend(object):
    def __init__(self, uep=None):
        self.cp_provider = StubCPProvider()
        self.entitlement_dir = None
        self.product_dir = None
        self.content_connection = None
        self.cs = StubCertSorter()
        self.overrides = None
        self.certlib = None

    def on_cert_check_timer(self):
        pass

    def update(self):
        pass


class StubContentConnection(object):
    proxy_hostname = None
    proxy_port = None


class StubFacts(Facts):
    def __init__(self, fact_dict=None, facts_changed=True):
        fact_dict = fact_dict or {}
        self.facts = fact_dict

        self.delta_values = {}
        # Simulate the delta as being the new set of facts provided.
        if facts_changed:
            self.delta_values = self.facts

    def get_facts(self, refresh=True):
        return self.facts

    def has_changed(self):
        return self.delta_values

    def update_check(self, uep, consumer_uuid, force=False):
        uep.updateConsumer(consumer_uuid, self.facts)

    def get_last_update(self):
        return None

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubConsumer(object):
    def __init__(self):
        self.uuid = None

    def is_valid(self):
        return True

    def reload(self):
        pass

    def getConsumerId(self):
        return "12341234234"


class StubEntActionInvoker(object):
    def __init__(self, uep=None):
        self.uep = uep or StubUEP()

    def update(self):
        pass


class StubCertSorter(CertSorter):

    def __init__(self):
        super(StubCertSorter, self).__init__()

    def update_product_manager(self):
        pass

    def _parse_server_status(self):
        # Override this method to just leave all fields uninitialized so
        # tests can do whatever they wish with them.
        pass


class StubCPProvider(object):

    def __init__(self):
        self.cert_file = StubConsumerIdentity.certpath()
        self.key_file = StubConsumerIdentity.keypath()
        self.consumer_auth_cp = StubUEP()
        self.basic_auth_cp = StubUEP()
        self.no_auth_cp = StubUEP()
        self.content_connection = StubContentConnection()

    def set_connection_info(self,
        host=None,
        ssl_port=None,
        handler=None,
        cert_file=None,
        key_file=None,
        proxy_hostname_arg=None,
        proxy_port_arg=None,
        proxy_user_arg=None,
        proxy_password_arg=None,
        no_proxy_arg=None,
        correlation_id=None,
        restlib_class=None):
        pass

    def set_content_connection_info(self, cdn_hostname=None, cdn_port=None):
        pass

    def set_user_pass(self, username=None, password=None):
        pass

    def set_correlation_id(self, correlation_id):
        pass

    # tries to write to /var/lib and it reads the rpm db
    def clean(self):
        pass

    def get_consumer_auth_cp(self):
        return self.consumer_auth_cp

    def get_basic_auth_cp(self):
        return self.basic_auth_cp

    def get_no_auth_cp(self):
        return self.no_auth_cp

    def get_content_connection(self):
        return self.content_connection


class StubEntitlementStatusCache(EntitlementStatusCache):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubPoolStatusCache(PoolStatusCache):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubProductStatusCache(ProductStatusCache):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubOverrideStatusCache(OverrideStatusCache):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubReleaseStatusCache(ReleaseStatusCache):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubPool(object):

    def __init__(self, poolid):
        self.id = poolid


class StubAsyncUpdater(AsyncWidgetUpdater):

    def update(self, widget_update, backend_method, args=[], kwargs={}, exception_msg=None, callback=None):
        try:
            result = backend_method(*args, **kwargs)
            if callback:
                callback(result)
        except Exception as e:
            message = exception_msg or str(e)
            handle_gui_exception(e, message, self.parent_window)
        finally:
            widget_update.finished()


class StubInstalledProductsManager(InstalledProductsManager):
    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None


class StubProfileManager(ProfileManager):

    def write_cache(self):
        pass

    def delete_cache(self):
        self.server_status = None

    def _get_current_profile(self):
        mock_packages = [
                  profile.Package(name="package1", version="1.0.0", release=1, arch="x86_64"),
                  profile.Package(name="package2", version="2.0.0", release=2, arch="x86_64")]
        self._current_profile = StubRpmProfile(mock_packages=mock_packages)
        return self._current_profile

    # NOTE: ProfileManager asks the ether for it's profile, so
    # stub that as well
    def _get_profile(self, profile_type):
        return self._get_current_profile()


# could be a Mock
class StubRpmProfile(profile.RPMProfile):
    def __init__(self, from_file=None, mock_packages=None):
        self.mock_packages = mock_packages
        mock_file = self._mock_pkg_profile_file()

        # create an RPMProfile from the mock_packages list
        super(StubRpmProfile, self).__init__(from_file=mock_file)

    def _get_packages(self):
        """return a list of profile.Package objects"""
        if self.mock_packages:
            return self.mock_packages
        return []

    def _mock_pkg_profile_file(self):
        """
        Turn a list of package objects into an RPMProfile object.
        """

        packages = self._get_packages()
        dict_list = []
        for pkg in packages:
            dict_list.append(pkg.to_dict())

        mock_file = mock.Mock()
        mock_file.read = mock.Mock(return_value=json.dumps(dict_list))

        return mock_file
