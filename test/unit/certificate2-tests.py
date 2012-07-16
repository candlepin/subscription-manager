#
# Copyright (c) 2012 Red Hat, Inc.
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
from datetime import datetime

import certdata
from rhsm.certificate import create_from_pem, CertificateException
from rhsm.certificate2 import *


class V1CertTests(unittest.TestCase):

    def setUp(self):
        self.prod_cert = create_from_pem(certdata.PRODUCT_CERT_V1_0)
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V1_0)

    def test_no_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem, "")

    def test_junk_contents_throws_exception(self):
        self.assertRaises(CertificateException, create_from_pem,
                "DOESTHISLOOKLIKEACERTTOYOU?")

    def test_factory_method_on_product_cert(self):
        self.assertEquals("1.0", str(self.prod_cert.version))
        self.assertTrue(isinstance(self.prod_cert, ProductCertificate))
        self.assertEquals(1, len(self.prod_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.prod_cert.products[0].name)

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("1.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)
        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)
        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)

    def test_is_valid(self):
        self.assertTrue(self.ent_cert.is_valid(on_date=datetime(2012, 12, 1)))
        self.assertFalse(self.ent_cert.is_valid(on_date=datetime(2014, 12, 1)))

    def test_order(self):
        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)

    def _find_content_by_label(self, content, label):
        """ Just pulls out content from a list if label matches. """
        for c in content:
            if c.label == label:
                return c

    def test_content(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "always-enabled-content")
        self.assertEquals("always-enabled-content", content.name)
        self.assertEquals(True, content.enabled)
        self.assertEquals("/foo/path/always/$releasever", content.url)
        self.assertEquals("/foo/path/always/gpg", content.gpg)

    # TODO: test exception when cert major version is newer than we can handle


# TODO: move to certdata:
BAD_PADDING_CERT = """
-----BEGIN CERTIFICATE-----
MIIGgzCCBeygAwIBAgIITl1llqNEc7wwDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MTYwMDAwMDBaFw0xMzA3MTYwMDAwMDBaMCsxKTAnBgNVBAMTIGZmODA4
MDgxMzg5MTM2MmMwMTM4OTE2ZjQ3NGUwMDIzMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAk1q95ucrThIhRg5fP9R7I1Sj7uSvEFvsZD/wyoDqxjLQEMyd
1QTrlomEQWMx+Eb6BIKeumVpftKl3UqfQzb+P6lxlZyTsCIYy89WFNWuBChVHkUO
Rgz0hZ1lsKbHfNeS3mViiXZQNF/NjKgmlHAGWbPcvXE6+GcAm4qFizFpI2zgr0JU
OT3TZFyEfmaMEXND7EmXV9pNVRGSTzvBMZMwJr9/Igz9hjGti3QVCmCptr7tL5RZ
WpniKxu22OGwrRTpABHkvU2v9jOCMlZD4XYW886Zzf+iQlIboB9cfY5XACVW5+TI
aJYrSmCC/aXow56oslC6t/4FIV8UIjUqnhnWZwIDAQABo4IEHzCCBBswEQYJYIZI
AYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDBmBgNVHSMEXzBdgBREQHYTNskB3AHY
/8EcmROo5jrOoqE6pDgwNjEVMBMGA1UEAwwMMTkyLjE2OC4xLjI1MQswCQYDVQQG
EwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAPMeoqmMwB3XMB0GA1UdDgQWBBQvDaNz
Y436x2Xt/rOaiMjgsN5ztjATBgNVHSUEDDAKBggrBgEFBQcDAjCCA0cGCSsGAQQB
kggJBwSCAzgMggM0ZUp5dGxrdVBtekFRZ1A5S1pPMHhGQnNUQjNKclQ3MVZhbnRx
RmEwTW1BUXRZR3FiVGFKVi9udkhQUEpheUViWkpDRVlQT09aYjJZODhJYWtTb1JD
aXpjVXk5SW9IaHUwUU9FY1RaRTJYTmtMRHhQUHdYT0hzTjhZTDVyZkg1am1jU3py
MGdvUWoxSkNLSndJM1A5WDg5Smtab2NXQkU5UldSZVJYUjZsYVlEaFMyZ1E0bERn
Q0hlamVKNTZtT0laYUlveWFjM1JkK2IyNEU0ZDZWaGxsY2xrYWQzVk1uNFJSb01a
Qm1aNElVRDM2MFpvV1lqSmoxK1RWS3JKTm1EUHpIY3pGakEzNHpDcXF0Z2VNTkkw
eE52bTM1SysxS0RNVzJXcEhmRXExTTZzczNJRmt4dXVTanRhVUx3L281dmFpT202
YVBCWU1Kc0hJdkNkS1BLcDQwZiszQW41TEhROHlsam9oMkdZOEFBV3E1Uk02dGg2
L2JjTnVMQVJoSEZtMFFraEhtc0N3YU5jd0oyVTUxcE1VU0VNVDdqaHoySmJaUXBB
S2NNUTIxY0ltTFRHZjRwazhwMGJkSWpERWFXaHRZYTVXY09FYTgrdWtlNUJ3dTBs
VnRYcXVWYjVzQkJNdWlDVDgwamtnK3ViWFdVTjcrb0NjbldDUXg2TDA2VHRLazR2
Y1I5T3J6MkdNM3NzamkzS3F6U2R3SDB3bmZJZ0N4cncyenR6MndodG5PN3E2SHEr
NFR2WUlHMEluTDZDandpcGxLMkxyYVQ3cEVRdXVMWTc2cHpqVWhDbVRpSEc3SXds
aGo0NE1kQXlyaWVtRmJnek1hM3lHSXYvV0phMkMxNmxPWWpjeDNOUUh5TEN0OUN3
ajB1dnREVjBTK1dWVjRxdG1idW90YkdGeDlJVFBMeERmOVNmUDlPZHgwRUlIV29D
TnpzKzRQUlRCRHVkcTNoOXV1M2RVNDI3TUM0UWx0TU9BWjk4aU8xbzFuUm1SR3hx
SmV3akZoMEtzOXR4ZmI5dFE5NDl1dnFlMzd3TUxELzFMakg1bGhuckxtRHI1alVG
MFMvZzJYNjUvdzk0YWYybTASBgkrBgEEAZIICQYEBQwDMi4wMA0GCSqGSIb3DQEB
BQUAA4GBAIor4WsvMyG4tLuS78Yyxf9la+OHDXJxwHN8i24g0uajmrQ269ZdPDWm
9z7vliPlYQ0Cdy3Qk6lvxyyBQnFubbA223RJXD8vt21APZg9FCK1E+cD5Le4x9sO
g0yNCN/I5b8Tk4SSuB+1uIqNf/wyHFVyNQF+SIYRICczWm050MTB
-----END CERTIFICATE-----
"""


BAD_HEADER_CERT = """
-----BEGIN CERTIFICATE-----
MIIGgzCCBeygAwIBAgIIDFOYEsAlgt0wDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MTYwMDAwMDBaFw0xMzA3MTYwMDAwMDBaMCsxKTAnBgNVBAMTIGZmODA4
MDgxMzg5MTM2MmMwMTM4OTE2YTRiYmUwMDEzMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAghXR3hzHx96ceHyRvZAi2wVbMdBNLHZhwuF3HPgxMs3OHr2K
YjKaStkg0qioPKu02WkDk6aCJT7+3BiLD7CKnZ98nqMXh2wErq6JQCnMeplDsbON
3It2QVifxtOLZ18fUtU1RtdfPP9PyBgQOQs5et67AniFY1nglN/rpQRpl+PKSZrM
Oh0Im4lxblNFcccaXQ5PhLVFGc/QL65ukKdjKnQdi8AFWz81J3JgsciM5gfc7G31
kqTl7wgSGgDH10rbffKXx1gpE7F1Su/vZa+oKxZnZyHFPsfasJ2jUOFZmQ50k1eU
ZqcoFTTYIPdBUP1GfKRqLFY9NpKbpFoVV5xXkQIDAQABo4IEHzCCBBswEQYJYIZI
AYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDBmBgNVHSMEXzBdgBREQHYTNskB3AHY
/8EcmROo5jrOoqE6pDgwNjEVMBMGA1UEAwwMMTkyLjE2OC4xLjI1MQswCQYDVQQG
EwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAPMeoqmMwB3XMB0GA1UdDgQWBBS2WJuf
1Xj1rSzXUqok1SnWAwtW9DATBgNVHSUEDDAKBggrBgEFBQcDAjCCA0cGCSsGAQQB
kggJBwSCAzgMggM0ZUp5dGx0MlBvakFRd1A4VjAreWpIQzFWQk4vdW52YnRrcnQ3
dW9zeHBSUWxDNVJ0eTZyWitML2ZsQSsvRmx6anFpS0Z6blRtTnpNZGVFZFN4VUto
K1R2aXNqQ0tjWVBtS0p5aE1kS0dLWHZoWWVJNWVPWVEvdy9HOC9yM0Y2WVo1N0lx
ckFEeEtDV0V3b25BL2RlS0ZTWTFPelFuZUl5S0tvL3M4aWhKQWd4ZlFvTVFod0pI
dUIzeFdlSmhpcWVnS1lxNE1VYy9tTnVETzFXa3VVcExrOHJDdXFzbGZ4RkdneGtm
ekxCY2dPNzNqZEF5RjZPZnYwZUpWS050NEMvOWladjZnZSttREVabHllMEJJMDFE
dkszL0xlbExCY3FzVVpiYUVXOUM3Y3c2TFZZd3VXR3FzS001eGZzenVyR05tSzd5
R3M5aklRbmpnRGc4eHI0em1Vd1RKNXo1TXdkekpqek9KbDZNUTFpc1ZES3V1UFg2
WHhOd1lTTUk0OVNpRTBJOHZ3NEVpeklCZHhLV2FURkd1VEFzWm9ZdHhiWk1GWUJT
SDBOczN5QmcwaHIvSmVMUk16UG9FSWNqU2sxckRUT3poZ25YbmwwajNZT0UyMG1z
eXRXeVVsbS9FRXk2SUpPeFNHUzk2NXRkYVEzdnFoeHlkWUpESG90VHArMHFUaWR4
SDA2blBZUXpmU3lPTGNxck5LM0FmVEN0Y2k4TDZ2SGJPM1BiQ0cyYzl1cm9lclpo
TzlnZ1RRaWNyb0tQQ0ltVWpZdU5wUHVrUkNhWXRqdnFuT05TRUtaT0lZYnNEQ1dH
UGpneDBES3VKNllSdURNeGpmSVF5K1N4TEUwWHZFcHpFTG1QNTZEZVI0UnZvZkUv
TDczQzF0QXRsVmRjS2JaNjdxTFdoaFllU2svdzhBNzlXWC8rU25jZUJpRzByd25j
N0hpUDAwOFI3SFNtK1BwMDI3dW5HbmRoWENBc3hpMENQdmtRMjlHczZkUUliaW9s
N0NNV0hRcXozWEZkdjIxQzNqNjZ1cDVmdnd3c3Z2UXVNZnFSR3VzdVlPdjZOUVhS
YitEWmZySC9EeWJnL2pzPTASBgkrBgEEAZIICQYEBQwDMi4wMA0GCSqGSIb3DQEB
BQUAA4GBAJHm4ShJiIbG234Z5m0sJ2LY8M6Xrs8t2tnz7bClpd9+oMKl5t6HgQAf
JtS3cbsiUhDYqWprrpuG8sq9Cg9mO8dU2TgUVQkF1KInLr+JGhTlAZkkMfaKn/6g
u79SxF0zp0gfXHKi2iz/t16Xaq//vVhyF0BrlmUJHGDlAe5nNNHR
-----END CERTIFICATE-----
"""



class V2CertTests(unittest.TestCase):

    def setUp(self):
        self.ent_cert = create_from_pem(certdata.ENTITLEMENT_CERT_V2_0)

    def test_factory_method_on_ent_cert(self):
        self.assertEquals("2.0", str(self.ent_cert.version))
        self.assertTrue(isinstance(self.ent_cert, EntitlementCertificate))
        self.assertEquals(2012, self.ent_cert.start.year)
        self.assertEquals(2013, self.ent_cert.end.year)

        self.assertEquals("Awesome OS for x86_64", self.ent_cert.order.name)

        self.assertEquals(1, len(self.ent_cert.products))
        self.assertEquals('Awesome OS for x86_64 Bits',
                self.ent_cert.products[0].name)

    def test_is_valid(self):
        self.assertTrue(self.ent_cert.is_valid(on_date=datetime(2012, 12, 1)))
        self.assertFalse(self.ent_cert.is_valid(on_date=datetime(2014, 12, 1)))

    def _find_content_by_label(self, content, label):
        """ Just pulls out content from a list if label matches. """
        for c in content:
            if c.label == label:
                return c

    def test_order(self):
        self.assertEquals(2, self.ent_cert.order.quantity_used)
        self.assertEquals("1", self.ent_cert.order.stacking_id)
        self.assertEquals("awesomeos-x86_64", self.ent_cert.order.sku)

    def test_content_enabled(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "always-enabled-content")
        self.assertEquals("always-enabled-content", content.name)
        self.assertEquals(True, content.enabled)
        self.assertEquals(200, content.metadata_expire)
        self.assertEquals("/foo/path/always/$releasever", content.url)
        self.assertEquals("/foo/path/always/gpg", content.gpg)

    def test_content_disabled(self):
        self.assertEquals(4, len(self.ent_cert.content))
        content = self._find_content_by_label(self.ent_cert.content,
                "never-enabled-content")
        self.assertEquals("never-enabled-content", content.name)
        self.assertEquals(False, content.enabled)

    def test_bad_padding(self):
        # Just want to see this pass, it would fail to decode the JSON in the past:
        cert = create_from_pem(BAD_PADDING_CERT)

    def test_bad_header(self):
        # Just want to see this pass, it would fail to decode the JSON in the past:
        cert = create_from_pem(BAD_HEADER_CERT)


class IdentityCertTests(unittest.TestCase):

    def test_creation(self):
        id_cert = create_from_pem(certdata.IDENTITY_CERT)
        self.assertTrue(isinstance(id_cert, IdentityCertificate))
        self.assertEquals("DirName:/CN=redhat.local.rm-rf.ca", id_cert.alt_name)
        self.assertEquals("eaadd6ea-852d-4430-94a7-73d5887d48e8", id_cert.subject['CN'])
        self.assertFalse(hasattr(id_cert, 'products'))


class ContentTests(unittest.TestCase):

    def test_enabled(self):
        c = Content(name="mycontent", label="mycontent", enabled=None)
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled="1")
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled=True)
        self.assertTrue(c.enabled)
        c = Content(name="mycontent", label="mycontent", enabled="0")
        self.assertFalse(c.enabled)
        self.assertRaises(CertificateException, Content, name="mycontent",
                label="mycontent", enabled="5")


class ProductTests(unittest.TestCase):

    def test_arch_multi_valued(self):
        p = Product(id="pid", name="pname", architectures="i386,x86_64")
        self.assertEquals(2, len(p.architectures))
        self.assertEquals("i386", p.architectures[0])
        self.assertEquals("x86_64", p.architectures[1])



