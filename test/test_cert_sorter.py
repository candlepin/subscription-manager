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

from fixture import SubManFixture
from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubEntitlementDirectory, StubProductDirectory, \
    StubUEP, StubCertSorter
from subscription_manager.cert_sorter import CertSorter, UNKNOWN
from rhsm.connection import RestlibException
from datetime import timedelta, datetime
from mock import Mock
import simplejson as json

SAMPLE_COMPLIANCE_JSON = json.loads("""
{
  "date" : "2013-02-27T16:03:42.509+0000",
  "compliantUntil" : "2013-02-27T16:03:42.509+0000",
  "nonCompliantProducts" : [ "69" ],
  "compliantProducts" : {
    "37060" : [ {
      "created" : "2013-02-27T16:03:18.111+0000",
      "updated" : "2013-02-27T16:03:18.111+0000",
      "id" : "402881983d17fabf013d1c64c1df0b7a",
      "consumer" : {
        "id" : "402881983d17fabf013d1c5c98810b70",
        "uuid" : "4bb47522-df95-46c2-ac23-c4532faf6d8d",
        "name" : "lenovo.local.rm-rf.ca",
        "href" : "/consumers/4bb47522-df95-46c2-ac23-c4532faf6d8d"
      },
      "pool" : {
        "created" : "2013-02-26T19:30:06.708+0000",
        "updated" : "2013-02-27T16:03:18.119+0000",
        "id" : "402881983d17fabf013d17fbbcf40363",
        "owner" : {
          "id" : "402881983d17fabf013d17fae23d005d",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "402881983d17fabf013d17fb94510241",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 5,
        "startDate" : "2013-02-26T00:00:00.000+0000",
        "endDate" : "2014-02-26T00:00:00.000+0000",
        "productId" : "awesomeos-virt-4",
        "providedProducts" : [ {
          "created" : "2013-02-26T19:30:06.709+0000",
          "updated" : "2013-02-26T19:30:06.709+0000",
          "id" : "402881983d17fabf013d17fbbcf5036a",
          "productId" : "37060",
          "productName" : "Awesome OS Server Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "created" : "2013-02-26T19:30:06.708+0000",
          "updated" : "2013-02-26T19:30:06.708+0000",
          "id" : "402881983d17fabf013d17fbbcf40364",
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : "awesomeos-virt-4"
        }, {
          "created" : "2013-02-26T19:30:06.708+0000",
          "updated" : "2013-02-26T19:30:06.708+0000",
          "id" : "402881983d17fabf013d17fbbcf40365",
          "name" : "virt_limit",
          "value" : "4",
          "productId" : "awesomeos-virt-4"
        }, {
          "created" : "2013-02-26T19:30:06.709+0000",
          "updated" : "2013-02-26T19:30:06.709+0000",
          "id" : "402881983d17fabf013d17fbbcf50366",
          "name" : "type",
          "value" : "MKT",
          "productId" : "awesomeos-virt-4"
        }, {
          "created" : "2013-02-26T19:30:06.709+0000",
          "updated" : "2013-02-26T19:30:06.709+0000",
          "id" : "402881983d17fabf013d17fbbcf50367",
          "name" : "arch",
          "value" : "ALL",
          "productId" : "awesomeos-virt-4"
        }, {
          "created" : "2013-02-26T19:30:06.709+0000",
          "updated" : "2013-02-26T19:30:06.709+0000",
          "id" : "402881983d17fabf013d17fbbcf50368",
          "name" : "version",
          "value" : "6.1",
          "productId" : "awesomeos-virt-4"
        }, {
          "created" : "2013-02-26T19:30:06.709+0000",
          "updated" : "2013-02-26T19:30:06.709+0000",
          "id" : "402881983d17fabf013d17fbbcf50369",
          "name" : "variant",
          "value" : "ALL",
          "productId" : "awesomeos-virt-4"
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "102",
        "accountNumber" : "12331131231",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Awesome OS with up to 4 virtual guests",
        "href" : "/pools/402881983d17fabf013d17fbbcf40363"
      },
      "startDate" : "2013-02-26T00:00:00.000+0000",
      "endDate" : "2014-02-26T00:00:00.000+0000",
      "certificates" : [ {
        "created" : "2013-02-27T16:03:18.219+0000",
        "updated" : "2013-02-27T16:03:18.219+0000",
        "key" : "",
        "cert" : "",
        "id" : "402881983d17fabf013d1c64c24b0b88",
        "serial" : {
          "created" : "2013-02-27T16:03:18.187+0000",
          "updated" : "2013-02-27T16:03:18.187+0000",
          "id" : 3772349624435077441,
          "revoked" : false,
          "collected" : false,
          "expiration" : "2014-02-26T00:00:00.000+0000",
          "serial" : 3772349624435077441
        }
      } ],
      "quantity" : 1,
      "accountNumber" : "12331131231",
      "contractNumber" : "102",
      "href" : "/entitlements/402881983d17fabf013d1c64c1df0b7a"
    } ]
  },
  "partiallyCompliantProducts" : {
    "100000000000002" : [ {
      "created" : "2013-02-27T16:02:39.298+0000",
      "updated" : "2013-02-27T16:02:39.298+0000",
      "id" : "402881983d17fabf013d1c642a420b78",
      "consumer" : {
        "id" : "402881983d17fabf013d1c5c98810b70",
        "uuid" : "4bb47522-df95-46c2-ac23-c4532faf6d8d",
        "name" : "lenovo.local.rm-rf.ca",
        "href" : "/consumers/4bb47522-df95-46c2-ac23-c4532faf6d8d"
      },
      "pool" : {
        "created" : "2013-02-26T19:30:07.553+0000",
        "updated" : "2013-02-27T16:02:39.299+0000",
        "id" : "402881983d17fabf013d17fbc0410407",
        "owner" : {
          "id" : "402881983d17fabf013d17fae23d005d",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "402881983d17fabf013d17fb6bab01bf",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 10,
        "startDate" : "2013-02-26T00:00:00.000+0000",
        "endDate" : "2014-02-26T00:00:00.000+0000",
        "productId" : "awesomeos-x86_64",
        "providedProducts" : [ {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc0430410",
          "productId" : "100000000000002",
          "productName" : "Awesome OS for x86_64 Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc0420408",
          "name" : "arch",
          "value" : "x86_64",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc0420409",
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040a",
          "name" : "stacking_id",
          "value" : "1",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040b",
          "name" : "type",
          "value" : "MKT",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040c",
          "name" : "sockets",
          "value" : "1",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc043040d",
          "name" : "version",
          "value" : "3.11",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc043040e",
          "name" : "warning_period",
          "value" : "30",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc043040f",
          "name" : "variant",
          "value" : "ALL",
          "productId" : "awesomeos-x86_64"
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "67",
        "accountNumber" : "12331131231",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Awesome OS for x86_64",
        "href" : "/pools/402881983d17fabf013d17fbc0410407"
      },
      "startDate" : "2013-02-26T00:00:00.000+0000",
      "endDate" : "2014-02-26T00:00:00.000+0000",
      "certificates" : [ {
        "created" : "2013-02-27T16:02:39.385+0000",
        "updated" : "2013-02-27T16:02:39.385+0000",
        "key" : "",
        "cert" : "",
        "id" : "402881983d17fabf013d1c642a990b79",
        "serial" : {
          "created" : "2013-02-27T16:02:39.337+0000",
          "updated" : "2013-02-27T16:02:39.337+0000",
          "id" : 7014120607119972290,
          "revoked" : false,
          "collected" : false,
          "expiration" : "2014-02-26T00:00:00.000+0000",
          "serial" : 7014120607119972290
        }
      } ],
      "quantity" : 1,
      "accountNumber" : "12331131231",
      "contractNumber" : "67",
      "href" : "/entitlements/402881983d17fabf013d1c642a420b78"
    } ]
  },
  "partialStacks" : {
    "1" : [ {
      "created" : "2013-02-27T16:02:39.298+0000",
      "updated" : "2013-02-27T16:02:39.298+0000",
      "id" : "402881983d17fabf013d1c642a420b78",
      "consumer" : {
        "id" : "402881983d17fabf013d1c5c98810b70",
        "uuid" : "4bb47522-df95-46c2-ac23-c4532faf6d8d",
        "name" : "lenovo.local.rm-rf.ca",
        "href" : "/consumers/4bb47522-df95-46c2-ac23-c4532faf6d8d"
      },
      "pool" : {
        "created" : "2013-02-26T19:30:07.553+0000",
        "updated" : "2013-02-27T16:02:39.299+0000",
        "id" : "402881983d17fabf013d17fbc0410407",
        "owner" : {
          "id" : "402881983d17fabf013d17fae23d005d",
          "key" : "admin",
          "displayName" : "Admin Owner",
          "href" : "/owners/admin"
        },
        "activeSubscription" : true,
        "subscriptionId" : "402881983d17fabf013d17fb6bab01bf",
        "subscriptionSubKey" : "master",
        "sourceEntitlement" : null,
        "quantity" : 10,
        "startDate" : "2013-02-26T00:00:00.000+0000",
        "endDate" : "2014-02-26T00:00:00.000+0000",
        "productId" : "awesomeos-x86_64",
        "providedProducts" : [ {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc0430410",
          "productId" : "100000000000002",
          "productName" : "Awesome OS for x86_64 Bits"
        } ],
        "attributes" : [ ],
        "productAttributes" : [ {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc0420408",
          "name" : "arch",
          "value" : "x86_64",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc0420409",
          "name" : "multi-entitlement",
          "value" : "yes",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040a",
          "name" : "stacking_id",
          "value" : "1",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040b",
          "name" : "type",
          "value" : "MKT",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc042040c",
          "name" : "sockets",
          "value" : "1",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.554+0000",
          "updated" : "2013-02-26T19:30:07.554+0000",
          "id" : "402881983d17fabf013d17fbc043040d",
          "name" : "version",
          "value" : "3.11",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc043040e",
          "name" : "warning_period",
          "value" : "30",
          "productId" : "awesomeos-x86_64"
        }, {
          "created" : "2013-02-26T19:30:07.555+0000",
          "updated" : "2013-02-26T19:30:07.555+0000",
          "id" : "402881983d17fabf013d17fbc043040f",
          "name" : "variant",
          "value" : "ALL",
          "productId" : "awesomeos-x86_64"
        } ],
        "restrictedToUsername" : null,
        "contractNumber" : "67",
        "accountNumber" : "12331131231",
        "consumed" : 1,
        "exported" : 0,
        "productName" : "Awesome OS for x86_64",
        "href" : "/pools/402881983d17fabf013d17fbc0410407"
      },
      "startDate" : "2013-02-26T00:00:00.000+0000",
      "endDate" : "2014-02-26T00:00:00.000+0000",
      "certificates" : [ {
        "created" : "2013-02-27T16:02:39.385+0000",
        "updated" : "2013-02-27T16:02:39.385+0000",
        "key" : "",
        "cert" : "",
        "id" : "402881983d17fabf013d1c642a990b79",
        "serial" : {
          "created" : "2013-02-27T16:02:39.337+0000",
          "updated" : "2013-02-27T16:02:39.337+0000",
          "id" : 7014120607119972290,
          "revoked" : false,
          "collected" : false,
          "expiration" : "2014-02-26T00:00:00.000+0000",
          "serial" : 7014120607119972290
        }
      } ],
      "quantity" : 1,
      "accountNumber" : "12331131231",
      "contractNumber" : "67",
      "href" : "/entitlements/402881983d17fabf013d1c642a420b78"
    } ]
  },
  "status" : "invalid",
  "compliant" : false
}
""")


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.products:
            if product.id == product_id:
                return True
    return False


INST_PID_1 = "37060"
INST_PID_2 = "100000000000002"
INST_PID_3 = "69"
INST_PID_4 = 1004
INST_PID_5 = 1005
INST_PID_6 = 1006
STACK_1 = 'stack1'
STACK_2 = 'stack2'

PARTIAL_STACK_ID = "1"


def stub_prod_cert(pid):
    return StubProductCertificate(StubProduct(pid))

class CertSorterTests(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)

        # Setup mock product and entitlement certs:
        self.prod_dir = StubProductDirectory(
                pids=[INST_PID_1, INST_PID_2, INST_PID_3])

        self.ent_dir = StubEntitlementDirectory([
            StubEntitlementCertificate(StubProduct(INST_PID_2)),
            StubEntitlementCertificate(StubProduct(INST_PID_3),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct(INST_PID_4),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() + timedelta(days=365)),
            StubEntitlementCertificate(StubProduct(INST_PID_5)),
            # entitled, but not installed
            StubEntitlementCertificate(StubProduct('not_installed_product')),
            ])

        self.mock_uep = StubUEP()
        self.mock_uep.getCompliance = Mock(return_value=SAMPLE_COMPLIANCE_JSON)
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, self.mock_uep)
        self.sorter.is_registered = Mock(return_value=True)

    def test_unregistered_status(self):
        sorter = CertSorter(self.prod_dir, self.ent_dir, self.mock_uep)
        sorter.is_registered = Mock(return_value=False)
        self.assertEquals(UNKNOWN, sorter.get_status(INST_PID_1))

    def test_server_has_no_compliance_api(self):
        self.mock_uep = StubUEP()
        self.mock_uep.getCompliance = Mock(
                side_effect=RestlibException('boom'))
        sorter = CertSorter(self.prod_dir, self.ent_dir, self.mock_uep)
        sorter.is_registered = Mock(return_value=True)
        self.assertEquals(UNKNOWN, sorter.get_status(INST_PID_1))

    def test_unentitled_products(self):
        self.assertEquals(1, len(self.sorter.unentitled_products))
        self.assertTrue("69" in self.sorter.unentitled_products)

    def test_valid_products(self):
        self.assertEquals(1, len(self.sorter.valid_products))
        self.assertTrue("37060" in self.sorter.valid_products)

    def test_partially_valid_products(self):
        self.assertEquals(1, len(self.sorter.partially_valid_products))
        self.assertTrue("100000000000002" in
                self.sorter.partially_valid_products)

    def test_installed_products(self):
        self.assertEquals(3, len(self.sorter.installed_products))
        self.assertTrue(INST_PID_1 in self.sorter.installed_products)
        self.assertTrue(INST_PID_2 in self.sorter.installed_products)
        self.assertTrue(INST_PID_3 in self.sorter.installed_products)

    def test_partial_stack(self):
        self.assertEquals(1, len(self.sorter.partial_stacks))
        self.assertTrue(PARTIAL_STACK_ID in self.sorter.partial_stacks)

    def test_installed_mismatch_unentitled(self):
        # Use a different product directory with something not present
        # in the response from the server as an unentitled product:
        prod_dir = StubProductDirectory(
                pids=[INST_PID_1, INST_PID_2])
        sorter = CertSorter(prod_dir, self.ent_dir, self.mock_uep)
        self.assertFalse(INST_PID_3 in sorter.installed_products)
        # Should get filtered out of unentitled products even though
        # server reported it here:
        self.assertFalse(INST_PID_3 in sorter.unentitled_products)

    def test_missing_installed_product(self):
        # Add a new installed product server doesn't know about:
        prod_dir = StubProductDirectory(pids=[INST_PID_1, INST_PID_2,
            INST_PID_3, "product4"])
        sorter = CertSorter(prod_dir, self.ent_dir, self.mock_uep)
        self.assertTrue('product4' in sorter.unentitled_products)

    def test_no_compliant_until(self):
        SAMPLE_COMPLIANCE_JSON['compliantUntil'] = None
        self.sorter = CertSorter(self.prod_dir, self.ent_dir, self.mock_uep)
        self.sorter.is_registered = Mock(return_value=True)
        self.assertTrue(self.sorter.compliant_until is None)
        self.assertTrue(self.sorter.first_invalid_date is None)

    def test_compliant_until(self):
        compliant_until = self.sorter.compliant_until
        self.assertEquals(2013, compliant_until.year)
        self.assertEquals(2, compliant_until.month)
        self.assertEquals(27, compliant_until.day)
        self.assertEquals(16, compliant_until.hour)
        self.assertEquals(03, compliant_until.minute)
        self.assertEquals(42, compliant_until.second)

    def test_first_invalid_date(self):
        first_invalid = self.sorter.first_invalid_date
        self.assertEquals(2013, first_invalid.year)
        self.assertEquals(2, first_invalid.month)
        self.assertEquals(28, first_invalid.day)

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

        sorter = StubCertSorter(prod_dir, ent_dir)
        sorter.valid_products = {"a": StubProduct("a")}
        sorter.partially_valid_products = {"b": StubProduct("b")}

        sorter._scan_entitlement_certs()

        self.assertEquals(["d"], sorter.expired_products.keys())
        self.assertEquals(["e"], sorter.future_products.keys())

        self.assertEquals(3, len(sorter.valid_entitlement_certs))

