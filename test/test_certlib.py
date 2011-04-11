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
import os
from subscription_manager.certlib import *
from subscription_manager.repolib import RepoFile
from subscription_manager.productid import ProductDatabase
from modelhelpers import *
from stubs import *
from rhsm.certificate import GMT


def dummy_exists(filename):
    return True

class PathTests(unittest.TestCase):
    """
    Tests for the certlib Path class, changes to it's ROOT setting can affect
    a variety of things that only surface in anaconda.
    """

    def setUp(self):
        # monkey patch os.path.exists, be careful, this can break things 
        # including python-nose if we don't set it back in tearDown.
        self.actual_exists = os.path.exists
        os.path.exists = dummy_exists

    def tearDown(self):
        Path.ROOT = "/"
        os.path.exists = self.actual_exists

    def test_normal_root(self):
        # this is the default, but have to set it as other tests can modify
        # it if they run first.
        self.assertEquals('/etc/pki/consumer/', Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/etc/pki/consumer/', Path.abs('etc/pki/consumer/'))

    def test_modified_root(self):
        Path.ROOT = '/mnt/sysimage/'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_modified_root_no_trailing_slash(self):
        Path.ROOT = '/mnt/sysimage'
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('/etc/pki/consumer/'))
        self.assertEquals('/mnt/sysimage/etc/pki/consumer/',
                Path.abs('etc/pki/consumer/'))

    def test_repo_file(self):
        # Fake that the redhat.repo exists:
        old = os.path.exists

        Path.ROOT = '/mnt/sysimage'
        rf = RepoFile()
        self.assertEquals("/mnt/sysimage/etc/yum.repos.d/redhat.repo", rf.path)

    def test_product_database(self):
        Path.ROOT = '/mnt/sysimage'
        prod_db = ProductDatabase()
        self.assertEquals('/mnt/sysimage/var/lib/rhsm/productid.js',
                prod_db.dir.abspath('productid.js'))

    def test_sysimage_pathjoin(self):
        Path.ROOT = '/mnt/sysimage'
        ed = EntitlementDirectory()
        self.assertEquals('/mnt/sysimage/etc/pki/entitlement/1-key.pem', 
                Path.join(ed.productpath(), '1-key.pem'))

    def test_normal_pathjoin(self):
        ed = EntitlementDirectory()
        self.assertEquals('/etc/pki/entitlement/1-key.pem', 
                Path.join(ed.productpath(), "1-key.pem"))

class ActionTests(unittest.TestCase):
    key_content = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0JJ/rk1HjrQR2y6yys8IASwznu40Weh5li3Mdaj1GQBfOxnE
F1vWqUKXVTaBRSMkC3jRC+n7HMVIorIcxhmgk8+DP66Ac5yGIDFGYhUJ87knH8Gi
8/0CBqpLQ91okP/bucsEmWy3P+Xn6BFbVJ2JfNCz2FjYk1/rxnC9vJXV4fi50mSH
GN8HloSZrJagY3V6F7prT5t7CSbyKpg94eCJiCzXHB0AoAX7FBzeWrtnmWVcuej8
Gj4dPkD3cozhLi3ztEGDGTrqjbxM7MhkcqvcosqIMQPKgvuNGjQO4URfy+f2lk7X
8dRueYSDifUSevppU42DDR3LDrL8zaSplB/UoQIDAQABAoIBAG6zUtFQcwpqyI9s
2biK6dS1gTB5fY+6s83hwQMyCeSbLfBQXKOJOwXbMjcoFrR7UkZEea+5IG7ExyiT
IHKEZ5YMLb0/AS5bhVTQ0mp8gCu7uehA/hxBzTF8cTYz7awIILcb6fUEnr5raArk
K3Vdp/t3Sf0qKskNwDYy4IGXhU3Jn0hYfvOk8EFnGb80iRHAop1A7CAaQL6vOPDL
vJBSi430dKKS53gTvLIX7mSH3OY/HjEIdYf82yItCgbqiL6+FjUKeRXDAjq1YCpu
FKQwQfJarEwDq670JA8kqak3NsHW/Wwr2CctEzCr59IAmWWwZJY4XAGvBfJYXud/
K15RPYECgYEA/8sg/TzOCEZS8m2LZi5g/CaAjp5yPIBLpoPiJnuzW69bIgJGIqt9
BLPsCI0ehn47SalT7POcTjIPLjFLiun31GCX0JSd6vzQixI++wcYvYUqkCu4iytX
3FW/8mB1gU0CRP2fuhaV4nylpqsRcRW8p+ejX0V1cXjYzotAlSvtFYsCgYEA0L2c
CWrB1kmpzKVixsLJNtVo5SmyEdbtuhsE452lUeBa/bRHXf39n23vH8ePriHJt82l
97bdXrdZu68WW9m12bXdpCZwEyFZx0WW171/DtilKPUpZR9aitN2SK1QKiVNUuXd
AmWvoiRxZ9ZZTUWcWuz/M5pbwLqas48uet9kPAMCgYEAumC/gMU1OkJDXfEDiUhx
0kgbk89PXVX9yS5/MZsgbMWwmW8eu1RIm4ydhv2MKGMBwAJo7FX0peVDulygtm8T
7OMUux4OkpHzQeHhkfbxx+WnxbSVmpHSSvEQEwLFm5kI9kv2fhjGzWgVKwOqicNU
2uKk31403KE5GAXO4OJItVECgYA1gMQj7cctQ8hP+fwtcfPdKCowwtUvmWVplE9W
gCvFprnr2W+JefauDKGEBcSgH2zyvbVSnv5yrpBDeQdEF7Ny0Bi1YFzNqni2iPG2
7o1IouMCcoRftP+iIb1pt3KauuDs5JoXaTTxXGHs+ZX+Jl+DNsfa1C+8YJgSehqx
x9yLPQKBgQCp03t8hrH4CxYA4jHhQnj6wJqHiEP4ewxlGI479+wph9Qb8A9K8bes
xbSoovHHp6e9v55d93YYWMpwgtHLLgqfQyjvOAxz75zbx3BhSHqCt5VHCfgC6dlr
GfcgLc+FXtHMbf+VTvGgeJsDwtSr0WRWojyyvJBMV736CI+04I1TCg==
-----END RSA PRIVATE KEY-----
"""
    cert_content = """-----BEGIN CERTIFICATE-----
MIIEtTCCBB6gAwIBAgIIDe68HxGYKq8wDQYJKoZIhvcNAQEFBQAwRDEjMCEGA1UE
AwwaYWxpa2lucy51c2Vyc3lzLnJlZGhhdC5jb20xCzAJBgNVBAYTAlVTMRAwDgYD
VQQHDAdSYWxlaWdoMB4XDTExMDQwNDAwMDAwMFoXDTEyMDQwMzAwMDAwMFowKzEp
MCcGA1UEAxMgOGE4YjY3OWMyZjIxYzY5MjAxMmY0NjJlMWJhMzAyOTYwggEiMA0G
CSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCuk+G+bFKwGOPTQvTmG55/vf5AZOaX
xz3bt/gMAbBzVCwkrRXzYyFu2IcMr6MhtE7UzdA/3Li8NC1J6T8bpvuLJvnA6jKM
3vpHBI3L9YE2vYgnXdu0aLB/DpKNqElkmSw3fRwpZhTeHkI6DmEJZZ4aRjGg/524
mcmfeVgSkJWS4aYIIUHUdKbrWmZjLn3dSbx+UGfcrafCZnBk8EXGG25vh5KBc7uK
m9ZNy6serrkxIV6FicagObT/J8PNICKvzmzHxOGld4D6xw3g0XO+VNt94gD+1rZn
1+mywro6ZNGxeoMDYmt7S81OkrBHkenWWnPBSBBBDdZG+k0z9ZxzQd2hAgMBAAGj
ggJDMIICPzARBglghkgBhvhCAQEEBAMCBaAwCwYDVR0PBAQDAgSwMHQGA1UdIwRt
MGuAFJkH4LRF+Fhr73thg1s3IpAXxdr1oUikRjBEMSMwIQYDVQQDDBphbGlraW5z
LnVzZXJzeXMucmVkaGF0LmNvbTELMAkGA1UEBhMCVVMxEDAOBgNVBAcMB1JhbGVp
Z2iCCQCe/CAbegkH5DAdBgNVHQ4EFgQUJOO6190WrguRM6/z7f1BgYtCQi4wEwYD
VR0lBAwwCgYIKwYBBQUHAwIwIQYKKwYBBAGSCAkEAQQTDBFNYW5hZ2VtZW50IEFk
ZC1PbjAwBgorBgEEAZIICQQCBCIMIDhhOGI2NzljMmYyMWM2OTIwMTJmMjFjNzE1
ZWYwMTFmMB4GCisGAQQBkggJBAMEEAwObWFuYWdlbWVudC0xMDAwEQYKKwYBBAGS
CAkEBQQDDAE1MCQGCisGAQQBkggJBAYEFgwUMjAxMS0wNC0wNFQwMDowMDowMFow
JAYKKwYBBAGSCAkEBwQWDBQyMDEyLTA0LTAzVDAwOjAwOjAwWjASBgorBgEEAZII
CQQMBAQMAjkwMBIGCisGAQQBkggJBAoEBAwCNDUwGwYKKwYBBAGSCAkEDQQNDAsx
MjMzMTEzMTIzMTARBgorBgEEAZIICQQOBAMMATEwEQYKKwYBBAGSCAkECwQDDAEx
MDQGCisGAQQBkggJBQEEJgwkZmJmNmI4MzgtMWM3Ny00OTBlLWE2YTktY2UxMjZh
YjZiODgyMA0GCSqGSIb3DQEBBQUAA4GBAA5DRvx5BD2pgsC4GOwjtmYJgxpXKHEK
EF5Awg/Ct+UyPCSP3ttsvW3DlT6eGVpLh09+EmR+6UEka2VywQsOm/2WHaNomk/o
hu0hZhU+U78AoV3eFtIGhNUpHZ66bXsqPnQ0u1G/XHL1cb38LFUkFBVjCvzvQCyi
vHkM1ggwdhJ5
-----END CERTIFICATE-----
"""

    def test_action(self):
        action = Action()

    def test_action_build(self):
        action = Action()
        bundle = {'key': self.key_content,
                   'cert': self.cert_content}
        key, cert = action.build(bundle)
        assert(key.content == self.key_content)
        print cert.serialNumber()


class FindLastValidTests(unittest.TestCase):

    def test_just_entitlements(self):
        cert1 = StubEntitlementCertificate(
                    StubProduct('product1'), start_date=datetime(2010, 1, 1),
                    end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime(2010, 1, 1),
                    end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])
        prod_dir = StubCertificateDirectory([])
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir,
                product_dir=prod_dir)
        self.assertEqual(2050, last_valid_date.year)
        self.assertEqual(2, last_valid_date.day)

    def test_unentitled_products(self):
        cert = StubProductCertificate(StubProduct('unentitledProduct'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)

    def test_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        product_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProductCertificate(StubProduct('product2')),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir=ent_dir, product_dir=product_dir)
        self.assertEqual(2050, last_valid_date.year)

    def test_all_expired_entitlements(self):
        pass


class CertSorterTests(unittest.TestCase):

    def setUp(self):
        # Setup mock product and entitlement certs:
        self.prod_dir = StubCertificateDirectory([
            # Will be unentitled:
            StubProductCertificate(StubProduct('product1')),
            # Will be entitled:
            StubProductCertificate(StubProduct('product2')),
            # Will be entitled but expired:
            StubProductCertificate(StubProduct('product3')),
        ])

        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('product2')),
            StubEntitlementCertificate(StubProduct('product3'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2)),
            StubEntitlementCertificate(StubProduct('product4'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() + timedelta(days=365),
                order_end_date=datetime.now() - timedelta(days=2)) # in warning period
        ])

    def test_unentitled_product_certs(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue('product1' in self.sorter.unentitled_products)

    def test_entitled_products(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(2, len(self.sorter.valid_products.keys()))
        self.assertTrue('product2' in self.sorter.valid_products)
        self.assertTrue('product4' in self.sorter.valid_products)

        self.assertEqual(2, len(self.sorter.valid_entitlement_certs))
        self.assertTrue(cert_list_has_product(
            self.sorter.valid_entitlement_certs, 'product2'))
        self.assertTrue(cert_list_has_product(
            self.sorter.valid_entitlement_certs, 'product4'))

    def test_expired(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEqual(2, len(self.sorter.expired_entitlement_certs))

        self.assertTrue(cert_list_has_product(
            self.sorter.expired_entitlement_certs, 'product3'))
        # Certificate in warning period should show up as expired, even though
        # they can technically still be used. We use the CertSorter to warn
        # customer of invalid entitlement issues.
        self.assertTrue(cert_list_has_product(
            self.sorter.expired_entitlement_certs, 'product4'))

        self.assertEqual(1, len(self.sorter.expired_products.keys()))
        self.assertTrue('product3' in self.sorter.expired_products)

    def test_expired_in_future(self):
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                on_date=datetime(2050, 1, 1))
        self.assertEqual(3, len(self.sorter.expired_entitlement_certs))
        self.assertTrue('product2' in self.sorter.expired_products)
        self.assertTrue('product3' in self.sorter.expired_products)
        self.assertFalse('product4' in self.sorter.expired_products) # it's not installed
        self.assertTrue('product1' in self.sorter.unentitled_products)
        self.assertEqual(0, len(self.sorter.valid_entitlement_certs))

    def test_entitled_products(self):
        provided = [StubProduct('product1'), StubProduct('product2'),
                StubProduct('product3')]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEquals(3, len(self.sorter.valid_products.keys()))
        self.assertTrue('product1' in self.sorter.valid_products)
        self.assertTrue('product2' in self.sorter.valid_products)
        self.assertTrue('product3' in self.sorter.valid_products)

    def test_expired_but_provided_in_another_entitlement(self):
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=[StubProduct('product3')]),
            StubEntitlementCertificate(StubProduct('mktproduct'),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=2),
                provided_products=[StubProduct('product3')]),
            StubEntitlementCertificate(StubProduct('product4'))
        ])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir)
        self.assertEquals(1, len(self.sorter.valid_products.keys()))
        self.assertTrue('product3' in self.sorter.valid_products)
        self.assertEquals(0, len(self.sorter.expired_products.keys()))
        self.assertEquals(2, len(self.sorter.unentitled_products.keys()))

    def test_multi_product_entitlement_expired(self):
        # Setup one ent cert that provides everything we have installed (see setUp)
        provided = [StubProduct('product2'), StubProduct('product3')]
        self.ent_dir = StubCertificateDirectory([
            StubEntitlementCertificate(StubProduct('mktproduct'),
                provided_products=provided)])
        self.sorter = CertSorter(self.prod_dir, self.ent_dir,
                on_date=datetime(2050, 1, 1))

        self.assertEquals(1, len(self.sorter.expired_entitlement_certs))
        self.assertEquals(2, len(self.sorter.expired_products.keys()))
        self.assertTrue('product2' in self.sorter.expired_products)
        self.assertTrue('product3' in self.sorter.expired_products)

        self.assertEquals(1, len(self.sorter.unentitled_products.keys()))
        self.assertTrue('product1' in self.sorter.unentitled_products)


def cert_list_has_product(cert_list, product_id):
    for cert in cert_list:
        for product in cert.getProducts():
            if product.getHash() == product_id:
                return True
    return False


