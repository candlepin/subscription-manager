# Copyright (c) 2011 Red Hat, Inc.
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

import copy

import subscription_manager.injection as inj

from fixture import SubManFixture
from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubEntitlementDirectory, StubProductDirectory, \
    StubUEP, StubCertSorter
import subscription_manager.cert_sorter
from subscription_manager.cert_sorter import CertSorter, UNKNOWN
from subscription_manager.cache import EntitlementStatusCache
from datetime import timedelta, datetime
from mock import Mock, patch
from rhsm import ourjson as json


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.products:
            if product.id == product_id:
                return True
    return False


INST_PID_1 = "100000000000002"  # awesomeos 64
ENT_ID_1 = "ff8080813e468fd8013e4690966601d7"
INST_PID_2 = "100000000000003"  # ppc64 awesomeos
ENT_ID_2 = "ff8080813e468fd8013e4694a4921179"
INST_PID_3 = "801"  # non-entitled ram limiting product
INST_PID_4 = "900"  # multiattr stack
ENT_ID_4 = "ff8080813e468fd8013e4690f041031b"
STACK_1 = 'multiattr-stack-test'  # multiattr
STACK_2 = '1'  # awesomeos 64

PARTIAL_STACK_ID = STACK_1
PROD_4 = StubProduct(INST_PID_4,
        name="Multi-Attribute Stackable")
PROD_2 = StubProduct(INST_PID_2,
        name="Awesome OS for ppc64")
PROD_1 = StubProduct(INST_PID_1,
        name="Awesome OS for x86_64")


def stub_prod_cert(pid):
    return StubProductCertificate(StubProduct(pid))


class CertSorterTests(SubManFixture):

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def setUp(self, mock_update):
        SubManFixture.setUp(self)
        # Setup mock product and entitlement certs:
        self.prod_dir = StubProductDirectory(
                pids=[INST_PID_1, INST_PID_2, INST_PID_3, INST_PID_4])
        self.ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(PROD_2,
                ent_id=ENT_ID_2),
            StubEntitlementCertificate(PROD_1,
                ent_id=ENT_ID_1),
            StubEntitlementCertificate(product=PROD_4,
                stacking_id=STACK_1,
                ent_id=ENT_ID_4),
            # entitled, but not installed
            StubEntitlementCertificate(StubProduct('not_installed_product',
                name="Some Product"),
                ent_id="SomeSubId"),
            ])

        self.mock_uep = StubUEP()

        self.status_mgr = EntitlementStatusCache()
        self.status_mgr.load_status = Mock(
                return_value=SAMPLE_COMPLIANCE_JSON)
        self.status_mgr.write_cache = Mock()
        inj.provide(inj.ENTITLEMENT_STATUS_CACHE, self.status_mgr)
        inj.provide(inj.PROD_DIR, self.prod_dir)
        inj.provide(inj.ENT_DIR, self.ent_dir)
        self.sorter = CertSorter()
        self.sorter.is_registered = Mock(return_value=True)

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_unregistered_status(self, mock_update):
        sorter = CertSorter()
        sorter.is_registered = Mock(return_value=False)
        self.assertEqual(UNKNOWN, sorter.get_status(INST_PID_1))

    # Server doesn't support compliance API, or server is unreachable and
    # we cannot use the cache for some reason.
    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_no_usable_status(self, mock_update):
        self.status_mgr.load_status = Mock(
                return_value=None)
        sorter = CertSorter()
        sorter.is_registered = Mock(return_value=True)
        self.assertEqual(UNKNOWN, sorter.get_status(INST_PID_1))

    # Consumer has been deleted, overall status should be unknown
    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_deleted_consumer_status(self, mock_update):
        self.status_mgr.load_status = Mock(
                return_value=None)
        sorter = CertSorter()
        sorter.is_registered = Mock(return_value=True)
        expected = subscription_manager.cert_sorter.STATUS_MAP['unknown']
        self.assertEqual(expected, sorter.get_system_status())

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_unregistered_system_status(self, mock_update):
        self.status_mgr.load_status = Mock(
                return_value=None)
        sorter = CertSorter()
        sorter.is_registered = Mock(return_value=False)
        expected = subscription_manager.cert_sorter.STATUS_MAP['unknown']
        self.assertEqual(expected, sorter.get_system_status())

    def test_unentitled_products(self):
        self.assertEqual(1, len(self.sorter.unentitled_products))
        self.assertTrue(INST_PID_3 in self.sorter.unentitled_products)

    def test_valid_products(self):
        self.assertEqual(1, len(self.sorter.valid_products))
        self.assertTrue(INST_PID_1 in self.sorter.valid_products)

    def test_partially_valid_products(self):
        self.assertEqual(2, len(self.sorter.partially_valid_products))
        self.assertTrue(INST_PID_2 in
                self.sorter.partially_valid_products)
        self.assertTrue(INST_PID_4 in
                self.sorter.partially_valid_products)

    def test_installed_products(self):
        self.assertEqual(4, len(self.sorter.installed_products))
        self.assertTrue(INST_PID_1 in self.sorter.installed_products)
        self.assertTrue(INST_PID_2 in self.sorter.installed_products)
        self.assertTrue(INST_PID_3 in self.sorter.installed_products)
        self.assertTrue(INST_PID_3 in self.sorter.installed_products)

    def test_partial_stack(self):
        self.assertEqual(1, len(self.sorter.partial_stacks))
        self.assertTrue(PARTIAL_STACK_ID in self.sorter.partial_stacks)

    def test_reasons(self):
        self.assertEqual(5, len(self.sorter.reasons.reasons))
        expected_keys = ['NOTCOVERED', 'CORES', 'SOCKETS', 'RAM', 'ARCH']
        result_keys = [reason['key'] for reason in self.sorter.reasons.reasons]
        self.assertEqual(sorted(expected_keys), sorted(result_keys))

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_installed_mismatch_unentitled(self, mock_update):
        # Use a different product directory with something not present
        # in the response from the server as an unentitled product:
        prod_dir = StubProductDirectory(
                pids=[INST_PID_1, INST_PID_2])
        inj.provide(inj.PROD_DIR, prod_dir)
        sorter = CertSorter()
        self.assertFalse(INST_PID_3 in sorter.installed_products)
        # Should get filtered out of unentitled products even though
        # server reported it here:
        self.assertFalse(INST_PID_3 in sorter.unentitled_products)

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_missing_installed_product(self, mock_update):
        # Add a new installed product server doesn't know about:
        prod_dir = StubProductDirectory(pids=[INST_PID_1, INST_PID_2,
            INST_PID_3, "product4"])
        inj.provide(inj.PROD_DIR, prod_dir)
        sorter = CertSorter()
        self.assertTrue('product4' in sorter.unentitled_products)

    @patch('subscription_manager.cache.InstalledProductsManager.update_check')
    def test_no_compliant_until(self, mock_update):
        # don't want to munge the module scope version of this because
        # setup will load it for later tests
        no_compliance_until = copy.deepcopy(SAMPLE_COMPLIANCE_JSON)
        no_compliance_until['compliantUntil'] = None

        # build and inject a status cache with new values
        status_mgr = EntitlementStatusCache()
        status_mgr.load_status = Mock(return_value=no_compliance_until)
        status_mgr.write_cache = Mock()
        inj.provide(inj.ENTITLEMENT_STATUS_CACHE, status_mgr)

        self.sorter = CertSorter()
        self.sorter.is_registered = Mock(return_value=True)
        self.assertTrue(self.sorter.compliant_until is None)

    def test_compliant_until(self):
        compliant_until = self.sorter.compliant_until
        self.assertEqual(2013, compliant_until.year)
        self.assertEqual(4, compliant_until.month)
        self.assertEqual(26, compliant_until.day)
        self.assertEqual(13, compliant_until.hour)
        self.assertEqual(43, compliant_until.minute)
        self.assertEqual(12, compliant_until.second)

    def test_scan_for_expired_or_future_products(self):
        prod_dir = StubProductDirectory(pids=["a", "b", "c", "d", "e"])
        ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(StubProduct("a")),
            StubEntitlementCertificate(StubProduct("b")),
            StubEntitlementCertificate(StubProduct("c")),
            StubEntitlementCertificate(StubProduct("d"),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct("e"),
                start_date=datetime.now() + timedelta(days=365),
                end_date=datetime.now() + timedelta(days=730)),
            ])

        inj.provide(inj.PROD_DIR, prod_dir)
        inj.provide(inj.ENT_DIR, ent_dir)

        sorter = StubCertSorter()
        sorter.valid_products = {"a": StubProduct("a")}
        sorter.partially_valid_products = {"b": StubProduct("b")}

        sorter._scan_entitlement_certs()

        self.assertEqual(["d"], list(sorter.expired_products.keys()))
        self.assertEqual(["e"], list(sorter.future_products.keys()))

        self.assertEqual(3, len(sorter.valid_entitlement_certs))

    def test_get_system_status(self):
        self.assertEqual('Invalid', self.sorter.get_system_status())
        self.sorter.system_status = 'valid'
        self.assertEqual('Current', self.sorter.get_system_status())
        self.sorter.system_status = 'partial'
        self.assertEqual('Insufficient', self.sorter.get_system_status())


SAMPLE_COMPLIANCE_JSON = json.loads("""
{
  "date" : "2013-04-26T13:43:12.436+0000",
  "compliantUntil" : "2013-04-26T13:43:12.436+0000",
  "nonCompliantProducts" : [ "801" ],
  "compliantProducts" : {
    "100000000000002" : [ {
      "created" : "2013-04-26T13:41:56.688+0000",
      "updated" : "2013-04-26T13:41:56.688+0000",
      "id" : "ff8080813e468fd8013e46942f501173",
      "consumer" : null,
      "pool" : {
        "created" : "2013-04-26T13:38:29.296+0000",
        "updated" : "2013-04-26T13:41:56.688+0000",
        "id" : "ff8080813e468fd8013e469105300613",
        "owner" : {
          "id" : "ff8080813e468fd8013e468ff4c70002",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "ff8080813e468fd8013e4690809e018f",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 10,
        "startDate" : "2013-04-26T00:00:00.000+0000",
        "endDate" : "2014-04-26T00:00:00.000+0000",
        "productId" : "awesomeos-x86_64",
        "providedProducts" : [ {
          "id" : "ff8080813e468fd8013e46910531061c",
          "productId" : "100000000000002",
          "productName" : "Awesome OS for x86_64 Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "id" : null,
          "name" : "arch",
          "value" : "x86_64",
          "productId" : null
        }, {
          "id" : null,
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : null
        }, {
          "id" : null,
          "name" : "type",
          "value" : "MKT",
          "productId" : null
        }, {
          "id" : null,
          "name" : "stacking_id",
          "value" : "1",
          "productId" : null
        }, {
          "id" : null,
          "name" : "sockets",
          "value" : "1",
          "productId" : null
        }, {
          "id" : null,
          "name" : "version",
          "value" : "3.11",
          "productId" : null
        }, {
          "id" : null,
          "name" : "variant",
          "value" : "ALL",
          "productId" : null
        }, {
          "id" : null,
          "name" : "warning_period",
          "value" : "30",
          "productId" : null
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "79",
        "accountNumber" : "12331131231",
        "orderNumber" : "order-8675309",
        "consumed" : 3,
        "exported" : 0,
        "productName" : "Awesome OS for x86_64",
        "href" : "/pools/ff8080813e468fd8013e469105300613"
      },
      "startDate" : "2013-04-26T00:00:00.000+0000",
      "endDate" : "2014-04-26T00:00:00.000+0000",
      "certificates" : [ ],
      "quantity" : 3,
      "href" : "/entitlements/ff8080813e468fd8013e46942f501173"
    }, {
      "created" : "2013-04-26T13:41:28.554+0000",
      "updated" : "2013-04-26T13:41:28.554+0000",
      "id" : "ff8080813e468fd8013e4693c16a1170",
      "consumer" : null,
      "pool" : {
        "created" : "2013-04-26T13:38:29.320+0000",
        "updated" : "2013-04-26T13:41:28.554+0000",
        "id" : "ff8080813e468fd8013e46910548061d",
        "owner" : {
          "id" : "ff8080813e468fd8013e468ff4c70002",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "ff8080813e468fd8013e4690801e018e",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 5,
        "startDate" : "2013-04-26T00:00:00.000+0000",
        "endDate" : "2014-04-26T00:00:00.000+0000",
        "productId" : "awesomeos-x86_64",
        "providedProducts" : [ {
          "id" : "ff8080813e468fd8013e469105490627",
          "productId" : "100000000000002",
          "productName" : "Awesome OS for x86_64 Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "id" : null,
          "name" : "arch",
          "value" : "x86_64",
          "productId" : null
        }, {
          "id" : null,
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : null
        }, {
          "id" : null,
          "name" : "type",
          "value" : "MKT",
          "productId" : null
        }, {
          "id" : null,
          "name" : "stacking_id",
          "value" : "1",
          "productId" : null
        }, {
          "id" : null,
          "name" : "sockets",
          "value" : "1",
          "productId" : null
        }, {
          "id" : null,
          "name" : "version",
          "value" : "3.11",
          "productId" : null
        }, {
          "id" : null,
          "name" : "variant",
          "value" : "ALL",
          "productId" : null
        }, {
          "id" : null,
          "name" : "warning_period",
          "value" : "30",
          "productId" : null
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "78",
        "accountNumber" : "12331131231",
        "orderNumber" : "order-8675309",
        "consumed" : 5,
        "exported" : 0,
        "productName" : "Awesome OS for x86_64",
        "href" : "/pools/ff8080813e468fd8013e46910548061d"
      },
      "startDate" : "2013-04-26T00:00:00.000+0000",
      "endDate" : "2014-04-26T00:00:00.000+0000",
      "certificates" : [ ],
      "quantity" : 5,
      "href" : "/entitlements/ff8080813e468fd8013e4693c16a1170"
    } ]
  },
  "partiallyCompliantProducts" : {
    "100000000000003" : [ {
      "created" : "2013-04-26T13:42:26.706+0000",
      "updated" : "2013-04-26T13:42:26.706+0000",
      "id" : "ff8080813e468fd8013e4694a4921179",
      "consumer" : null,
      "pool" : {
        "created" : "2013-04-26T13:38:28.981+0000",
        "updated" : "2013-04-26T13:42:26.707+0000",
        "id" : "ff8080813e468fd8013e469103f505b6",
        "owner" : {
          "id" : "ff8080813e468fd8013e468ff4c70002",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "ff8080813e468fd8013e4690966601d7",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 10,
        "startDate" : "2013-04-26T00:00:00.000+0000",
        "endDate" : "2014-04-26T00:00:00.000+0000",
        "productId" : "awesomeos-ppc64",
        "providedProducts" : [ {
          "id" : "ff8080813e468fd8013e469103f505be",
          "productId" : "100000000000003",
          "productName" : "Awesome OS for ppc64 Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "id" : null,
          "name" : "sockets",
          "value" : "16",
          "productId" : null
        }, {
          "id" : null,
          "name" : "arch",
          "value" : "ppc64",
          "productId" : null
        }, {
          "id" : null,
          "name" : "type",
          "value" : "MKT",
          "productId" : null
        }, {
          "id" : null,
          "name" : "version",
          "value" : "3.11",
          "productId" : null
        }, {
          "id" : null,
          "name" : "variant",
          "value" : "ALL",
          "productId" : null
        }, {
          "id" : null,
          "name" : "warning_period",
          "value" : "30",
          "productId" : null
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "97",
        "accountNumber" : "12331131231",
        "orderNumber" : "order-8675309",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Awesome OS for ppc64",
        "href" : "/pools/ff8080813e468fd8013e469103f505b6"
      },
      "startDate" : "2013-04-26T00:00:00.000+0000",
      "endDate" : "2014-04-26T00:00:00.000+0000",
      "certificates" : [ ],
      "quantity" : 1,
      "href" : "/entitlements/ff8080813e468fd8013e4694a4921179"
    } ],
    "900" : [ {
      "created" : "2013-04-26T13:42:16.220+0000",
      "updated" : "2013-04-26T13:42:16.220+0000",
      "id" : "ff8080813e468fd8013e46947b9c1176",
      "consumer" : null,
      "pool" : {
        "created" : "2013-04-26T13:38:27.320+0000",
        "updated" : "2013-04-26T13:42:16.220+0000",
        "id" : "ff8080813e468fd8013e4690fd7803a4",
        "owner" : {
          "id" : "ff8080813e468fd8013e468ff4c70002",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "ff8080813e468fd8013e4690f041031b",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 5,
        "startDate" : "2013-04-26T00:00:00.000+0000",
        "endDate" : "2014-04-26T00:00:00.000+0000",
        "productId" : "sock-core-ram-multiattr",
        "providedProducts" : [ {
          "id" : "ff8080813e468fd8013e4690fd7903b0",
          "productId" : "900",
          "productName" : "Multi-Attribute Limited Product"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "id" : null,
          "name" : "cores",
          "value" : "16",
          "productId" : null
        }, {
          "id" : null,
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : null
        }, {
          "id" : null,
          "name" : "ram",
          "value" : "8",
          "productId" : null
        }, {
          "id" : null,
          "name" : "support_type",
          "value" : "Level 3",
          "productId" : null
        }, {
          "id" : null,
          "name" : "type",
          "value" : "MKT",
          "productId" : null
        }, {
          "id" : null,
          "name" : "arch",
          "value" : "ALL",
          "productId" : null
        }, {
          "id" : null,
          "name" : "stacking_id",
          "value" : "multiattr-stack-test",
          "productId" : null
        }, {
          "id" : null,
          "name" : "version",
          "value" : "1.0",
          "productId" : null
        }, {
          "id" : null,
          "name" : "support_level",
          "value" : "Super",
          "productId" : null
        }, {
          "id" : null,
          "name" : "sockets",
          "value" : "4",
          "productId" : null
        }, {
          "id" : null,
          "name" : "variant",
          "value" : "ALL",
          "productId" : null
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "204",
        "accountNumber" : "12331131231",
        "orderNumber" : "order-8675309",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)",
        "href" : "/pools/ff8080813e468fd8013e4690fd7803a4"
      },
      "startDate" : "2013-04-26T00:00:00.000+0000",
      "endDate" : "2014-04-26T00:00:00.000+0000",
      "certificates" : [ ],
      "quantity" : 1,
      "href" : "/entitlements/ff8080813e468fd8013e46947b9c1176"
    } ]
  },
  "partialStacks" : {
    "multiattr-stack-test" : [ {
      "created" : "2013-04-26T13:42:16.220+0000",
      "updated" : "2013-04-26T13:42:16.220+0000",
      "id" : "ff8080813e468fd8013e46947b9c1176",
      "consumer" : null,
      "pool" : {
        "created" : "2013-04-26T13:38:27.320+0000",
        "updated" : "2013-04-26T13:42:16.220+0000",
        "id" : "ff8080813e468fd8013e4690fd7803a4",
        "owner" : {
          "id" : "ff8080813e468fd8013e468ff4c70002",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "ff8080813e468fd8013e4690f041031b",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 5,
        "startDate" : "2013-04-26T00:00:00.000+0000",
        "endDate" : "2014-04-26T00:00:00.000+0000",
        "productId" : "sock-core-ram-multiattr",
        "providedProducts" : [ {
          "id" : "ff8080813e468fd8013e4690fd7903b0",
          "productId" : "900",
          "productName" : "Multi-Attribute Limited Product"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "id" : null,
          "name" : "cores",
          "value" : "16",
          "productId" : null
        }, {
          "id" : null,
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : null
        }, {
          "id" : null,
          "name" : "ram",
          "value" : "8",
          "productId" : null
        }, {
          "id" : null,
          "name" : "support_type",
          "value" : "Level 3",
          "productId" : null
        }, {
          "id" : null,
          "name" : "type",
          "value" : "MKT",
          "productId" : null
        }, {
          "id" : null,
          "name" : "arch",
          "value" : "ALL",
          "productId" : null
        }, {
          "id" : null,
          "name" : "stacking_id",
          "value" : "multiattr-stack-test",
          "productId" : null
        }, {
          "id" : null,
          "name" : "version",
          "value" : "1.0",
          "productId" : null
        }, {
          "id" : null,
          "name" : "support_level",
          "value" : "Super",
          "productId" : null
        }, {
          "id" : null,
          "name" : "sockets",
          "value" : "4",
          "productId" : null
        }, {
          "id" : null,
          "name" : "variant",
          "value" : "ALL",
          "productId" : null
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "204",
        "accountNumber" : "12331131231",
        "orderNumber" : "order-8675309",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)",
        "href" : "/pools/ff8080813e468fd8013e4690fd7803a4"
      },
      "startDate" : "2013-04-26T00:00:00.000+0000",
      "endDate" : "2014-04-26T00:00:00.000+0000",
      "certificates" : [ ],
      "quantity" : 1,
      "href" : "/entitlements/ff8080813e468fd8013e46947b9c1176"
    } ]
  },
  "reasons" : [ {
    "key" : "NOTCOVERED",
    "message" : "The system does not have subscriptions that cover RAM Limiting Product.",
    "attributes" : {
      "product_id" : "801",
      "name" : "RAM Limiting Product"
    }
  }, {
    "key" : "CORES",
    "message" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM) only covers 16 of 32 cores.",
    "attributes" : {
      "has" : "32",
      "covered" : "16",
      "stack_id" : "multiattr-stack-test",
      "name" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)"
    }
  }, {
    "key" : "SOCKETS",
    "message" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM) only covers 4 of 8 sockets.",
    "attributes" : {
      "has" : "8",
      "covered" : "4",
      "stack_id" : "multiattr-stack-test",
      "name" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)"
    }
  }, {
    "key" : "RAM",
    "message" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM) only covers 8GB of 31GB of RAM.",
    "attributes" : {
      "has" : "31",
      "covered" : "8",
      "stack_id" : "multiattr-stack-test",
      "name" : "Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)"
    }
  }, {
    "key" : "ARCH",
    "message" : "Awesome OS for ppc64 covers architecture ppc64 but the system is x86_64.",
    "attributes" : {
      "has" : "x86_64",
      "covered" : "ppc64",
      "entitlement_id" : "ff8080813e468fd8013e4694a4921179",
      "name" : "Awesome OS for ppc64"
    }
  } ],
  "status" : "invalid",
  "compliant" : false
}
""")
