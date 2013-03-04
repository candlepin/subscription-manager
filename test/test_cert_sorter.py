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

import unittest
from fixture import SubManFixture
from subscription_manager.injection import FEATURES, IDENTITY
from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubCertificateDirectory, StubEntitlementDirectory, StubFacts, StubProductDirectory, \
    StubUEP
from subscription_manager.cert_sorter import EntitlementCertStackingGroupSorter, \
    CertSorter, FUTURE_SUBSCRIBED, SUBSCRIBED, NOT_SUBSCRIBED, EXPIRED, PARTIALLY_SUBSCRIBED, UNKNOWN
from subscription_manager.identity import ConsumerIdentity
from datetime import timedelta, datetime
from rhsm.certificate import GMT
from mock import Mock, patch
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

#    def test_requested_date(self):
#        expected = "date" : "2013-02-27T16:03:42.509+0000"

#    def test_compliantUntil(self):
#        expected = "compliantUntil" : "2013-02-27T16:03:42.509+0000",


#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_unentitled_product_certs(self, id_mock):
#        id_mock.return_value = True
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())
#        self.assertEqual(1, len(self.sorter.unentitled_products.keys()))
#        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
#        self.assertFalse(self.sorter.is_valid())
#        self.assertEqual(NOT_SUBSCRIBED, self.sorter.get_status(INST_PID_1))

#    def test_ent_cert_no_installed_product(self):
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())
#        # TODO: looks like this test was never completed

#    def test_ent_cert_no_product(self):
#        self.ent_dir = StubCertificateDirectory(
#            [StubEntitlementCertificate(None, provided_products=[],
#                                        quantity=2)])

#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
#                stub_facts.get_facts(), StubUEP())

#        self.assertEqual(0, len(self.sorter.partially_valid_products))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_expired(self, id_mock):
#        id_mock.return_value = True
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())
#        self.assertEqual(1, len(self.sorter.expired_entitlement_certs))

#        self.assertTrue(cert_list_has_product(
#            self.sorter.expired_entitlement_certs, INST_PID_3))

#        self.assertEqual(1, len(self.sorter.expired_products.keys()))
#        self.assertTrue(INST_PID_3 in self.sorter.expired_products)
#        self.assertFalse(self.sorter.is_valid())
#        self.assertEquals(EXPIRED, self.sorter.get_status(INST_PID_3))

#    def test_expired_in_future(self):
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP(),
#                on_date=datetime(2050, 1, 1, tzinfo=GMT()))
#        self.assertEqual(5, len(self.sorter.expired_entitlement_certs))
#        self.assertTrue(INST_PID_2 in self.sorter.expired_products)
#        self.assertTrue(INST_PID_3 in self.sorter.expired_products)
#        self.assertFalse(INST_PID_4 in self.sorter.expired_products)  # it's not installed
#        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
#        self.assertEqual(0, len(self.sorter.valid_entitlement_certs))
#        self.assertFalse(self.sorter.is_valid())

#    def test_entitled_products(self):
#        provided = [StubProduct(INST_PID_1), StubProduct(INST_PID_2),
#                StubProduct(INST_PID_3)]
#        self.ent_dir = StubCertificateDirectory([
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=provided)])
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())
#        self.assertEquals(3, len(self.sorter.valid_products.keys()))
#        self.assertTrue(INST_PID_1 not in self.sorter.partially_valid_products)
#        self.assertTrue(INST_PID_1 in self.sorter.valid_products)
#        self.assertTrue(INST_PID_2 in self.sorter.valid_products)
#        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
#        self.assertTrue(self.sorter.is_valid())

#    def test_expired_but_provided_in_another_entitlement(self):
#        self.ent_dir = StubCertificateDirectory([
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=[StubProduct(INST_PID_3)]),
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                start_date=datetime.now() - timedelta(days=365),
#                end_date=datetime.now() - timedelta(days=2),
#                provided_products=[StubProduct(INST_PID_3)]),
#            StubEntitlementCertificate(StubProduct(INST_PID_4))
#        ])
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())
#        self.assertEquals(1, len(self.sorter.valid_products.keys()))
#        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
#        self.assertEquals(0, len(self.sorter.expired_products.keys()))

#    def test_multi_product_entitlement_expired(self):
#        # Setup one ent cert that provides several things installed
#        # installed:
#        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
#        self.ent_dir = StubCertificateDirectory([
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=provided)])
#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP(),
#                on_date=datetime(2050, 1, 1, tzinfo=GMT()))

#        self.assertEquals(1, len(self.sorter.expired_entitlement_certs))
#        self.assertEquals(2, len(self.sorter.expired_products.keys()))
#        self.assertTrue(INST_PID_2 in self.sorter.expired_products)
#        self.assertTrue(INST_PID_3 in self.sorter.expired_products)

#        # Expired should not show up as unentitled also:
#        self.assertEquals(1, len(self.sorter.unentitled_products.keys()))
#        self.assertTrue(INST_PID_1 in self.sorter.unentitled_products)
#        self.assertFalse(self.sorter.is_valid())

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_future_entitled(self, id_mock):
#        id_mock.return_value = True
#        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
#        self.ent_dir = StubCertificateDirectory([
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=provided,
#                start_date=datetime.now() + timedelta(days=30),
#                end_date=datetime.now() + timedelta(days=120)),
#            ])

#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())

#        self.assertEquals(0, len(self.sorter.valid_products))
#        self.assertEquals(2, len(self.sorter.future_products))
#        self.assertEquals(3, len(self.sorter.unentitled_products))
#        self.assertTrue(INST_PID_2 in self.sorter.future_products)
#        self.assertTrue(INST_PID_3 in self.sorter.future_products)
#        self.assertEquals(FUTURE_SUBSCRIBED, self.sorter.get_status(INST_PID_2))
#        self.assertEquals(FUTURE_SUBSCRIBED, self.sorter.get_status(INST_PID_3))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_future_and_currently_entitled(self, id_mock):
#        id_mock.return_value = True
#        provided = [StubProduct(INST_PID_2), StubProduct(INST_PID_3)]
#        self.ent_dir = StubCertificateDirectory([
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=provided,
#                start_date=datetime.now() + timedelta(days=30),
#                end_date=datetime.now() + timedelta(days=120)),
#            StubEntitlementCertificate(StubProduct(INST_PID_5),
#                provided_products=provided),
#            ])

#        self.sorter = CertSorter(self.prod_dir, self.ent_dir, {}, StubUEP())

#        self.assertEquals(2, len(self.sorter.valid_products))
#        self.assertEquals(2, len(self.sorter.future_products))
#        self.assertEquals(1, len(self.sorter.unentitled_products))
#        self.assertTrue(INST_PID_2 in self.sorter.future_products)
#        self.assertTrue(INST_PID_3 in self.sorter.future_products)
#        self.assertTrue(INST_PID_2 in self.sorter.valid_products)
#        self.assertTrue(INST_PID_3 in self.sorter.valid_products)
#        self.assertEquals(SUBSCRIBED, self.sorter.get_status(INST_PID_2))
#        self.assertEquals(SUBSCRIBED, self.sorter.get_status(INST_PID_3))

#    def test_non_stacked_lacking_sockets(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
#        # Only 2 sockets covered by a non-stacked entitlement:
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], sockets=2,
#            quantity=5)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertEquals(1, len(sorter.partially_valid_products))
#        self.assertEquals(1, len(sorter.partially_valid_products[INST_PID_1]))

#    def test_non_stacked_0_sockets(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
#        # 0 sockets is basically "unlimited" sockets
#        # see bz#805415
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], sockets=0,
#            quantity=5)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)

#    def test_4GB_system_covered_by_1_4GB_ent(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 4194304 total memory:
#        stub_facts = StubFacts(fact_dict={"memory.memtotal": "4194304"})
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], ram=4)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(1, len(sorter.valid_products))

#    def test_8GB_system_partially_covered_by_4GB_ent(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8388608 total memory:
#        stub_facts = StubFacts(fact_dict={"memory.memtotal": "8388608"})
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], ram=4)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(1, len(sorter.partially_valid_products))

#    def test_4GB_2_socket_system_covered_by_1_4GB_2_socket_ent(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 4194304 total memory and 2 sockets
#        stub_facts = StubFacts(fact_dict={"memory.memtotal": "4194304",
#                                          "cpu.cpu_socket(s)": 2})
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], ram=4, sockets=2)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(1, len(sorter.valid_products))

#    def test_4GB_4_socket_system_partially_covered_by_1_4GB_2_socket_ent(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 4194304 total memory and 4 sockets
#        stub_facts = StubFacts(fact_dict={"memory.memtotal": "4194304",
#                                          "cpu.cpu_socket(s)": 4})
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], ram=4, sockets=2)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(1, len(sorter.partially_valid_products))

#    def test_8GB_2_socket_system_partially_covered_by_1_4GB_2_socket_ent(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8388608 total memory and 2 sockets
#        stub_facts = StubFacts(fact_dict={"memory.memtotal": "8388608",
#                                          "cpu.cpu_socket(s)": 2})
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], ram=4, sockets=2)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(1, len(sorter.partially_valid_products))


#class CertSorterStackingTests(unittest.TestCase):

#    def test_simple_partial_stack(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
#        # Only 2 sockets covered:
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=2)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertEquals(1, len(sorter.partially_valid_products))
#        self.assertEquals(1, len(sorter.partially_valid_products[INST_PID_1]))

#    def test_simple_full_stack_multicert(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
#        # 2 ent certs providing 4 sockets each means we're valid:
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=4),
#            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=4)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertEquals(0, len(sorter.partially_valid_products))

#    def test_simple_full_stack_0_sockets(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 1 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 1})
#        # 0 sockets is basically "unlimited" sockets
#        # see bz#805415
#        ent_dir = StubCertificateDirectory([
#                stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1, sockets=0)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)

#    def test_simple_full_stack_singlecert_with_quantity(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])
#        # System has 8 sockets:
#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 8})
#        # 1 ent cert providing 4 sockets with quantity 2 means we're valid:
#        ent_dir = StubCertificateDirectory([
#            stub_ent_cert(INST_PID_5, [INST_PID_1], stack_id=STACK_1,
#                sockets=4, quantity=2)])
#        sorter = CertSorter(prod_dir, ent_dir, stub_facts.get_facts(), StubUEP())

#        self.assertFalse(INST_PID_1 in sorter.unentitled_products)
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertFalse(INST_PID_1 in sorter.partially_valid_products)
#        self.assertEquals(0, len(sorter.partially_valid_products))

#    # This is still technically invalid:
#    def test_partial_stack_for_uninstalled_products(self):
#        # No products installed:
#        prod_dir = StubProductDirectory([])

#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 42})
#        ents = []
#        ents.append(stub_ent_cert(INST_PID_5, ['prod1'],
#            stack_id=STACK_1, quantity=2))
#        ent_dir = StubCertificateDirectory(ents)
#        sorter = CertSorter(prod_dir, ent_dir,
#                stub_facts.get_facts(), StubUEP())

#        # No installed products, so nothing should show up as partially valid:
#        self.assertEquals(0, len(sorter.partially_valid_products))

#        self.assertEquals(1, len(sorter.partial_stacks))
#        self.assertTrue(STACK_1 in sorter.partial_stacks)
#        self.assertFalse(sorter.is_valid())

#    # Entitlements with the same stack ID will not necessarily have the same
#    # first product, thus why we key off stacking_id attribute:
#    def test_partial_stack_different_first_product(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])

#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})
#        ents = []
#        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
#            stack_id=STACK_1, sockets=1))
#        ents.append(stub_ent_cert(INST_PID_6, [INST_PID_1],
#            stack_id=STACK_1, sockets=1))
#        ent_dir = StubCertificateDirectory(ents)

#        sorter = CertSorter(prod_dir, ent_dir,
#                stub_facts.get_facts(), StubUEP())

#        # Installed product should show up as partially valid:
#        self.assertEquals(1, len(sorter.partially_valid_products))
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertTrue(STACK_1 in sorter.partial_stacks)

#    # Edge case, but technically two stacks could have same first product
#    def test_multiple_partial_stacks_same_first_product(self):
#        prod_dir = StubProductDirectory([
#            stub_prod_cert(INST_PID_1)])

#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})

#        ents = []
#        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
#            stack_id=STACK_1, sockets=1))
#        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
#            stack_id=STACK_2, sockets=1))
#        ent_dir = StubCertificateDirectory(ents)
#        sorter = CertSorter(prod_dir, ent_dir,
#                stub_facts.get_facts(), StubUEP())

#        # Our installed product should be partially valid:
#        self.assertEquals(1, len(sorter.partially_valid_products))
#        self.assertTrue(INST_PID_1 in sorter.partially_valid_products)
#        self.assertFalse(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(2, len(sorter.partial_stacks))
#        self.assertTrue(STACK_1 in sorter.partial_stacks)
#        self.assertTrue(STACK_2 in sorter.partial_stacks)

#    def test_valid_stack_different_first_products(self):
#        prod_dir = StubProductDirectory([stub_prod_cert(INST_PID_1)])

#        stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": 4})
#        # Two entitlements, same stack, different first products, each
#        # providing 2 sockets: (should be valid)
#        ents = []
#        ents.append(stub_ent_cert(INST_PID_5, [INST_PID_1],
#            stack_id=STACK_1, sockets=2))
#        ents.append(stub_ent_cert(INST_PID_6, [INST_PID_1],
#            stack_id=STACK_1, sockets=2))
#        ent_dir = StubCertificateDirectory(ents)

#        sorter = CertSorter(prod_dir, ent_dir,
#                stub_facts.get_facts(), StubUEP())

#        # Installed product should show up as valid:
#        self.assertEquals(1, len(sorter.valid_products))
#        self.assertTrue(INST_PID_1 in sorter.valid_products)
#        self.assertEquals(0, len(sorter.partially_valid_products))
#        self.assertEquals(0, len(sorter.partial_stacks))


#class TestCertSorterStatus(unittest.TestCase):

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_subscribed(self, id_mock):
#        id_mock.return_value = True
#        product = create_prod_cert(INST_PID_1)
#        entitlement = stub_ent_cert(INST_PID_1, sockets=None)
#        sorter = create_cert_sorter([product], [entitlement])
#        self.assertEqual(SUBSCRIBED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_not_subscribed(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        sorter = create_cert_sorter([installed], [])
#        self.assertEqual(NOT_SUBSCRIBED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_expired(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        expired_ent = stub_ent_cert(INST_PID_1,
#                                         start_date=datetime.now() - timedelta(days=365),
#                                         end_date=datetime.now() - timedelta(days=2))
#        sorter = create_cert_sorter([installed], [expired_ent])
#        self.assertEqual(EXPIRED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_future_subscribed(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        expired_ent = stub_ent_cert(INST_PID_1,
#                                         start_date=datetime.now() + timedelta(days=10),
#                                         end_date=datetime.now() + timedelta(days=365))
#        sorter = create_cert_sorter([installed], [expired_ent])
#        self.assertEqual(FUTURE_SUBSCRIBED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_partially_subscribed(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        partial_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
#                                         stack_id=STACK_1, sockets=2)
#        sorter = create_cert_sorter([installed], [partial_ent])
#        self.assertEqual(PARTIALLY_SUBSCRIBED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_partially_subscribed_and_future_subscription(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        partial_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
#                                         stack_id=STACK_1, sockets=2)
#        future_ent = stub_ent_cert(INST_PID_2, [INST_PID_1], quantity=1,
#                                         stack_id=STACK_1, sockets=2,
#                                         start_date=datetime.now() + timedelta(days=10),
#                                         end_date=datetime.now() + timedelta(days=365))
#        sorter = create_cert_sorter([installed], [partial_ent, future_ent])
#        self.assertEqual(PARTIALLY_SUBSCRIBED, sorter.get_status(INST_PID_1))

#    @patch.object(ConsumerIdentity, 'existsAndValid')
#    def test_expired_and_future_entitlements_report_future(self, id_mock):
#        id_mock.return_value = True
#        installed = create_prod_cert(INST_PID_1)
#        expired_ent = stub_ent_cert(INST_PID_1,
#                                         start_date=datetime.now() - timedelta(days=365),
#                                         end_date=datetime.now() - timedelta(days=10))
#        future_ent = stub_ent_cert(INST_PID_1,
#                                         start_date=datetime.now() + timedelta(days=10),
#                                         end_date=datetime.now() + timedelta(days=365))

#        sorter = create_cert_sorter([installed], [future_ent, expired_ent])
#        self.assertEqual(FUTURE_SUBSCRIBED, sorter.get_status(INST_PID_1))


#class TestEntitlementCertStackingGroupSorter(unittest.TestCase):

#    def test_sorter_adds_group_for_non_stackable_entitlement(self):
#        ent1_prod = StubProduct("Product 1")
#        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=None)
#        entitlements = [ent1]

#        sorter = EntitlementCertStackingGroupSorter(entitlements)
#        # With no stacking id, we expect an empty group name
#        self._assert_1_group_with_1_entitlement("", ent1, sorter)

#    def test_sorter_adds_group_for_stackable_entitlement(self):
#        ent1_prod = StubProduct("Product 1")
#        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=3)
#        entitlements = [ent1]

#        sorter = EntitlementCertStackingGroupSorter(entitlements)
#        self._assert_1_group_with_1_entitlement('Product 1', ent1, sorter)

#    def test_sorter_adds_multiple_entitlements_to_group_when_same_stacking_id(self):
#        expected_stacking_id = 5

#        ent1_prod = StubProduct("Product 1")
#        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=expected_stacking_id)

#        ent2_prod = StubProduct("Product 2")
#        ent2 = StubEntitlementCertificate(ent2_prod, stacking_id=expected_stacking_id)
#        entitlements = [ent1, ent2]

#        sorter = EntitlementCertStackingGroupSorter(entitlements)
#        self.assertEquals(1, len(sorter.groups))
#        self.assertEquals("Product 1", sorter.groups[0].name)
#        self.assertEquals(2, len(sorter.groups[0].entitlements))
#        self.assertEquals(ent1, sorter.groups[0].entitlements[0])
#        self.assertEquals(ent2, sorter.groups[0].entitlements[1])

#    def test_sorter_adds_multiple_groups_for_non_stacking_entitlements(self):
#        ent1_prod = StubProduct("Product 1")
#        ent1 = StubEntitlementCertificate(ent1_prod, stacking_id=None)

#        ent2_prod = StubProduct("Product 2")
#        ent2 = StubEntitlementCertificate(ent2_prod, stacking_id=None)

#        entitlements = [ent1, ent2]

#        sorter = EntitlementCertStackingGroupSorter(entitlements)
#        self.assertEquals(2, len(sorter.groups))

#        self.assertEquals('', sorter.groups[0].name)
#        self.assertEquals(1, len(sorter.groups[0].entitlements))
#        self.assertEquals(ent1, sorter.groups[0].entitlements[0])

#        self.assertEquals('', sorter.groups[1].name)
#        self.assertEquals(1, len(sorter.groups[1].entitlements))
#        self.assertEquals(ent2, sorter.groups[1].entitlements[0])

#    def _assert_1_group_with_1_entitlement(self, name, entitlement, sorter):
#        self.assertEquals(1, len(sorter.groups))
#        group = sorter.groups[0]
#        self.assertEquals(name, group.name)
#        self.assertEquals(1, len(group.entitlements))
#        self.assertEquals(entitlement, group.entitlements[0])


def stub_ent_cert(parent_pid, provided_pids=None, quantity=1,
        stack_id=None, sockets=1, ram=None, start_date=None, end_date=None):
    provided_prods = []

    if provided_pids is None:
        provided_pids = []

    for provided_pid in provided_pids:
        provided_prods.append(StubProduct(provided_pid))

    parent_prod = StubProduct(parent_pid)

    return StubEntitlementCertificate(parent_prod,
            provided_products=provided_prods, quantity=quantity,
            stacking_id=stack_id, sockets=sockets, ram=ram, start_date=start_date,
            end_date=end_date)


    # TODO: remove
def create_cert_sorter(product_certs, entitlement_certs, machine_sockets=8):
    return CertSorter(StubProductDirectory(product_certs),
                      StubEntitlementDirectory(entitlement_certs),
                      StubUEP())
