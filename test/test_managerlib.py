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

import datetime
import time
import unittest
import os
from os import linesep as NEW_LINE

from stubs import StubCertificateDirectory, StubProductCertificate, StubProduct, \
    StubEntitlementCertificate
from subscription_manager.managerlib import merge_pools, PoolFilter, getInstalledProductStatus, \
    LocalTz, parseDate, configure_i18n, merge_pools, MergedPoolsStackingGroupSorter
from modelhelpers import *
from subscription_manager import managerlib
import stubs
import rhsm

cfg = rhsm.config.initConfig()
ENT_CONFIG_DIR = cfg.get('rhsm', 'entitlementCertDir')

#[-]*BEGIN [\w\ ]*[-]* - Find all begin lines
#[-]*BEGIN[\w\ ]*[-]*|[-]*END[\w\ ]*[-]* - Find all BEGIN END lines
#(?P<start>[-]*BEGIN[\w\ ]*[-]*)(?P<content>[^-]*)(?P<end>[-]*END[\w\ ]*[-]*)

EXPECTED_CERT_CONTENT = """-----BEGIN CERTIFICATE-----
MIIJwTCCCSqgAwIBAgIIRW4yerC04nIwDQYJKoZIhvcNAQEFBQAwNDETMBEGA1UE
AwwKbXN0ZWFkLmNzYjELMAkGA1UEBhMCVVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcN
MTEwNzEzMDAwMDAwWhcNMTIwNzEyMDAwMDAwWjArMSkwJwYDVQQDEyA4MDgwODA4
MDMxMjg1NjIwMDEzMTI5NzZiMDIyMDAwNjCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAMemhvL5+3/EfoK+Elile3JC6y+FolWJXTxuiuJwO4GXiS5AiIx1
x3sYSZjGvMH2aSopoxrVBLYFTvZ6PmxK6wuV8JVO9pfi5BVpCMwaVosssPAZhFpM
EpM6B/DU2AWSmBk2zvI6PbZ83HzMICByDTUsBLed+HtU6az5rhGXLnUYlnGnau9w
5WkbAbS+hTqZHvWPdwpdMJ/bNyV04xg2LcsnHDSodIVmXgBtQiZD32rGOjkB48QX
mMHnuBpjYiRaZhZCGeOSPI6boSK/pGcr5QdHJB4+NRFSW3INwHHSWjKaTJSRi6+q
LOYGijUKBmv0AE+Bd1acbynxwRPLvcTJATUCAwEAAaOCB18wggdbMBEGCWCGSAGG
+EIBAQQEAwIFoDALBgNVHQ8EBAMCBLAwZAYDVR0jBF0wW4AUooCU0h+EAAGYfSf5
ncDamLLCeUOhOKQ2MDQxEzARBgNVBAMMCm1zdGVhZC5jc2IxCzAJBgNVBAYTAlVT
MRAwDgYDVQQHDAdSYWxlaWdoggkAnVMmeWWGXWwwHQYDVR0OBBYEFKuittOhxG6z
ag5P9cr2fvN+6xIrMBMGA1UdJQQMMAoGCCsGAQUFBwMCMCIGDSsGAQQBkggJAYKh
SQEEEQwPQ2x1c3RlcmluZyBCaXRzMBQGCysGAQQBkggJAgABBAUMA3l1bTAnBgwr
BgEEAZIICQIAAQEEFwwVbmV2ZXItZW5hYmxlZC1jb250ZW50MCcGDCsGAQQBkggJ
AgABAgQXDBVuZXZlci1lbmFibGVkLWNvbnRlbnQwHQYMKwYBBAGSCAkCAAEFBA0M
C3Rlc3QtdmVuZG9yMCEGDCsGAQQBkggJAgABBgQRDA8vZm9vL3BhdGgvbmV2ZXIw
JQYMKwYBBAGSCAkCAAEHBBUMEy9mb28vcGF0aC9uZXZlci9ncGcwEwYMKwYBBAGS
CAkCAAEIBAMMATAwFQYMKwYBBAGSCAkCAAEJBAUMAzYwMDAUBgsrBgEEAZIICQIB
AQQFDAN5dW0wKAYMKwYBBAGSCAkCAQEBBBgMFmFsd2F5cy1lbmFibGVkLWNvbnRl
bnQwKAYMKwYBBAGSCAkCAQECBBgMFmFsd2F5cy1lbmFibGVkLWNvbnRlbnQwHQYM
KwYBBAGSCAkCAQEFBA0MC3Rlc3QtdmVuZG9yMCIGDCsGAQQBkggJAgEBBgQSDBAv
Zm9vL3BhdGgvYWx3YXlzMCYGDCsGAQQBkggJAgEBBwQWDBQvZm9vL3BhdGgvYWx3
YXlzL2dwZzATBgwrBgEEAZIICQIBAQgEAwwBMTAVBgwrBgEEAZIICQIBAQkEBQwD
MjAwMCkGDSsGAQQBkggJAYKhRAEEGAwWQXdlc29tZSBPUyBTZXJ2ZXIgQml0czAU
BgsrBgEEAZIICQICAQQFDAN5dW0wIAYMKwYBBAGSCAkCAgEBBBAMDnRhZ2dlZC1j
b250ZW50MCAGDCsGAQQBkggJAgIBAgQQDA50YWdnZWQtY29udGVudDAdBgwrBgEE
AZIICQICAQUEDQwLdGVzdC12ZW5kb3IwIgYMKwYBBAGSCAkCAgEGBBIMEC9mb28v
cGF0aC9hbHdheXMwJgYMKwYBBAGSCAkCAgEHBBYMFC9mb28vcGF0aC9hbHdheXMv
Z3BnMBMGDCsGAQQBkggJAgIBCAQDDAExMBsGDCsGAQQBkggJAgIBCgQLDAlUQUcx
LFRBRzIwFQYMKwYBBAGSCAkCiFcBBAUMA3l1bTAaBg0rBgEEAZIICQKIVwEBBAkM
B2NvbnRlbnQwIAYNKwYBBAGSCAkCiFcBAgQPDA1jb250ZW50LWxhYmVsMB4GDSsG
AQQBkggJAohXAQUEDQwLdGVzdC12ZW5kb3IwHAYNKwYBBAGSCAkCiFcBBgQLDAkv
Zm9vL3BhdGgwIQYNKwYBBAGSCAkCiFcBBwQQDA4vZm9vL3BhdGgvZ3BnLzAUBg0r
BgEEAZIICQKIVwEIBAMMATEwFAYNKwYBBAGSCAkCiFcBCQQDDAEwMCYGDSsGAQQB
kggJAYKhTgEEFQwTTG9hZCBCYWxhbmNpbmcgQml0czAqBg0rBgEEAZIICQGCoUwB
BBkMF0xhcmdlIEZpbGUgU3VwcG9ydCBCaXRzMCYGDSsGAQQBkggJAYKhSwEEFQwT
U2hhcmVkIFN0b3JhZ2UgQml0czAiBg0rBgEEAZIICQGCoU0BBBEMD01hbmFnZW1l
bnQgQml0czBHBgorBgEEAZIICQQBBDkMN0F3ZXNvbWUgT1MgU2VydmVyIEJ1bmRs
ZWQgKDIgU29ja2V0cywgU3RhbmRhcmQgU3VwcG9ydCkwMAYKKwYBBAGSCAkEAgQi
DCA4MDgwODA4MDMxMjRjMjRlMDEzMTI0YzMxZTdkMDBjMzAtBgorBgEEAZIICQQD
BB8MHWF3ZXNvbWVvcy1zZXJ2ZXItMi1zb2NrZXQtc3RkMBEGCisGAQQBkggJBAUE
AwwBNTAkBgorBgEEAZIICQQGBBYMFDIwMTEtMDctMTNUMDA6MDA6MDBaMCQGCisG
AQQBkggJBAcEFgwUMjAxMi0wNy0xMlQwMDowMDowMFowEgYKKwYBBAGSCAkEDAQE
DAIzMDASBgorBgEEAZIICQQKBAQMAjEyMBsGCisGAQQBkggJBA0EDQwLMTIzMzEx
MzEyMzEwEQYKKwYBBAGSCAkEDgQDDAExMBgGCisGAQQBkggJBA8ECgwIU3RhbmRh
cmQwFQYKKwYBBAGSCAkEEAQHDAVMMS1MMzARBgorBgEEAZIICQQLBAMMATEwNAYK
KwYBBAGSCAkFAQQmDCQ5NGJkZDg2MS0wMzc1LTRhOWEtYTZhMS05M2Y4NGM0ZGZi
NDYwDQYJKoZIhvcNAQEFBQADgYEAiCKjWQKGX9uoMOiG9kn5aPOdhwy2McrefHnS
3qVkcqSxp/LQPTjej+MY7E/XECQInuO14h/RTTWrKReO2nRy9zFFm57fVPt2CjRz
ts/UsltTKEkTD4KBKxFVFELt1KWWT0AE5ire9mWcIdZRlPqvY0EpdmWDsUmX3E5d
oS/s7EY=
-----END CERTIFICATE-----"""

EXPECTED_KEY_CONTENT = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAx6aG8vn7f8R+gr4SWKV7ckLrL4WiVYldPG6K4nA7gZeJLkCI
jHXHexhJmMa8wfZpKimjGtUEtgVO9no+bErrC5XwlU72l+LkFWkIzBpWiyyw8BmE
WkwSkzoH8NTYBZKYGTbO8jo9tnzcfMwgIHINNSwEt534e1TprPmuEZcudRiWcadq
73DlaRsBtL6FOpke9Y93Cl0wn9s3JXTjGDYtyyccNKh0hWZeAG1CJkPfasY6OQHj
xBeYwee4GmNiJFpmFkIZ45I8jpuhIr+kZyvlB0ckHj41EVJbcg3AcdJaMppMlJGL
r6os5gaKNQoGa/QAT4F3VpxvKfHBE8u9xMkBNQIDAQABAoIBABcc5TSN0hrJgafb
Hz6Z8b+ZlaaLvu5OF7geR//M5GatR1lOaUBxhiVu+14va7y8rRIPfe1mScRUuv53
ynA5ABr4QcDXQl71ClicL0OJrQkxpE43dgYKFoBq0G6GBXgnr2oD2VNbgLd2nwPn
kbSP342PSgCDzjdg7ihzQz6QFPXDLVn5wTuJWiUCCg+WqkEUM6DaHirHLLy47vpB
HsA31sE24EiIG8lNNDln4KIp7bZ/A9Lzc9mF/Nwi/EEQq/EAD0rwvTVDkImyYyat
VjVbnANEWYlm/D8ZXmzcwct6Um1jbbJo+8V9eUs97/T2IiKXoYGzgKqwzkSNEnuH
G/3N6OUCgYEA+LzwEVwwV/PoMxe75whbAcRa2xr8qJJT5cqpngV4INUFFqWzyjOO
3rAZrmyq2oN7JqA82PplY3XHoXVojt067Kq2Vqgj+oJtx9WZoACKX5mmU1Zsvxwy
kuPTfQDQ5JkjtS/N/Snls7A7TgOAy97v0Cp4H3UJpXwKKCV7ifd/eqcCgYEAzXq1
0xHu8Q1EYmG8IulyJ2oJFNX92kkPegHheMnFvqUHnmVFbsj8H5E+FQXNQX1aUS1K
1epDN9LlVKBtWF33WGMCFy6VK0v0MGMZGQ+vI/O01MU8d+DBy2HRKz2UPW3OWevX
9udxLASoaCD/3LCn3eeGT5ucRUw12AIQ6zEzTMMCgYEArL1BlzzHkf0gD4N3Cc4i
rYp4cls+ha8BNr9Upho0P9DP9NdkkZLWsE3pt9ldmdzfhIaZWzIhgT4FQlqwHy8C
QeOYN3wTaGB17uanBpf5gMTK3mtRoDLr6FjxwYj0iRzU0Hp/ekZDcFN+DAKgynRr
ZMxpmacE6PjIcPL+5WSNElcCgYBjjKrgipSvtlTGMUGbzGvgyo+Bx7cH9VOJMbYR
9fdWyM9rHvdHmBoGFTD1sGzj6J5EK+RQxQEx33v5xwuSv1uhN76AirH8Wv0AIFK9
gIrCqUSXvMLx9TMOnOJgx6G1LSjHCesElNaQk+UfJbWwLun1KUE5+lL4g9amQ0H9
IEYRTwKBgQCXpMJ2P0bomDQMeIou2CSGCuEMcx8NuTA9x4t6xrf6Hyv7O9K7+fr1
5aNLpomnn09oQvg9Siz+AMzVEUkkbYmiHf3lDng/RE00hW32SDLJMloJEFmQLCrV
ufxBTlg4v0B3xS1GgvATMY4hyk53o5PffmlRO03dbfpGK/rkTIPwFg==
-----END RSA PRIVATE KEY-----"""


class MergePoolsTests(unittest.TestCase):

    def test_single_pool(self):
        product = 'product1'
        pools = [
                create_pool(product, product, quantity=10, consumed=5)
        ]
        results = merge_pools(pools)
        self.assertEquals(1, len(results.values()))
        result = results.values()[0]
        self.assertEquals(product, result.product_id)

    def test_multiple_pools(self):
        product1 = 'product1'
        product2 = 'product2'
        pools = [
                create_pool(product1, product1, quantity=10, consumed=5),
                create_pool(product1, product1, quantity=55, consumed=20),
                create_pool(product2, product2, quantity=10, consumed=5),
        ]
        results = merge_pools(pools)
        self.assertEquals(2, len(results.values()))
        self.assertTrue(product1 in results)
        self.assertTrue(product2 in results)

        # Check product1:
        merged_pools = results[product1]
        self.assertEquals(product1, merged_pools.product_id)
        self.assertEquals(65, merged_pools.quantity)
        self.assertEquals(25, merged_pools.consumed)

        # Check product2:
        merged_pools = results[product2]
        self.assertEquals(product2, merged_pools.product_id)
        self.assertEquals(10, merged_pools.quantity)
        self.assertEquals(5, merged_pools.consumed)


class PoolFilterTests(unittest.TestCase):

    def test_uninstalled_filter_direct_match(self):
        product1 = 'product1'
        product2 = 'product2'

        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_uninstalled_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_installed_filter_direct_match(self):
        product1 = 'product1'
        product2 = 'product2'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_multi_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided)),
            StubProductCertificate(StubProduct(product2))])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))


        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = pool_filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = pool_filter.filter_product_name(pools, "Foo")
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name_matches_provided(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1, provided_products=[product2]),
        ]
        result = pool_filter.filter_product_name(pools, "Bar")
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])


class InstalledProductStatusTests(unittest.TestCase):

    def test_entitlement_for_not_installed_product_shows_not_installed(self):
        product_directory = StubCertificateDirectory([])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct("product1"))])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("Not Installed", product_status[0][1])

    def test_entitlement_for_installed_product_shows_subscribed(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product)])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("Subscribed", product_status[0][1])

    def test_expired_entitlement_for_installed_product_shows_expired(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product,
                end_date=(datetime.now() - timedelta(days=2)))])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("Expired", product_status[0][1])

    def test_no_entitlement_for_installed_product_shows_no_subscribed(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(1, len(product_status))
        self.assertEquals("Not Subscribed", product_status[0][1])

    def test_one_product_with_two_entitlements_lists_product_twice(self):
        product = StubProduct("product1")
        product_directory = StubCertificateDirectory([
            StubProductCertificate(product)])
        entitlement_directory = StubCertificateDirectory([
            StubEntitlementCertificate(product),
            StubEntitlementCertificate(product)
        ])

        product_status = getInstalledProductStatus(product_directory,
                entitlement_directory)

        self.assertEquals(2, len(product_status))


class TestGetConsumedProductEntitlement(unittest.TestCase):
    def test_emtpy_ent_dir(self):
        entitlement_directory = StubCertificateDirectory([])
        def get_ent_dir():
            return StubCertificateDirectory([])

        managerlib.certdirectory.EntitlementDirectory = get_ent_dir
        a = managerlib.getConsumedProductEntitlements()
        print a

    def test_one_product(self):
        def get_ent_dir():
            product = StubProduct("product1")
            return StubCertificateDirectory([StubEntitlementCertificate(product)])

        managerlib.certdirectory.EntitlementDirectory = get_ent_dir
        a = managerlib.getConsumedProductEntitlements()
        self.assertEquals(len(a), 1)

    def test_one_stacking_product(self):
        def get_ent_dir():
            product = StubProduct("product1", attributes={'stacking_id': 13,
                                                          'multi-entitlement': 'yes',
                                                          'sockets': 1})
            return StubCertificateDirectory([StubEntitlementCertificate(product)])

        managerlib.certdirectory.EntitlementDirectory = get_ent_dir
        a = managerlib.getConsumedProductEntitlements()
        self.assertEquals(len(a), 1)

    def test_ent_cert_no_product(self):
        def get_ent_dir():
            return StubCertificateDirectory([StubEntitlementCertificate(product=None)])

        managerlib.certdirectory.EntitlementDirectory = get_ent_dir
        a = managerlib.getConsumedProductEntitlements()
        print a
        self.assertEquals(len(a), 1)


class TestParseDate(unittest.TestCase):
    def test_now_local_tz(self):
        tz = LocalTz()
        epoch = time.time()
        dt_no_tz = datetime.fromtimestamp(epoch)
        dt = datetime.fromtimestamp(epoch, tz=tz)
        parseDate(dt.isoformat())
        # last member is is_dst, which is -1, if there is no tzinfo, which
        # we expect for dt_no_tz
        #
        # see if we get the same times
        self.assertEquals(dt.timetuple()[:7], dt_no_tz.timetuple()[:7])
#        self.assertEquals(dt.isoformat(), dt_no_tz.isoformat())

    def test_server_date_utc_timezone(self):
        # sample date from json response from server
        server_date = "2012-04-10T00:00:00.000+0000"
        dt = parseDate(server_date)
        # no dst
        self.assertEquals(timedelta(seconds=0), dt.tzinfo.dst(dt))
        # it's a utc date, no offset
        self.assertEquals(timedelta(seconds=0), dt.tzinfo.utcoffset(dt))

    def test_server_date_est_timezone(self):
        est_date = "2012-04-10T00:00:00.000-04:00"
        dt = parseDate(est_date)
        self.assertEquals(timedelta(hours=4), dt.tzinfo.utcoffset(dt))

class TestI18N(unittest.TestCase):
    def test_configure_i18n_without_glade(self):
        configure_i18n()

    def test_configure_i18n_with_glade(self):
        configure_i18n(with_glade=True)


class MockLog:
    def info(self):
        pass


def MockSystemLog(self, message, priority):
    pass

EXPECTED_CONTENT = EXPECTED_CERT_CONTENT + NEW_LINE + EXPECTED_KEY_CONTENT

class ExtractorStub(managerlib.ImportFileExtractor):

    def __init__(self, content, file_path="test/file/path"):
        self.content = content
        self.writes = []
        managerlib.ImportFileExtractor.__init__(self, file_path)

    # Stub out any file system access
    def _read(self, file_path):
        return self.content

    def _write_file(self, target, content):
        self.writes.append((target, content))

    def _ensure_entitlement_dir_exists(self):
        # Do nothing but stub out the dir check to avoid file system access.
        pass

class TestImportFileExtractor(unittest.TestCase):

    def test_contains_key_content_when_key_and_cert_exists_in_import_file(self):
        extractor = ExtractorStub(EXPECTED_CONTENT)
        self.assertTrue(extractor.contains_key_content());

    def test_does_not_contain_key_when_key_does_not_exist_in_import_file(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT)
        self.assertFalse(extractor.contains_key_content());

    def test_get_key_content_when_key_exists(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEquals(EXPECTED_KEY_CONTENT, extractor.get_key_content())

    def test_get_key_content_returns_None_when_key_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_key_content())

    def test_get_cert_content(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEquals(EXPECTED_CERT_CONTENT, extractor.get_cert_content())

    def test_get_cert_content_returns_None_when_cert_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_cert_content())

    def test_verify_valid_entitlement_for_valid_cert(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_invalid_cert(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_cert_content(self):
        extractor = ExtractorStub("", file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_write_key_and_cert(self):
        expected_file_prefix = "12345"
        expected_cert_file = expected_file_prefix + ".pem"
        expected_key_file = expected_file_prefix + "-key.pem"
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path=expected_cert_file)
        extractor.write_to_disk()

        self.assertEquals(2, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])

        write_one = extractor.writes[1]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_key_file), write_one[0])
        self.assertEquals(EXPECTED_KEY_CONTENT, write_one[1])

    def test_write_cert_only(self):
        expected_cert_file = "12345.pem"
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path=expected_cert_file)
        extractor.write_to_disk()

        self.assertEquals(1, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])

class TestMergedPoolsStackingGroupSorter(unittest.TestCase):

    def test_sorter_adds_group_for_non_stackable_entitlement(self):
        pool = self._create_pool("test-prod-1", "Test Prod 1")
        merged = merge_pools([pool])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEquals("", group.name)
        self.assertEquals(1, len(group.entitlements))
        self.assertEquals(pools[0], group.entitlements[0])

    def test_sorter_adds_group_for_stackable_entitlement(self):
        expected_stacking_id = 1234
        pool = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        merged = merge_pools([pool])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEquals("Test Prod 1", group.name)
        self.assertEquals(1, len(group.entitlements))
        self.assertEquals(pools[0], group.entitlements[0])

    def test_sorter_adds_multiple_entitlements_to_group_when_same_stacking_id(self):
        expected_stacking_id = 1234
        pool1 = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])

        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(1, len(sorter.groups))
        group = sorter.groups[0]

        self.assertEquals("Test Prod 2", group.name)
        self.assertEquals(2, len(group.entitlements))

        self.assertEquals(pools[0], group.entitlements[0])
        self.assertEquals(pools[1], group.entitlements[1])

    def test_sorter_adds_multiple_groups_for_non_stacking_entitlements(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")
        pool2 = self._create_pool("test-prod-2", "Test Prod 2")

        merged = merge_pools([pool1, pool2])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEquals("", group1.name)
        self.assertEquals(1, len(group1.entitlements))
        self.assertEquals(pools[0], group1.entitlements[0])

        self.assertEquals("", group2.name)
        self.assertEquals(1, len(group2.entitlements))
        self.assertEquals(pools[1], group2.entitlements[0])

    def test_stacking_and_non_stacking_groups_created(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")

        expected_stacking_id = 1234
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])
        pools = merged.values()
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEquals(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEquals("Test Prod 2", group1.name)
        self.assertEquals(1, len(group1.entitlements))
        self.assertEquals(pools[0], group1.entitlements[0])

        self.assertEquals("", group2.name)
        self.assertEquals(1, len(group2.entitlements))
        self.assertEquals(pools[1], group2.entitlements[0])

    def _create_pool(self, product_id, product_name, stacking_id=None):
        prod_attrs = []
        if stacking_id:
            stacking_id_attribute = {
                "name": "stacking_id",
                "value": stacking_id
            }
            prod_attrs.append(stacking_id_attribute)
        return create_pool(product_id, product_name, productAttributes=prod_attrs)
