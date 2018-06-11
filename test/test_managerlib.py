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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from datetime import datetime, timedelta
import os

from .stubs import StubCertificateDirectory, StubProductCertificate, \
        StubProduct, StubProductDirectory, StubCertSorter
from .fixture import SubManFixture
from subscription_manager.managerlib import merge_pools, PoolFilter, \
        MergedPoolsStackingGroupSorter, MergedPools, \
        PoolStash, allows_multi_entitlement, valid_quantity
from subscription_manager.injection import provide, \
        PROD_DIR
from .modelhelpers import create_pool
from subscription_manager import managerlib
import rhsm
from rhsm.certificate import create_from_pem, DateRange, GMT
from mock import Mock, patch

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

EXPECTED_CERT = create_from_pem(EXPECTED_CERT_CONTENT)

# Used to simulate importing a valid bundle (cert+key) but when
# the cert is not actually an entitlement cert.
IDENTITY_CERT_WITH_KEY = """
-----BEGIN CERTIFICATE-----
MIIDVTCCAr6gAwIBAgIIdv1ldZ5/0IQwDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MzAxMzE5NTdaFw0yODA3MzAxMzE5NTdaMC8xLTArBgNVBAMTJDU2MzA4
ODU4LTZhOTMtNGFmZC04YjIyLWY1MjFhZmFlNTRiZjCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAJUDAlagg+Pbew+blR2S+DkDMZ81hfY3L10yalEDsXsq
NtX7eXG6eiSnsKXfZKpJXEZ1qIuW3OZEtOoBl5EWyQipBCsBufS4KKA2VbH5r8EA
gJKKXmu17pT9VH1mZ6A+eFUUAJU8CTvnNEchZLM9DZEoki4mPDiEizMPLpOzwtGp
KKaTIBWU8Fp1uO66EadjLsE/gbPSo4V1q60JE1P7qNHm07qVAM1OEKENxj4j49mr
bsiCPmVjppk+OezqwtJUseWEq/pAEYtOGJNy61l9EfFpp1HvaqdEsymjTal25j77
kMbNUIPRvOctB7ZKeoO1xThfK9Saw0RZDJqg7dxDcccCAwEAAaOB7jCB6zARBglg
hkgBhvhCAQEEBAMCBaAwCwYDVR0PBAQDAgSwMGYGA1UdIwRfMF2AFERAdhM2yQHc
Adj/wRyZE6jmOs6ioTqkODA2MRUwEwYDVQQDDAwxOTIuMTY4LjEuMjUxCzAJBgNV
BAYTAlVTMRAwDgYDVQQHDAdSYWxlaWdoggkA8x6iqYzAHdcwHQYDVR0OBBYEFLAY
15fAInsF+qo+KH90JLEpiVNsMBMGA1UdJQQMMAoGCCsGAQUFBwMCMC0GA1UdEQQm
MCSkIjAgMR4wHAYDVQQDDBVyZWRoYXQubG9jYWwucm0tcmYuY2EwDQYJKoZIhvcN
AQEFBQADgYEAFZRsK8LUJ/WnbpG1069xCKy5xlKDWfTll7ckCEDWOVsviZ09aYKz
Ceh5YXCYA+LJaNfePhGgASl/EdPB0ICdXefGM0Eg1OB+xGOAf0KU1OvVhxxp3q/D
8X8FZinFLArJpXIk64kKggIRRAiFnfIBl1lkL9vt39f0F+qIgjBKV9Q=
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAlQMCVqCD49t7D5uVHZL4OQMxnzWF9jcvXTJqUQOxeyo21ft5
cbp6JKewpd9kqklcRnWoi5bc5kS06gGXkRbJCKkEKwG59LgooDZVsfmvwQCAkope
a7XulP1UfWZnoD54VRQAlTwJO+c0RyFksz0NkSiSLiY8OISLMw8uk7PC0akoppMg
FZTwWnW47roRp2MuwT+Bs9KjhXWrrQkTU/uo0ebTupUAzU4QoQ3GPiPj2atuyII+
ZWOmmT457OrC0lSx5YSr+kARi04Yk3LrWX0R8WmnUe9qp0SzKaNNqXbmPvuQxs1Q
g9G85y0Htkp6g7XFOF8r1JrDRFkMmqDt3ENxxwIDAQABAoIBAQCFUifpcbwPRfQY
xs7novNLrzvagnzVChLqg4zz5yYIWICve0vxITLfUNmPzwu1/+T7dZHTMqt5qsdj
BwGg4o4DnZUJFYZXGd3fWj3Z+tfxCo3+jqZkIGbSDsZlXBYjHUF0fWz4GLr6SaZQ
beQ3KczVr0L632LJ/my8xjyaEh+gjSACu0XxnX956O/1x/WTmZLUrLqwymm8ZwSC
+1HOnlbj67dw0jBpi1HwefNtTCjElgIinKQZXitDmWYMzFsIBebfzM563xy5PINa
8mI4IprCFC9TWNgdNmMHnferdNteSmqH+a0G8YHc2yBAB4Yf41SB7mpWzkkFBJ5K
9Pccz82hAoGBAO9La6Cg+ODcZoOqqE2upYMt4UWKx9yj0TZ3+s8mazg81k/HaylV
5L6NS4H/VCiG17RhidI82z9807IeaVL4w7ZvpaYwFeMLEzagxzcZz6MzZIrXbyYd
cDQCf9ZlEAGBO6tWSlKvG6fgnZU4gpReMgs38q9VKomZTx0sjx60hUizAoGBAJ9q
Fr9Mf3w01RknrH8YylsO7O722L/4kaU9t+wnESzmktUIBoHcVcxpPnf53d5IVjRv
iG7/AwMxj87ovjYUEMlHpW9XcF6y+Vs30bwhnm+lu4xRZAx9DZ6LN++5tAAypMWF
3m1MgEFs6R5NejGXmTAM8y61krMGt0hf0ov2+LSdAoGAcIsxQGfVBbTDBjPyWi7E
q1CdvZ5K54uobwy4ykqQbO+3/+eTj+pU3gYIOEjE5RaeRrkFH/r9RvvHeONyt9JG
Afy6lNHSyWjBDZVKfLDIBkK6i85M+UkpJ1zxkP0RLRQB41B/PiobQLaUhsUALRWs
Rbh3jFzq17JiEh+N5GwUr58CgYAZuHY/G0qeca/IRTxxrUBI/NmBnNZP8v0c2h5o
vczpn7IlKQxTu4ckWf64QNppWOZ/w1cSAZcs1rxLOAYol4g10ZeBpWv9+4Z8Dz+J
ySrU/LqL4z3vPeYKpI+74AyI06L+M6E1pVg0NixOtVV31uvictRxvt4SgIzl4oAI
ESsDiQKBgQCTLo0f327QjLJuQpalQfRTDKXoQWOUhEGC1LLw21uvLSFEDbVIUjeH
UFsAtbXIRAREdmZrLABgUgYUvoLQc3+GgVYMo0v4nCxUs8FDbcKkT6Hb8XcVqEhy
HcikfLxQfRwalftfq5mDxkA8FDxrbGd/N8AviC2JJNL+VzMVthjy0w==
-----END RSA PRIVATE KEY-----
"""

EXPECTED_CERT_CONTENT_V3 = """-----BEGIN CERTIFICATE-----
MIIDrjCCAxegAwIBAgIIPjHvQ1mahX4wDQYJKoZIhvcNAQEFBQAwUjExMC8GA1UE
AwwoanNlZmxlci1mMTQtY2FuZGxlcGluLnVzZXJzeXMucmVkaGF0LmNvbTELMAkG
A1UEBhMCVVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcNMTIwOTI0MDAwMDAwWhcNMTMw
OTI0MDAwMDAwWjArMSkwJwYDVQQDEyA4YTkwZjgxZDM5ZmFjMGVlMDEzOWZlMzhl
NGY2MzE3ZjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAK+Dq57Pnq5i
IvRT+nyvSMvhxTyzoBQ67Do3AKG0LvRopKLq0gNjouuJCUrLSGIVy2yEnbM+HPnX
Nkh/QLsOc6QUcBSVlnFV/Xd/sXB+GtWoy1GzcmMNUUoNDbdIZjj+Omdm0/8ueofG
1QDOH4RZHR25lquDovkZU/WzSv5XKyiqPqFiHt+D8QFRXiHb7i6+yLThF4nNdtkk
97yai3xHRrRVqWhqR8nYIF7dPHsTByMUSaoRz5iKO5rmg9BBrZE4+kDZLFE+28wR
xtzD/Die2GdJwe7mQ5m0HUJC+1g9lyOruAyUKbJxl95HxGObBQZmVMddOZjNC14W
Dwt4kLf/qXECAwEAAaOCAS4wggEqMBEGCWCGSAGG+EIBAQQEAwIFoDALBgNVHQ8E
BAMCBLAwgYIGA1UdIwR7MHmAFIwL3uxPnqv0NKLwhuL/TkX149zOoVakVDBSMTEw
LwYDVQQDDChqc2VmbGVyLWYxNC1jYW5kbGVwaW4udXNlcnN5cy5yZWRoYXQuY29t
MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAMZok6HSfyb6MB0GA1Ud
DgQWBBQH/TRkcUo2VBq+LlvyqSpAMaEQiDATBgNVHSUEDDAKBggrBgEFBQcDAjAS
BgkrBgEEAZIICQYEBQwDMy4wMDsGCSsGAQQBkggJBwQuBCx42stLLUstYkjLz2dQ
KUrNSU0sBvMTc8oTK4sZChJLMhgA1NoL9QX6yNyT6DANBgkqhkiG9w0BAQUFAAOB
gQAMWeuSinQawzoJ8TvcbuC/d3dmJQIPPGNFbFNwADoBEfW4S9bblroMTgms1W5n
yFwoJo9WNjnDJbnHFdmesXeA07YkdklMkzfbTtTE+GiTLfd5gjYIkTLka8CaYVpw
6kWfcQe8CI7/15rhjCukzTJvguAMDNlGFNlHwXRA+NWTPw==
-----END CERTIFICATE-----"""

EXPECTED_CERT_ENTITLEMENT_V3 = """-----BEGIN ENTITLEMENT DATA-----
eJy1VV1vmzAU/SvI2iM0NuSD8NZO2l4ybVL6tCqqjLmhqGBTY7eLovz3XUNa0jVk
2dZFkcDcyzn3nHtttkQo2dgKNElIGM/G8QTSIBLxOhiHGQ3SSUiD6VRkDKYQ80wQ
nzxYLk1hNiRhPmls2ghd1KZQkiRb0txbROJP0KgKVBM0oB8R3CeSV4CRyy7ifV16
yzbkXVmZlZBhyhPXspA5SSKKwErcg2lIEvqk4pLnUIE0JDHaAkbx3UKAYyzhEUpE
/qahKmyFOGZTO6qFC3gR2e18onTmJG6JtFXaio35nK5jlkXzNRcUgLL2jqWzGaU0
nrwSOkFGw7VxJlEWBnQehONrSpP2/x1zQWZdMDoSRI+N5sK9PsUlF0JZp4WwMIoY
i/DCCFZZa5VZ4UTfbEnhAKMZnU569z6WtjGg0STvqsA8n6CDTWs9YRfUYWtxVxgQ
xmpwOORysSCrroTWv5vVzj8Apydb8yvH9IKdxbEnCKNJ345N25s91z41gKo2m7zO
MVLytO3jc6hddwlBl/GIJivXOwONCfYrdI2bO3w4Wis1au99gvm3Vjs0XFRgeMYN
v4UfdaGRnb44wAbK4+UT3zQBSJ7iaAbPwvoiBxPOrHHUAYw+aCiBN9Dtkb7sN4md
A2+khLQXQwfESId+QstQ/Fwpcl/9HoEka142cFxNmzskZnogJozGvxkdqU7NjVT/
bWjCgcIMz/OjBr8J/NmQnDMYGh4slpndIle7Ja8vP7vhxktI+h3P8Hfa1iFD/9LJ
vlx8Njru66sDaXZwIC0Uz7wrXnIp3vHEiw8IuM7B+1SU4C1tXStt3otk1pMs7zg2
xlsapfEj9l4E857gy8vX8V/AV7ufwASTMQ==
-----END ENTITLEMENT DATA-----"""

EXPECTED_CERT_SIGNATURE_V3 = """-----BEGIN RSA SIGNATURE-----
cN+DtEyAEoB6VRj3JQUiF++Yn/jDEAXpEkU5jtILZmWVBCTm/IgBSoEh8+idrZSF
nkAyrw5JB7YbKwmcfhyDU4/tE/x4WLZhd7e4Fs3IndY/S/YzYL8mafOK2PbVGxeA
ZyAnDZPe/CYX/FzNEgk4z62EbvYAtMMx4I3aif5qce8=
-----END RSA SIGNATURE-----"""

EXPECTED_KEY_CONTENT_V3 = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAr4Orns+ermIi9FP6fK9Iy+HFPLOgFDrsOjcAobQu9GikourS
A2Oi64kJSstIYhXLbISdsz4c+dc2SH9Auw5zpBRwFJWWcVX9d3+xcH4a1ajLUbNy
Yw1RSg0Nt0hmOP46Z2bT/y56h8bVAM4fhFkdHbmWq4Oi+RlT9bNK/lcrKKo+oWIe
34PxAVFeIdvuLr7ItOEXic122ST3vJqLfEdGtFWpaGpHydggXt08exMHIxRJqhHP
mIo7muaD0EGtkTj6QNksUT7bzBHG3MP8OJ7YZ0nB7uZDmbQdQkL7WD2XI6u4DJQp
snGX3kfEY5sFBmZUx105mM0LXhYPC3iQt/+pcQIDAQABAoIBABHAG0dAcCfqvOZA
6ABcKdyUxMHS2Mmy+9kXXvT7qBQH0T64yOyW0w9HGK17yaJB2gTrlJdgHMYXweGr
HPzOBVv+xScPydtEexHu1B8wYb5iB84He/YQjrwSfeSfadcxvu5eM+qG5NV+gmRG
dGGKMauj7V0DPyQ6L4eVzmvSnQbLpYGmfB8wQFuNRFYCYZ90SyuBn2CcC20sAEYZ
p76q0qzfdrRjkg//saoh4sU38NgOY3tYSok/14SI+g9EkIHGNFV9/Rq3mvlLcwi/
m98Mg69Yt0SF6PNTPwF6ZgsH1yWpvK9laycbEYZ44g7nIQOewQ0aKVHfDQt52rrA
/P2rV1ECgYEA+TevV8QdJei5TFpF8ERvbrFJn64SmqD/u5Wamki0QEoZ+SkdioWj
1C6jolHj85yVgC5nKBIlNm8f5hqp4p4E0b7BwvH5QbDRg5VDQfV5MBk87LC4Rj7Q
WQNhcicWF5pdAdgrmy0uZ2q3J386DS9y2dCm3bItIueKC132H4KzpHMCgYEAtEp9
kAqzmG3QJ+aI37e3OeL2XzUNDP47RaZicH5n3mmIVbffkgYu+wHkv7zukl3kdpsx
TWTuffjtcueMXmdHsqOukB+XkvcBXsWfweJq66uoxeZhYUQr04NEvapcZ/6wud5t
ZvMF/ASLL1zXAZ8IT7Xaufzbld1UT4MItYwcZYsCgYA760yIMInFjI/IsMex/fJA
zfVipAqrDNyPsGeMgsB72JUoF9+XZ4w9Pr1vEHtbHiG/wOhidQJndQ5ZV73S06Va
/J8/jMgeKDInjeKu4CM0Ek1YpyCXGxEi5bIvLQCdyipkgCHz3EgU605/+5Hsi6T0
g7srAGTjyIGjPAMqDlW8ywKBgQCVowXYGam6J9qOY17TH+4pU2Dc4HE2iYO0aUZm
y+N1y+1mB7i9v/gaSRYMtcjlHpzSfDhNXio7z/F0Xw44BEyTzhrCcBYj2nL+r9PK
3huUAuOPbYkBa81cPiU9rjoH7nHLsvrmaWpcI4FKDCo/pDkHv44Ms/ukxRCG9eCy
ndmrxQKBgGJiXMZnKjK9AUUDvsFBSp8Otrf20BoeCiq+tZF95S5jR9/I8nv4NBYp
59zCR1DOxxbyAHbRCjqZxdpZVAqKBl1BP+cmw93sAwJ3v9m+V4wFHVUFLJGmkXXV
X2mYlgErL9vzxIQrwfL5JdEo9f+PQ0eVs/lh9MPY2TliwEyXDrVp
-----END RSA PRIVATE KEY-----"""

EXPECTED_CERT_V3 = create_from_pem(EXPECTED_CERT_CONTENT_V3 + os.linesep +
                                   EXPECTED_CERT_ENTITLEMENT_V3 +
                                   os.linesep + EXPECTED_CERT_SIGNATURE_V3)


class MergePoolsTests(SubManFixture):

    def test_single_pool(self):
        product = 'product1'
        pools = [
                create_pool(product, product, quantity=10, consumed=5)
        ]
        results = merge_pools(pools)
        self.assertEqual(1, len(list(results.values())))
        result = list(results.values())[0]
        self.assertEqual(product, result.product_id)

    def test_multiple_pools(self):
        product1 = 'product1'
        product2 = 'product2'
        pools = [
                create_pool(product1, product1, quantity=10, consumed=5),
                create_pool(product1, product1, quantity=55, consumed=20),
                create_pool(product2, product2, quantity=10, consumed=5),
        ]
        results = merge_pools(pools)
        self.assertEqual(2, len(list(results.values())))
        self.assertTrue(product1 in results)
        self.assertTrue(product2 in results)

        # Check product1:
        merged_pools = results[product1]
        self.assertEqual(product1, merged_pools.product_id)
        self.assertEqual(65, merged_pools.quantity)
        self.assertEqual(25, merged_pools.consumed)

        # Check product2:
        merged_pools = results[product2]
        self.assertEqual(product2, merged_pools.product_id)
        self.assertEqual(10, merged_pools.quantity)
        self.assertEqual(5, merged_pools.consumed)


class PoolFilterTests(SubManFixture):

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
        self.assertEqual(1, len(result))
        self.assertEqual(product2, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product2, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product1, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product1, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product1, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product1, result[0]['productId'])

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
        self.assertEqual(1, len(result))
        self.assertEqual(product1, result[0]['productId'])

    def test_filter_no_overlap(self):
        product1 = "Test Product 1"
        provided1 = "1"  # Provided by product 1

        pd = StubCertificateDirectory([])
        pool_filter = PoolFilter(product_dir=pd,
                entitlement_dir=StubCertificateDirectory([]),
                sorter=StubCertSorter())

        begin_date = datetime.now() - timedelta(days=10)
        end_date = datetime.now() + timedelta(days=365)
        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(begin_date, end_date)),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual(1, len(result))

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual(0, len(result))

    def test_filter_overlap(self):
        product1 = "Test Product 1"
        provided1 = "1"
        product2 = "Test Product 2"
        provided2 = "2"

        cert_start = datetime.now() - timedelta(days=10)
        cert_end = datetime.now() + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)

        ent_dir = StubCertificateDirectory([cert1])
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=StubCertSorter())

        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(cert_start, cert_end)),
                self._create_pool(product2, product2, provided_products=[provided2],
                            start_end_range=DateRange(cert_start, cert_end)),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual([pools[1]], result)

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual([pools[0]], result)

    def test_filter_overlap_sorter_without_partially_valid(self):
        product1 = "Test Product 1"
        provided1 = "1"

        cert_start = datetime.now() - timedelta(days=10)
        cert_end = datetime.now() + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)

        ent_dir = StubCertificateDirectory([cert1])
        mock_sorter = StubCertSorter()
        mock_sorter.partially_valid_products = {}
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)

        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(cert_start, cert_end)),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual(0, len(result))

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual([pools[0]], result)

    def test_filter_overlap_sorter_with_partially_valid(self):
        product1 = "Test Product 1"
        provided1 = "1"
        product2 = "Test Product 2"
        provided2 = "2"
        product3 = "Test Product 3"

        cert_start = datetime.now() - timedelta(days=10)
        cert_end = datetime.now() + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)
        cert2 = StubProductCertificate(StubProduct(provided2),
                                                   start_date=cert_start,
                                                   end_date=cert_end)

        ent_dir = StubCertificateDirectory([cert1, cert2])
        mock_sorter = StubCertSorter()
        mock_sorter.partially_valid_products = {cert1.products[0].id: set([cert1])}
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)

        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(cert_start, cert_end)),
                self._create_pool(product2, product2, provided_products=[provided2, provided1],
                            start_end_range=DateRange(cert_start, cert_end)),
                self._create_pool(product3, product3, provided_products=[provided2],
                            start_end_range=DateRange(cert_start, cert_end)),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual([pools[0], pools[1]], result)

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual([pools[2]], result)

    def test_filter_no_overlap_with_future_entitlement(self):
        product1 = "Test Product 1"
        provided1 = "1"

        cert_start = datetime.now() + timedelta(days=365)
        cert_end = cert_start + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)

        ent_dir = StubCertificateDirectory([cert1])
        mock_sorter = StubCertSorter()
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)

        begin_date = datetime.now() - timedelta(days=100)
        end_date = datetime.now() + timedelta(days=100)
        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(begin_date, end_date)),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual(1, len(result))

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual(0, len(result))

    def test_filter_no_overlap_with_partial_stack(self):
        product1 = "Test Product 1"
        provided1 = "1"
        stacking_id1 = "123"

        ent_dir = StubCertificateDirectory()
        mock_sorter = StubCertSorter()
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)

        begin_date = datetime.now() - timedelta(days=100)
        end_date = datetime.now() + timedelta(days=100)
        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(begin_date, end_date),
                            stacking_id=stacking_id1),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual([pools[0]], result)

    def test_filter_overlap_with_partial_stack(self):
        product1 = "Test Product 1"
        provided1 = "1"
        stacking_id1 = "123"

        cert_start = datetime.now() - timedelta(days=10)
        cert_end = datetime.now() + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)
        ent_dir = StubCertificateDirectory([cert1])
        mock_sorter = StubCertSorter()
        mock_sorter.partial_stacks = {stacking_id1: [cert1]}
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)
        begin_date = datetime.now() - timedelta(days=100)
        end_date = datetime.now() + timedelta(days=100)
        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(begin_date, end_date),
                            stacking_id=stacking_id1),
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(begin_date, end_date),
                            stacking_id=stacking_id1),
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual(2, len(result))

    def test_filter_no_overlap_with_product_id(self):
        product1 = "Test Product 1"
        provided1 = "1"
        product2 = "0"  # different product id than that of product 1
        provided2 = "1"  # same provided product as product 1
        product2_type = 'SVC'

        cert_start = datetime.now() - timedelta(days=10)
        cert_end = datetime.now() + timedelta(days=365)
        cert1 = StubProductCertificate(StubProduct(provided1),
                                                   start_date=cert_start,
                                                   end_date=cert_end)

        ent_dir = StubCertificateDirectory([cert1])
        mock_sorter = StubCertSorter()
        mock_sorter.partially_valid_products = {}
        pool_filter = PoolFilter(product_dir=StubCertificateDirectory([]),
                entitlement_dir=ent_dir,
                sorter=mock_sorter)

        pools = [
                self._create_pool(product1, product1, provided_products=[provided1],
                            start_end_range=DateRange(cert_start, cert_end)),
                self._create_pool(product2, product2, provided_products=[provided2],
                            start_end_range=DateRange(cert_start, cert_end),
                            type=product2_type)
        ]
        result = pool_filter.filter_out_overlapping(pools)
        self.assertEqual([pools[1]], result)

        result = pool_filter.filter_out_non_overlapping(pools)
        self.assertEqual([pools[0]], result)

        # Adds in a stacking_id to be used in testing the partial stacks
        # Assume default type attribute of 'MKT'
    def _create_pool(self,
                     product_id,
                     product_name,
                     provided_products,
                     start_end_range,
                     stacking_id=None,
                     type='MKT'):
        prod_attrs = []
        if stacking_id:
            stacking_id_attribute = {
                "name": "stacking_id",
                "value": stacking_id
            }
            prod_attrs.append(stacking_id_attribute)
        if type:
            type_attribute = {
                "name": "type",
                "value": type
            }
            prod_attrs.append(type_attribute)
        pool = create_pool(product_id, product_name,
                           provided_products=provided_products,
                           start_end_range=start_end_range,
                           productAttributes=prod_attrs)
        return pool


class MockLog(object):
    def info(self):
        pass


def MockSystemLog(self, message, priority):
    pass


EXPECTED_CONTENT = EXPECTED_CERT_CONTENT + os.linesep + EXPECTED_KEY_CONTENT
EXPECTED_CERT_CONTENT_V3 = EXPECTED_CERT_CONTENT_V3 + os.linesep + \
                      EXPECTED_CERT_ENTITLEMENT_V3 + os.linesep + \
                      EXPECTED_CERT_SIGNATURE_V3
EXPECTED_CONTENT_V3 = EXPECTED_CERT_CONTENT_V3 + os.linesep + \
                      EXPECTED_KEY_CONTENT_V3


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
        self.assertTrue(extractor.contains_key_content())

    def test_contains_key_content_when_key_and_cert_exists_in_import_file_v3(self):
        extractor = ExtractorStub(EXPECTED_CONTENT_V3)
        self.assertTrue(extractor.contains_key_content())

    def test_does_not_contain_key_when_key_does_not_exist_in_import_file(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT)
        self.assertFalse(extractor.contains_key_content())

    def test_does_not_contain_key_when_key_does_not_exist_in_import_file_v3(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT_V3)
        self.assertFalse(extractor.contains_key_content())

    def test_get_key_content_when_key_exists(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEqual(EXPECTED_KEY_CONTENT, extractor.get_key_content())

    def test_get_key_content_when_key_exists_v3(self):
        extractor = ExtractorStub(EXPECTED_CONTENT_V3, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEqual(EXPECTED_KEY_CONTENT_V3, extractor.get_key_content())

    def test_get_key_content_returns_None_when_key_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_key_content())

    def test_get_key_content_returns_None_when_key_does_not_exist_v3(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT_V3, file_path="12345.pem")
        self.assertFalse(extractor.get_key_content())

    def test_get_cert_content(self):
        extractor = ExtractorStub(EXPECTED_CONTENT, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEqual(EXPECTED_CERT_CONTENT, extractor.get_cert_content())

    def test_get_cert_content_v3(self):
        extractor = ExtractorStub(EXPECTED_CONTENT_V3, file_path="12345.pem")
        self.assertTrue(extractor.contains_key_content())
        self.assertEqual(EXPECTED_CERT_CONTENT_V3, extractor.get_cert_content())

    def test_get_cert_content_returns_None_when_cert_does_not_exist(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.get_cert_content())

    def test_get_cert_content_returns_None_when_cert_does_not_exist_v3(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT_V3, file_path="12345.pem")
        self.assertFalse(extractor.get_cert_content())

    def test_verify_valid_entitlement_for_invalid_cert(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_invalid_cert_v3(self):
        extractor = ExtractorStub(EXPECTED_KEY_CONTENT_V3, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_invalid_cert_bundle(self):
        # Use a bundle of cert + key, but the cert is not an entitlement cert:
        extractor = ExtractorStub(IDENTITY_CERT_WITH_KEY,
                file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_key(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_key_v3(self):
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT_V3, file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_verify_valid_entitlement_for_no_cert_content(self):
        extractor = ExtractorStub("", file_path="12345.pem")
        self.assertFalse(extractor.verify_valid_entitlement())

    def test_write_cert_only(self):
        expected_cert_file = "%d.pem" % (EXPECTED_CERT.serial)
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT, file_path=expected_cert_file)
        extractor.write_to_disk()

        self.assertEqual(1, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEqual(EXPECTED_CERT_CONTENT, write_one[1])

    def test_write_cert_only_v3(self):
        expected_cert_file = "%d.pem" % (EXPECTED_CERT_V3.serial)
        extractor = ExtractorStub(EXPECTED_CERT_CONTENT_V3, file_path=expected_cert_file)
        extractor.write_to_disk()

        self.assertEqual(1, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEqual(EXPECTED_CERT_CONTENT_V3, write_one[1])

    def test_write_key_and_cert(self):
        filename = "%d.pem" % (EXPECTED_CERT.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_write_key_and_cert_v3(self):
        filename = "%d.pem" % (EXPECTED_CERT_V3.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename_v3(filename)

    def test_file_renamed_when_imported_with_serial_no_and_custom_extension(self):
        filename = "%d.cert" % (EXPECTED_CERT.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_serial_no_and_custom_extension_v3(self):
        filename = "%d.cert" % (EXPECTED_CERT_V3.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename_v3(filename)

    def test_file_renamed_when_imported_with_serial_no_and_no_extension(self):
        filename = str(EXPECTED_CERT.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_serial_no_and_no_extension_v3(self):
        filename = str(EXPECTED_CERT_V3.serial)
        self._assert_correct_cert_and_key_files_generated_with_filename_v3(filename)

    def test_file_renamed_when_imported_with_custom_name_and_pem_extension(self):
        filename = "entitlement.pem"
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_custom_name_and_pem_extension_v3(self):
        filename = "entitlement.pem"
        self._assert_correct_cert_and_key_files_generated_with_filename_v3(filename)

    def test_file_renamed_when_imported_with_custom_name_no_extension(self):
        filename = "entitlement"
        self._assert_correct_cert_and_key_files_generated_with_filename(filename)

    def test_file_renamed_when_imported_with_custom_name_no_extension_v3(self):
        filename = "entitlement"
        self._assert_correct_cert_and_key_files_generated_with_filename_v3(filename)

    def _assert_correct_cert_and_key_files_generated_with_filename(self, filename):
        expected_file_prefix = "%d" % (EXPECTED_CERT.serial)
        expected_cert_file = expected_file_prefix + ".pem"
        expected_key_file = expected_file_prefix + "-key.pem"

        extractor = ExtractorStub(EXPECTED_CONTENT, file_path=filename)
        extractor.write_to_disk()

        self.assertEqual(2, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEqual(EXPECTED_CERT_CONTENT, write_one[1])

        write_two = extractor.writes[1]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_key_file), write_two[0])
        self.assertEqual(EXPECTED_KEY_CONTENT, write_two[1])

    def _assert_correct_cert_and_key_files_generated_with_filename_v3(self, filename):
        expected_file_prefix = "%d" % (EXPECTED_CERT_V3.serial)
        expected_cert_file = expected_file_prefix + ".pem"
        expected_key_file = expected_file_prefix + "-key.pem"

        extractor = ExtractorStub(EXPECTED_CONTENT_V3, file_path=filename)
        extractor.write_to_disk()

        self.assertEqual(2, len(extractor.writes))

        write_one = extractor.writes[0]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_cert_file), write_one[0])
        self.assertEqual(EXPECTED_CERT_CONTENT_V3, write_one[1])

        write_two = extractor.writes[1]
        self.assertEqual(os.path.join(ENT_CONFIG_DIR, expected_key_file), write_two[0])
        self.assertEqual(EXPECTED_KEY_CONTENT_V3, write_two[1])


class TestMergedPoolsStackingGroupSorter(unittest.TestCase):

    def test_sorter_adds_group_for_non_stackable_entitlement(self):
        pool = self._create_pool("test-prod-1", "Test Prod 1")
        merged = merge_pools([pool])
        pools = list(merged.values())
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEqual(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEqual("", group.name)
        self.assertEqual(1, len(group.entitlements))
        self.assertEqual(pools[0], group.entitlements[0])

    def test_sorter_adds_group_for_stackable_entitlement(self):
        expected_stacking_id = 1234
        pool = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        merged = merge_pools([pool])
        pools = list(merged.values())
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEqual(1, len(sorter.groups))
        group = sorter.groups[0]
        self.assertEqual("Test Prod 1", group.name)
        self.assertEqual(1, len(group.entitlements))
        self.assertEqual(pools[0], group.entitlements[0])

    def test_sorter_adds_multiple_entitlements_to_group_when_same_stacking_id(self):
        expected_stacking_id = 1234
        pool1 = self._create_pool("test-prod-1", "Test Prod 1", expected_stacking_id)
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])

        pools = list(merged.values())
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEqual(1, len(sorter.groups))
        group = sorter.groups[0]

        self.assertIn(group.name, ["Test Prod 1", "Test Prod 2"])
        self.assertEqual(2, len(group.entitlements))

        self.assertEqual(pools[0], group.entitlements[0])
        self.assertEqual(pools[1], group.entitlements[1])

    def test_sorter_adds_multiple_groups_for_non_stacking_entitlements(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")
        pool2 = self._create_pool("test-prod-2", "Test Prod 2")

        merged = merge_pools([pool1, pool2])
        pools = list(merged.values())
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEqual(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEqual("", group1.name)
        self.assertEqual(1, len(group1.entitlements))
        self.assertEqual(pools[0], group1.entitlements[0])

        self.assertEqual("", group2.name)
        self.assertEqual(1, len(group2.entitlements))
        self.assertEqual(pools[1], group2.entitlements[0])

    def test_stacking_and_non_stacking_groups_created(self):
        pool1 = self._create_pool("test-prod-1", "Test Prod 1")

        expected_stacking_id = 1234
        pool2 = self._create_pool("test-prod-2", "Test Prod 2", expected_stacking_id)

        merged = merge_pools([pool1, pool2])
        pools = list(merged.values())
        sorter = MergedPoolsStackingGroupSorter(pools)

        self.assertEqual(2, len(sorter.groups))
        group1 = sorter.groups[0]
        group2 = sorter.groups[1]

        self.assertEqual(set([group1.name, group2.name]), set(["", "Test Prod 2"]))
        self.assertEqual(1, len(group1.entitlements))
        self.assertEqual(pools[0], group1.entitlements[0])

        self.assertEqual(1, len(group2.entitlements))
        self.assertEqual(pools[1], group2.entitlements[0])

    def _create_pool(self, product_id, product_name, stacking_id=None):
        prod_attrs = []
        if stacking_id:
            stacking_id_attribute = {
                "name": "stacking_id",
                "value": stacking_id
            }
            prod_attrs.append(stacking_id_attribute)
        return create_pool(product_id, product_name, productAttributes=prod_attrs)


class MergedPoolsTests(unittest.TestCase):

    def test_sort_virt_to_top(self):
        # Fake some pool JSON with the bare minimum of data:
        pools = [
            {
                'id': 1,
                'attributes': [],
                'consumed': 0,
                'quantity': 10,
                'providedProducts': [],
            },
            {
                'id': 2,
                'attributes': [{'name': 'virt_only', 'value': 'true'}],
                'consumed': 0,
                'quantity': 10,
                'providedProducts': [],
            },
            {
                'id': 3,
                'attributes': [],
                'consumed': 0,
                'quantity': 10,
                'providedProducts': [],
            },
            {
                'id': 4,
                'attributes': [{'name': 'virt_only', 'value': 'true'}],
                'consumed': 0,
                'quantity': 10,
                'providedProducts': [],
            }]

        merged_pools = MergedPools('product', 'A Product')
        for p in pools:
            merged_pools.add_pool(p)

        merged_pools.sort_virt_to_top()
        # If we sort, the virt pools should become the first two in the list:
        self.assertEqual(merged_pools.pools[0]['attributes'][0]['value'],
                "true")
        self.assertEqual(merged_pools.pools[1]['attributes'][0]['value'],
                "true")
        self.assertFalse('virt_only' in merged_pools.pools[2]['attributes'])
        self.assertFalse('virt_only' in merged_pools.pools[3]['attributes'])


class PoolStashTest(SubManFixture):

    def test_empty_stash_zero_length(self):
        my_stash = PoolStash()
        self.assertTrue(my_stash.all_pools_size() == 0)


class TestAllowsMutliEntitlement(unittest.TestCase):

    def test_allows_when_yes(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("yes")
        self.assertTrue(allows_multi_entitlement(pool))

    def test_allows_when_1(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("1")
        self.assertTrue(allows_multi_entitlement(pool))

    def test_does_not_allow_when_no(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("no")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_0(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("0")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_not_set(self):
        pool = {"productAttributes": []}
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_empty_string(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_does_not_allow_when_any_other_value(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("not_a_good_value")
        self.assertFalse(allows_multi_entitlement(pool))

    def test_is_case_insensitive(self):
        pool = self._create_pool_data_with_multi_entitlement_attribute("YeS")
        self.assertTrue(allows_multi_entitlement(pool))

        pool = self._create_pool_data_with_multi_entitlement_attribute("nO")
        self.assertFalse(allows_multi_entitlement(pool))

    def _create_pool_data_with_multi_entitlement_attribute(self, value):
        return {"productAttributes": [{"name": "multi-entitlement", "value": value}]}


class TestValidQuantity(unittest.TestCase):
    def test_nonetype_not_valid(self):
        self.assertFalse(valid_quantity(None))

    def test_neg_quantity_value_is_invalid(self):
        self.assertFalse(valid_quantity(-1))

    def test_positive_quantity_value_is_valid(self):
        self.assertTrue(valid_quantity(3))

    def test_string_quantity_not_valid(self):
        self.assertFalse(valid_quantity("12dfg2"))


class TestGetAvailableEntitlements(SubManFixture):

    def setUp(self):
        self.p1 = patch('subscription_manager.facts.Facts.write_cache')
        self.p1.start()
        super(TestGetAvailableEntitlements, self).setUp()

    def tearDown(self):
        self.p1.stop()
        super(TestGetAvailableEntitlements, self).tearDown()

    def test_no_pools(self):
        # get the injected stub uep
        cp = self.get_consumer_cp()
        cp.getPoolsList = Mock(return_value=[])
        res = managerlib.get_available_entitlements()
        self.assertEqual(0, len(res))

    def test_incompatible(self):
        cp = self.get_consumer_cp()

        # patch the mock for getPoolsList
        def get_pools_list(consumer=None, listAll=False, active_on=None, owner=None, filter_string=None,
                           after_date=None, future=None):
            if listAll:
                return [self.build_pool_dict('1234'),
                        self.build_pool_dict('4321')]
            else:
                return [self.build_pool_dict('1234')]

        cp.getPoolsList = Mock(side_effect=get_pools_list)

        res = managerlib.get_available_entitlements(get_all=True)
        self.assertEqual(2, len(res))

        res = managerlib.get_available_entitlements(get_all=False)
        self.assertEqual(1, len(res))

    def test_installed(self):
        cp = self.get_consumer_cp()

        def get_pools_list(consumer=None, listAll=False, active_on=None, owner=None, filter_string=None,
                           after_date=None, future=None):
            if listAll:
                return [self.build_pool_dict('1234', ['some_product']),
                        self.build_pool_dict('4321'),
                        self.build_pool_dict('12321', ['some_product'])]
            else:
                return [self.build_pool_dict('1234', ['some_product'])]

        cp.getPoolsList = Mock(side_effect=get_pools_list)

        product_directory = StubProductDirectory(pids=['some_product'])
        provide(PROD_DIR, product_directory)

        res = managerlib.get_available_entitlements(get_all=True, uninstalled=True)
        self.assertEqual(2, len(res))

        res = managerlib.get_available_entitlements(uninstalled=True)
        self.assertEqual(1, len(res))

    def build_pool_dict(self, pool_id, provided_products=[]):
        return {'id': str(pool_id),
            # note things fail if any of these are not set, or
            # incorrect types
            'quantity': 5,
            'consumed': 1,
            'productId': '',
            'startDate': datetime.now(GMT()).isoformat(),
            'endDate': datetime.now(GMT()).isoformat(),
            'providedProducts': [{'productId': prod_id} for prod_id in provided_products],
            'productAttributes': [{'name': 'foo',
                'value': 'blip'}]
            }
