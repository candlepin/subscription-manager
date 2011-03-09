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

import unittest
from mock import Mock

from managerlib import *
from modelhelpers import *
from stubs import *

class MergePoolsTests(unittest.TestCase):

    def test_single_pool(self):
        facts = Mock()
        product = 'product1'
        pools = [
                create_pool(product, product, quantity=10, consumed=5)
        ]
        results = merge_pools(pools)
        self.assertEquals(1, len(results.values()))
        result = results.values()[0]
        self.assertEquals(product, result.product_id)

    def test_multiple_pools(self):
        facts = Mock()
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
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_uninstalled_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = filter.filter_out_uninstalled(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product2, result[0]['productId'])

    def test_installed_filter_direct_match(self):
        product1 = 'product1'
        product2 = 'product2'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(product2))])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_provided_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided))])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))


        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_installed_filter_multi_match(self):
        product1 = 'product1'
        product2 = 'product2'
        provided = 'providedProduct'
        pd = StubCertificateDirectory([
            StubProductCertificate(StubProduct(provided)),
            StubProductCertificate(StubProduct(product2))])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))


        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2, provided_products=[provided]),
        ]
        result = filter.filter_out_installed(pools)
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1),
                create_pool(product2, product2),
        ]
        result = filter.filter_product_name(pools, "Foo")
        self.assertEquals(1, len(result))
        self.assertEquals(product1, result[0]['productId'])

    def test_filter_product_name_matches_provided(self):
        product1 = 'Foo Product'
        product2 = 'Bar Product'
        pd = StubCertificateDirectory([])
        filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]))

        pools = [
                create_pool(product1, product1, provided_products=[product2]),
        ]
        result = filter.filter_product_name(pools, "Bar")
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
