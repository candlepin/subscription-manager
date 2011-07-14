#
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
import os
from os import linesep as NEW_LINE
import unittest
from subscription_manager.gui.importsub import ImportFileExtractor
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

EXPECTED_CONTENT = EXPECTED_CERT_CONTENT + NEW_LINE + EXPECTED_KEY_CONTENT

class ExtractorStub(ImportFileExtractor):

    def __init__(self, content, file_path="test/file/path"):
        self.content = content
        ImportFileExtractor.__init__(self, file_path)

    # Stub out any file system access
    def _read(self, file_path):
        return self.content

class TestImportFileKeyExtractor(unittest.TestCase):

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
        writes = []

        def write_file_override(target, content):
            writes.append((target, content))

        expected_file_prefix = "12345"
        expected_cert_file = expected_file_prefix + ".pem"
        expected_key_file = expected_file_prefix + "-key.pem"
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path=expected_cert_file)
        extractor._write_file = write_file_override

        extractor.write_to_disk()

        self.assertEquals(2, len(writes))

        write_one = writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])

        write_one = writes[1]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_key_file), write_one[0])
        self.assertEquals(EXPECTED_KEY_CONTENT, write_one[1])

    def test_write_cert_only(self):
        writes = []

        def write_file_override(target, content):
            writes.append((target, content))

        expected_cert_file = "12345.pem"
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path=expected_cert_file)
        extractor._write_file = write_file_override

        extractor.write_to_disk()

        self.assertEquals(1, len(writes))

        write_one = writes[0]
        self.assertEquals(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEquals(EXPECTED_CERT_CONTENT, write_one[1])
