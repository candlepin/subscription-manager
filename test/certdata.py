from __future__ import print_function, division, absolute_import

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

# A product cert from Candlepin's test data (product ID 100000000000002):
PRODUCT_CERT_V1_0 = """
-----BEGIN CERTIFICATE-----
MIIDeDCCAuGgAwIBAgIECgf/jTANBgkqhkiG9w0BAQUFADAzMRIwEAYDVQQDDAls
b2NhbGhvc3QxCzAJBgNVBAYTAlVTMRAwDgYDVQQHDAdSYWxlaWdoMB4XDTExMDgy
MzE3NDEzOVoXDTIxMDgyMzE3NDEzOVowGjEYMBYGA1UEAxMPMTAwMDAwMDAwMDAw
MDAyMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkbvsjJXu+vRzbBa+
G9S77gbQTtSbZXWncykJkinwqQkUl2jEnGN+BBYa30dfLFatkA6UP4XICIu+xVMw
qXc2O82BBubYvBTcqJy62U1YQnJFz/upSF0b9mKhcwJv2sAqMfkviGTYpjuCTfw6
VVSFUvIj+K16vRzZWgn+qTIUIt8yXipuz7E/4t+R2BG/9GCqjQq7LQb4y0FmWdGT
OehTjEY+G4+evsjyom5hXLgXlMhd3vkb7gHOyc3Yuk9h9eqGKg0oCiaF88KafMcu
hCp0mIC7W97jE2tHTWzfERw99j+uPjccBUljqVpNfW6S/iKDx0tkzv0pOnSxYYmd
HF5rbQIDAQABo4IBLDCCASgwEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIE
sDBjBgNVHSMEXDBagBQckL9Tc4HS6Df/ppG4uN7zSUsnD6E3pDUwMzESMBAGA1UE
AwwJbG9jYWxob3N0MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAPrR
0C/V93lLMB0GA1UdDgQWBBQPunbOh02rAFia+TmNDHCa05vI/DATBgNVHSUEDDAK
BggrBgEFBQcDAjAxBhErBgEEAZIICQGW3rGD6YACAQQcDBpBd2Vzb21lIE9TIGZv
ciB4ODZfNjQgQml0czAdBhErBgEEAZIICQGW3rGD6YACAwQIDAZ4ODZfNjQwGwYR
KwYBBAGSCAkBlt6xg+mAAgIEBgwEMy4xMTANBgkqhkiG9w0BAQUFAAOBgQARCW1E
d/w1WYaQElsYAN9/EyDXyXq4GJfTFES8eg09nUKYrMACds2wdh8m8vV7NtHl8E0y
wE//vrTlHGSD5m4/mcXsgpkHvbj/kOTP7aag7RPa51M8ocjtOplugUyIF0PsXO4B
SOxSnd1U0dX6pzEwMaJD9lCW8xZ2jsmdLUtLzQ==
-----END CERTIFICATE-----
"""

# FIXME: remove
# A product cert from Candlepin's test data (product 37060, Awesome
# OS server bits", this one with the "brand_type" oid added.
PRODUCT_CERT_WITH_OS_NAME_V1_0 = """
-----BEGIN CERTIFICATE-----
MIIDejCCAuOgAwIBAgIEAuhqBjANBgkqhkiG9w0BAQUFADBDMSIwIAYDVQQDDBlk
aGNwMjMxLTI4LnJkdS5yZWRoYXQuY29tMQswCQYDVQQGEwJVUzEQMA4GA1UEBwwH
UmFsZWlnaDAeFw0xMjA0MDIxODQ5NTlaFw0yMjA0MDIxODQ5NTlaMBAxDjAMBgNV
BAMTBTM3MDYwMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAjwldtpsx
qrXrob1CTPL5Wp3gY0mLsNqOCtd+PSUXLxTqgosktnp5Y6qIzllC4JnZDyjECKto
6Lt9JIaSKTq7ku5eBVg1WQ85skt37nriNc8ChjB2yA39szd7UtPB35Kmn+ItQP8a
pcaCQcUPLgNxa23n4YoEiUQOMnh94GAprhBBhuEwFKehKiI9H9FxvqrWRGCqLBBJ
zflJTo4dX5qf0qX9X23Ukb3PtVcsa8Y4vfhUloJvvzo62bcv64bNbXsLUXMvdWy1
px98SUwuFLot3MSZ4g4axEeTbtGDPUVqr1GxE+NN/7/qug4U/drgDsSagb9LUGcT
1H24cs42vJBEcwIDAQABo4IBKDCCASQwEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1Ud
DwQEAwIEsDBzBgNVHSMEbDBqgBRO8xc0xHgseEqLc1Hzn2fDN/74saFHpEUwQzEi
MCAGA1UEAwwZZGhjcDIzMS0yOC5yZHUucmVkaGF0LmNvbTELMAkGA1UEBhMCVVMx
EDAOBgNVBAcMB1JhbGVpZ2iCCQC/s2gOKUGq5DAdBgNVHQ4EFgQUw/jCiPX1vUBM
k24ZzCywPw3yjUwwEwYDVR0lBAwwCgYIKwYBBQUHAwIwKQYNKwYBBAGSCAkBgqFE
AQQYDBZBd2Vzb21lIE9TIFNlcnZlciBCaXRzMBYGDSsGAQQBkggJAYKhRAMEBQwD
QUxMMBYGDSsGAQQBkggJAYKhRAIEBQwDNi4xMA0GCSqGSIb3DQEBBQUAA4GBAF6t
KC2GWH+HzIQlapw7f+TkZbWhYeDqHDL2LJkFPcTt2KDRV86okdeIRHa1bHZSqDnY
3VP4xOrhpfXDtLULsox7dm/BCdXyvK16MwaYGxFjsWOTnDQk3MhEugXomch5DrjU
O04owaV6c4MmAy1odMk8E3bZRqPtAO1qxwTPRY7P
-----END CERTIFICATE-----
"""

# Test entitlement to the product cert above:
ENTITLEMENT_CERT_V1_0 = """
-----BEGIN CERTIFICATE-----
MIIMmjCCDAOgAwIBAgIIANVjq5EWLIIwDQYJKoZIhvcNAQEFBQAwMTEQMA4GA1UE
AwwHYm9vZ2FkeTELMAkGA1UEBhMCVVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcNMTIw
OTA3MDAwMDAwWhcNMTMwOTA3MDAwMDAwWjArMSkwJwYDVQQDEyBmZjgwODA4MTM5
YWZmYmI1MDEzOWI1ODQxODA5NzA2ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCC
AQoCggEBAKXbLDYZOC6pmP/ykUkxQ5C+kvRjQDJpH2pDiAA4QvQtaobZlWf9nA8W
s5AItzIktMBHIrtWghvyM7jDu0xfCx1W+559gb4gO0R7JiHzZYfRMh2FTj9kSzCa
DamkH80WGLVj7W84TKTE82cc8a6orPeMDRTx7qk9MD0rpBNk25iNSGx5Z6DeIwwW
hdi2D2kjLqqmnjAl2KP9W1WwCknQCszbdVzVGN9GLLDDmzDbpMuTheKlRo18jJp6
P3hwZjzsIh6zDkvFZF72go3gIEDltgnvJcZYY4Ez8yDmCeONkhBdmdlgSr9XK4kH
BTccMzbaOUmxPe5RpeuV3AXEsmnV8hECAwEAAaOCCjswggo3MBEGCWCGSAGG+EIB
AQQEAwIFoDALBgNVHQ8EBAMCBLAwYQYDVR0jBFowWIAUJA/StfVIqP9zL2BSfNJm
y2mpkMmhNaQzMDExEDAOBgNVBAMMB2Jvb2dhZHkxCzAJBgNVBAYTAlVTMRAwDgYD
VQQHDAdSYWxlaWdoggkAgMyWN5DyzrEwHQYDVR0OBBYEFJRLNqSw9VMXi64pozr/
JYvuLj8yMBMGA1UdJQQMMAoGCCsGAQUFBwMCMCIGDSsGAQQBkggJAYKhSQEEEQwP
Q2x1c3RlcmluZyBCaXRzMBYGDSsGAQQBkggJAYKhSQMEBQwDQUxMMBYGDSsGAQQB
kggJAYKhSQIEBQwDMS4wMCkGDSsGAQQBkggJAYKhRAEEGAwWQXdlc29tZSBPUyBT
ZXJ2ZXIgQml0czAWBg0rBgEEAZIICQGCoUQDBAUMA0FMTDAWBg0rBgEEAZIICQGC
oUQCBAUMAzYuMTAVBgwrBgEEAZIICQKBawEEBQwDeXVtMCMGDSsGAQQBkggJAoFr
AQEEEgwQY29udGVudC1lbXB0eWdwZzAqBg0rBgEEAZIICQKBawECBBkMF2NvbnRl
bnQtbGFiZWwtZW1wdHktZ3BnMB4GDSsGAQQBkggJAoFrAQUEDQwLdGVzdC12ZW5k
b3IwHAYNKwYBBAGSCAkCgWsBBgQLDAkvZm9vL3BhdGgwEwYNKwYBBAGSCAkCgWsB
BwQCDAAwFAYNKwYBBAGSCAkCgWsBCAQDDAExMBQGDSsGAQQBkggJAoFrAQkEAwwB
MDAUBgsrBgEEAZIICQIBAQQFDAN5dW0wKAYMKwYBBAGSCAkCAQEBBBgMFmFsd2F5
cy1lbmFibGVkLWNvbnRlbnQwKAYMKwYBBAGSCAkCAQECBBgMFmFsd2F5cy1lbmFi
bGVkLWNvbnRlbnQwHQYMKwYBBAGSCAkCAQEFBA0MC3Rlc3QtdmVuZG9yMC4GDCsG
AQQBkggJAgEBBgQeDBwvZm9vL3BhdGgvYWx3YXlzLyRyZWxlYXNldmVyMCYGDCsG
AQQBkggJAgEBBwQWDBQvZm9vL3BhdGgvYWx3YXlzL2dwZzATBgwrBgEEAZIICQIB
AQgEAwwBMTAVBgwrBgEEAZIICQIBAQkEBQwDMjAwMBQGCysGAQQBkggJAgABBAUM
A3l1bTAnBgwrBgEEAZIICQIAAQEEFwwVbmV2ZXItZW5hYmxlZC1jb250ZW50MCcG
DCsGAQQBkggJAgABAgQXDBVuZXZlci1lbmFibGVkLWNvbnRlbnQwHQYMKwYBBAGS
CAkCAAEFBA0MC3Rlc3QtdmVuZG9yMCEGDCsGAQQBkggJAgABBgQRDA8vZm9vL3Bh
dGgvbmV2ZXIwJQYMKwYBBAGSCAkCAAEHBBUMEy9mb28vcGF0aC9uZXZlci9ncGcw
EwYMKwYBBAGSCAkCAAEIBAMMATAwFQYMKwYBBAGSCAkCAAEJBAUMAzYwMDAVBgwr
BgEEAZIICQKBagEEBQwDeXVtMCAGDSsGAQQBkggJAoFqAQEEDwwNY29udGVudC1u
b2dwZzAnBg0rBgEEAZIICQKBagECBBYMFGNvbnRlbnQtbGFiZWwtbm8tZ3BnMB4G
DSsGAQQBkggJAoFqAQUEDQwLdGVzdC12ZW5kb3IwHAYNKwYBBAGSCAkCgWoBBgQL
DAkvZm9vL3BhdGgwEwYNKwYBBAGSCAkCgWoBBwQCDAAwFAYNKwYBBAGSCAkCgWoB
CAQDDAExMBQGDSsGAQQBkggJAoFqAQkEAwwBMDAUBgsrBgEEAZIICQICAQQFDAN5
dW0wIAYMKwYBBAGSCAkCAgEBBBAMDnRhZ2dlZC1jb250ZW50MCAGDCsGAQQBkggJ
AgIBAgQQDA50YWdnZWQtY29udGVudDAdBgwrBgEEAZIICQICAQUEDQwLdGVzdC12
ZW5kb3IwIgYMKwYBBAGSCAkCAgEGBBIMEC9mb28vcGF0aC9hbHdheXMwJgYMKwYB
BAGSCAkCAgEHBBYMFC9mb28vcGF0aC9hbHdheXMvZ3BnMBMGDCsGAQQBkggJAgIB
CAQDDAExMBsGDCsGAQQBkggJAgIBCgQLDAlUQUcxLFRBRzIwFQYMKwYBBAGSCAkC
iFcBBAUMA3l1bTAaBg0rBgEEAZIICQKIVwEBBAkMB2NvbnRlbnQwIAYNKwYBBAGS
CAkCiFcBAgQPDA1jb250ZW50LWxhYmVsMB4GDSsGAQQBkggJAohXAQUEDQwLdGVz
dC12ZW5kb3IwHAYNKwYBBAGSCAkCiFcBBgQLDAkvZm9vL3BhdGgwIQYNKwYBBAGS
CAkCiFcBBwQQDA4vZm9vL3BhdGgvZ3BnLzAUBg0rBgEEAZIICQKIVwEIBAMMATEw
FAYNKwYBBAGSCAkCiFcBCQQDDAEwMCYGDSsGAQQBkggJAYKhTgEEFQwTTG9hZCBC
YWxhbmNpbmcgQml0czAWBg0rBgEEAZIICQGCoU4DBAUMA0FMTDAWBg0rBgEEAZII
CQGCoU4CBAUMAzEuMDAqBg0rBgEEAZIICQGCoUwBBBkMF0xhcmdlIEZpbGUgU3Vw
cG9ydCBCaXRzMBYGDSsGAQQBkggJAYKhTAMEBQwDQUxMMBYGDSsGAQQBkggJAYKh
TAIEBQwDMS4wMCYGDSsGAQQBkggJAYKhSwEEFQwTU2hhcmVkIFN0b3JhZ2UgQml0
czAWBg0rBgEEAZIICQGCoUsDBAUMA0FMTDAWBg0rBgEEAZIICQGCoUsCBAUMAzEu
MDAiBg0rBgEEAZIICQGCoU0BBBEMD01hbmFnZW1lbnQgQml0czAWBg0rBgEEAZII
CQGCoU0DBAUMA0FMTDAWBg0rBgEEAZIICQGCoU0CBAUMAzEuMDApBgorBgEEAZII
CQQBBBsMGUF3ZXNvbWUgT1MgU2VydmVyIEJ1bmRsZWQwMAYKKwYBBAGSCAkEAgQi
DCBmZjgwODA4MTM5YTBhNzE2MDEzOWEwYTg1MDFkMDI5NTAgBgorBgEEAZIICQQD
BBIMEGF3ZXNvbWVvcy1zZXJ2ZXIwEgYKKwYBBAGSCAkEBQQEDAIxMDARBgorBgEE
AZIICQQJBAMMATIwJAYKKwYBBAGSCAkEBgQWDBQyMDEyLTA5LTA3VDAwOjAwOjAw
WjAkBgorBgEEAZIICQQHBBYMFDIwMTMtMDktMDdUMDA6MDA6MDBaMBIGCisGAQQB
kggJBAwEBAwCMzAwEwYKKwYBBAGSCAkECgQFDAMzNTkwGwYKKwYBBAGSCAkEDQQN
DAsxMjMzMTEzMTIzMTARBgorBgEEAZIICQQOBAMMATEwFwYKKwYBBAGSCAkEDwQJ
DAdQcmVtaXVtMBcGCisGAQQBkggJBBAECQwHTGV2ZWwgMzARBgorBgEEAZIICQQL
BAMMATEwNAYKKwYBBAGSCAkFAQQmDCQwYmU4Yjc0Yi04Yzg5LTRmY2ItODU1Ny1l
MTBlNTE5YjljZTIwDQYJKoZIhvcNAQEFBQADgYEAqVd+8OitI2uoziO5QK9Nv797
ZHPTHIdt9pJWZN+6oik/Obz1YZFps8A+BEun//Ep7ic2Y/uGkFPAfst2XUzsppn6
xcZMWDJqsZUlxzf6asoTFFNWnKXUv0bbgalHSASEx7mEqTuo58upHJbEuDtz2o+6
Z9DOOKAxJ8/KPAjBmSA=
-----END CERTIFICATE-----
"""


ENTITLEMENT_CERT_V3_0 = """
-----BEGIN CERTIFICATE-----
MIIDjzCCAvigAwIBAgIIEiB+vHfSYuwwDQYJKoZIhvcNAQEFBQAwMDEPMA0GA1UE
AwwGcGlwYm95MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAeFw0xMjA5
MTgwMDAwMDBaFw0xMzA5MTgwMDAwMDBaMCsxKTAnBgNVBAMTIGZmODA4MDgxMzlk
OWUyNmMwMTM5ZGEyMzQ4OWEwMDY2MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAgDfkG4OZAfxAGKPjNrhrqBJbGbB0r7CmFRnFPcnwdQQVxx6gxyH5ia5/
VoNmQRsFlWJJsl2W64IJq8xe2PeF8nhqOh3bg8Q5lPkSqHHb/9G370quRj0Ig+FX
up3eDUfiF+BpKkTHlelpPOhG6aeZzvwuLcF9+5SSqJTtuyMv759Kneybijm/Gv7x
t8EZkaUydoZhjgkN7fQAhAEW9L6y0+fudL4nBXnm7CW7k3/JSA7V73Ae1u6L/3+k
W+FDGGqKa0NR+sYOroCarMsqVd29uRabSO4rxzmYZ5W0RE0f1cUfYFM0aDwaU1+l
bVnNelesXnhjJ219BWcVdZhS+X84VwIDAQABo4IBMTCCAS0wEQYJYIZIAYb4QgEB
BAQDAgWgMAsGA1UdDwQEAwIEsDBgBgNVHSMEWTBXgBThiP6NmxGeYgJ5XWPC2dy0
EoDcVKE0pDIwMDEPMA0GA1UEAwwGcGlwYm95MQswCQYDVQQGEwJVUzEQMA4GA1UE
BwwHUmFsZWlnaIIJAN6RU5TAoOZ5MB0GA1UdDgQWBBTqqQFQLeZGIrYGXQSYxfw8
zNaXqzATBgNVHSUEDDAKBggrBgEFBQcDAjASBgkrBgEEAZIICQYEBQwDMy4wMGEG
CSsGAQQBkggJBwRUBFJ42hXKwQmAMBAEwC0mJUiwG1llJY/ohbtgtHv1O8w95yVP
6IZTlxy7GVgHn0BaGaJvBY29ILmqPvkXh8IOWeAFpiEVtwrrTkxmoYKDgtHpgfcA
MA0GCSqGSIb3DQEBBQUAA4GBAF0jikJbd1C0PqhpRkmRGaNnAPO4kCSH+nTee1UF
xSYERpmDHnimDWYjcs35gb1wWwSOLVsTn4X+3TQqMQ1rdnEX5mn7iutqCjj5Rjzk
icfe5PF7mmnMv6FeKlFEg3WGkIkatI1tF13spHowM8GFZvAcMGVzFkvL6QtzyNKa
t6+/
-----END CERTIFICATE-----
-----BEGIN ENTITLEMENT DATA-----
eJydUl1vmzAU/SvI6iMMG1NCeNue9jZp29OmKvIXKQrYzDZNo6j/fdeQ0kT5aFU+
hM25595z7vUeCaPd0CmLKsSZpJLldUJzLpOcLklS3tc8KReiXt4XC8o5RTH6NzDt
G79DVRYjN3AnbNP7xmhU7ZHbDJCJbZUznTIueS6LVZEDS7NOAfJ1QqIfv6La2GiG
t8zqRq9RRTEkNWKjvEMVgbVnYgPIqpFAJ+glRsbKoHeP9NDxUXldlxhuQpdymfMc
42klMCnhHQu8qSZ4zGo9EDNMsgQvE1L+xrganz8QrLScQHoBhI55y0SgFwvYMyHM
oMOWZJQSQuEz6uytkYMIPv7u0SQfH1/ZO22JvjVAjtGTsm5sL6JfCAkVrXhsvBJ+
sCpkR4c2PkziVBAzl4R4v+tDkd3QvVVk7ZbtXKI0462SySsvRi3jqr0V8ATdMaHr
XjmfHHbglvlH+JnWxqRhnU4J0jurWsWcAhcQte7Xq8G2lwIBgoBOeSaZZyv13DcW
lGYYv8SvZgjJ8muGzs/cbOUcmk38VDL6zvyRgVGTN+nMSmfWoRmoqlnr1ImbcxaA
6SVDtDhyhK+40aFfN6ZzDf/ocPRhHjccncZeG09xOh5C3xvPpbl8bCB3HI5ROPvH
Zyo9TvL5eTzA/R9AE5nG
-----END ENTITLEMENT DATA-----
-----BEGIN RSA SIGNATURE-----
FWYaGqnaDRpuaKLEXu9RtxNLbp3q7BM651s1P1jwlE/Ff1GMZrzsreBfRa4FE6ST
jdWIkOEVpZPEHtdnHlpQaphYDOQBfdSGrOb2ksKqfp0qKrqT4dvzau5IzqtVmkTJ
SgW0kgf/C5sFxdgD6s9NKmP/u6OgI/qqE+KfnCex/ko=
-----END RSA SIGNATURE-----
"""

ENTITLEMENT_CERT_V3_0_NO_CONTENT= """
-----BEGIN CERTIFICATE-----
MIIDejCCAuOgAwIBAgIIY4bpXjAB064wDQYJKoZIhvcNAQEFBQAwPDEbMBkGA1UE
AwwSY2FuZGxlLmxvY2FsZG9tYWluMQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFs
ZWlnaDAeFw0xODExMTkwMDAwMDBaFw0xOTExMTkwMDAwMDBaMDsxDjAMBgNVBAoT
BWFkbWluMSkwJwYDVQQDEyA0MDI4ZmE3YTY3MmMwMWUxMDE2NzJjMjBkMWQxMDli
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAIasgH1wyYDhvtWG7zcu
fR2R7JyqTOHgv/gOxK2vWSaGaU92aaNN+4Ukip9zBoMSXeqQLdLIGKLPJrMIZO3y
35MHtI/KgvWoLLGaHTjuuu+/1w59LTNv12+6Q9b+cMUNZwHINfcE1YLtpxbWbxrn
/yBZqOSNqjhhxUxXpKY6uZm51Ymztl90bujCzNaDNKU3mli8uX6/GoRyda5e+/8j
ey5BxRyPoUGctO3Eha5G2AgzlO1S7psQLfikPOZWU9KCvWh6uy14VZgfNgLsZvRi
Qt3+l3L+M7xgejm8RgL6yp5bnO6bBh5XxAq63Gedf3NppNK4VpBilkttCckiYuGV
tZ8CAwEAAaOCAQAwgf0wEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDBs
BgNVHSMEZTBjgBR+GGFdclqCRTwQ5OylB26+7guhe6FApD4wPDEbMBkGA1UEAwwS
Y2FuZGxlLmxvY2FsZG9tYWluMQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWln
aIIJAIfmGC26Avq2MB0GA1UdDgQWBBQh4zE1pDNNBtb5SElgJmU2g8buTTATBgNV
HSUEDDAKBggrBgEFBQcDAjASBgkrBgEEAZIICQYEBQwDMy4zMBQGCSsGAQQBkggJ
CAQHDAVCYXNpYzAPBgkrBgEEAZIICQcEAgQAMA0GCSqGSIb3DQEBBQUAA4GBAJkP
hN0v/br7rMKg6EB2XBmMDOc0J7CTTtj1FKd2jXFFbYsb1K4hE0k92tSW92AfgsVL
OhcewkOoEuHMgiO7FizI4nu0W0WLDuuzgC2CMjfniSV93VjBwYjYuVwOGazcssl5
mWBrODrkVzB/wBbqRtoQ//PjaE07fCBszdxgCsyc
-----END CERTIFICATE-----
-----BEGIN ENTITLEMENT DATA-----
eJx1UE1r4zAQ/StmTi1URWPFjuVbe+mlC4HtqaUUWZZ3RfyRlUdhQ8h/35ECe2kL
BnnevPfmzZzBLvMaJxegBVVZjVpqUdWyEhtEKRqLg9CDLnWtdKcHhDv4E81Mnk7Q
Vnewxm61wR/ILzO0Z1j3kZ2CmUoxxZG8IQqsmc3kGP+RIPHAmO8iueInGbs33eiK
m7J4erxlJkuhLdnYhaO3LnmO7uhGVu+Cm3ycmESnQ7J7To1CwYXpycnPvz58z43/
o0XGBbmVEmsJfdr0DHOcurxzRkRTbysl9aflyARiUimxEYgC9YuUbf5emevm/trU
XzT5rhSMTXLJpbF2iXOqsFQKUfGDKdIhLH20tEL7doYcXkv5/cWe/eTJ9cXuKmPi
0YU1Hx/wPk8K9jdTLMXgkiv8beqPegPv10wuhXh7v3B5WJYxHSNP3ciyGczW1NvS
SnQoMf/Vg5KNVHYDl8s/gJaozA==
-----END ENTITLEMENT DATA-----
-----BEGIN RSA SIGNATURE-----
GgQryM9Caj38NNvVS/+wiAFzhxkBxtci+oNVkXG2HwUEuw8nVXRv/DpIHkfLTLm5
gRiWpxSH036c4bfOsXaBtYlvwh2UDBS3WDhh0e7st4IEt9Be70T7XAgLCXUAILMe
U2cdYX6mLGP/5bBrpCwjz/jECXuGp+pO2I+srx7bujQ=
-----END RSA SIGNATURE-----
"""


IDENTITY_CERT = """
-----BEGIN CERTIFICATE-----
MIIDdzCCAuCgAwIBAgIIBdnhr/WCKpMwDQYJKoZIhvcNAQEFBQAwTDErMCkGA1UE
Awwid3BvdGVhdC1kZXNrdG9wLnVzZXJzeXMucmVkaGF0LmNvbTELMAkGA1UEBhMC
VVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcNMTQwNTA4MTMwNDA0WhcNMzAwNTA4MTMw
NDA0WjAvMS0wKwYDVQQDEyQwZjVkNDYxNy1kOTEzLTRhMGYtYmU2MS1kOGE5Yzg4
ZTE0NzYwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCHsIAMwqDBji/k
SMy0BgkrWscYYwy/3vhaU8oEmhFBRMFwy8gzByKcKTTMB642cDhFa+anBbNm4+QS
OKpfKf8JDj8GKnBspQF3qWxxi1vJGo6iTD/znPQRAlB//furFNmEDaDbhMUtcHEK
UvjALioR5V3flfMU3hPCYdaAcVvYu8ikI6N52abPlFWCkzbp6EGehISyVZxrlqac
QOCIPmnUnMVZ1pxYjOTrEhqjvjHMlUuEAmeKlLXKtirgs+X2yfulMJFYXUDeeO20
AB9CRp/wg3zoGcSzwtriO8GuRSuAmXO0O4HzcpXU7oXJGYBjrTy/B8rukuZbep+t
Y3+FQmr1AgMBAAGjgfowgfcwEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIE
sDB8BgNVHSMEdTBzgBTPYX+LWg9Ed3S0lIZtc4PuYrbv5qFQpE4wTDErMCkGA1UE
Awwid3BvdGVhdC1kZXNrdG9wLnVzZXJzeXMucmVkaGF0LmNvbTELMAkGA1UEBhMC
VVMxEDAOBgNVBAcMB1JhbGVpZ2iCCQCQJzUqJvMgMjAdBgNVHQ4EFgQU4yyaMLWq
Mc3ch8CwTPRHZrhHFCQwEwYDVR0lBAwwCgYIKwYBBQUHAwIwIwYDVR0RBBwwGoYY
Q049cmVkaGF0LmxvY2FsLnJtLXJmLmNhMA0GCSqGSIb3DQEBBQUAA4GBAEso9d/F
xZsoPA4OgfEcTad/5CorTswNTqpmwlkQ6Yp61h8L7BDWJ6ywovqXJQqo6lYK3149
9+EC6nhTA9uhtODtQQgITkU6nwlYRkB0vrbofR7yO7eewlJ+ybhcVw1FllXfc4E9
7SS6c7YbmlfQhcoGyzfYXuJYGCyDmDHvcQiU
-----END CERTIFICATE-----
"""


# Cert contents
# NOTE: Must match the contents of the certs above.
# NOTE: Some editors will automatically replace tabs/spaces
#       and remove trailing whitespace. This will cause
#       test errors if this happens.

ENTITLEMENT_CERT_V1_0_OUTPUT = """
+-------------------------------------------+
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 1.0
\tSerial: 60063758564076674
\tStart Date: 2012-09-07 00:00:00+00:00
\tEnd Date: 2013-09-07 00:00:00+00:00
\tPool ID: Not Available

Subject:
\tCN: ff80808139affbb50139b5841809706e

Issuer:
\tC: US
\tCN: boogady
\tL: Raleigh

Product:
\tID: 37060
\tName: Awesome OS Server Bits
\tVersion: 6.1
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Product:
\tID: 37065
\tName: Clustering Bits
\tVersion: 1.0
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Product:
\tID: 37067
\tName: Shared Storage Bits
\tVersion: 1.0
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Product:
\tID: 37068
\tName: Large File Support Bits
\tVersion: 1.0
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Product:
\tID: 37069
\tName: Management Bits
\tVersion: 1.0
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Product:
\tID: 37070
\tName: Load Balancing Bits
\tVersion: 1.0
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Order:
\tName: Awesome OS Server Bundled
\tNumber: ff80808139a0a7160139a0a8501d0295
\tSKU: awesomeos-server
\tContract: 359
\tAccount: 12331131231
\tService Type: Level 3
\tRoles: 
\tService Level: Premium
\tUsage: 
\tAdd-ons: 
\tQuantity: 10
\tQuantity Used: 1
\tSocket Limit: 2
\tRAM Limit:%(space)s
\tCore Limit:%(space)s
\tVirt Only: False
\tStacking ID:%(space)s
\tWarning Period: 30
\tProvides Management: 1

Content:
\tType: yum
\tName: always-enabled-content
\tLabel: always-enabled-content
\tVendor: test-vendor
\tURL: /foo/path/always/$releasever
\tGPG: /foo/path/always/gpg
\tEnabled: True
\tExpires: 200
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: content
\tLabel: content-label
\tVendor: test-vendor
\tURL: /foo/path
\tGPG: /foo/path/gpg/
\tEnabled: True
\tExpires: 0
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: content-emptygpg
\tLabel: content-label-empty-gpg
\tVendor: test-vendor
\tURL: /foo/path
\tGPG:%(space)s
\tEnabled: True
\tExpires: 0
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: content-nogpg
\tLabel: content-label-no-gpg
\tVendor: test-vendor
\tURL: /foo/path
\tGPG:%(space)s
\tEnabled: True
\tExpires: 0
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: never-enabled-content
\tLabel: never-enabled-content
\tVendor: test-vendor
\tURL: /foo/path/never
\tGPG: /foo/path/never/gpg
\tEnabled: False
\tExpires: 600
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: tagged-content
\tLabel: tagged-content
\tVendor: test-vendor
\tURL: /foo/path/always
\tGPG: /foo/path/always/gpg
\tEnabled: True
\tExpires:%(space)s
\tRequired Tags: TAG1, TAG2
\tArches:%(space)s
""" % ({'space': ' '})

ENTITLEMENT_CERT_V3_0_OUTPUT = """
+-------------------------------------------+
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 3.0
\tSerial: 1306183239866671852
\tStart Date: 2012-09-18 00:00:00+00:00
\tEnd Date: 2013-09-18 00:00:00+00:00
\tPool ID: Not Available

Subject:
\tCN: ff80808139d9e26c0139da23489a0066

Issuer:
\tC: US
\tCN: pipboy
\tL: Raleigh

Product:
\tID: 100000000000002
\tName: Awesome OS for x86_64 Bits
\tVersion: 3.11
\tArch: x86_64
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Order:
\tName: Awesome OS for x86_64
\tNumber: ff80808139d94b400139d94c018c0164
\tSKU: awesomeos-x86_64
\tContract: 67
\tAccount: 12331131231
\tService Type:%(space)s
\tRoles: 
\tService Level:%(space)s
\tUsage: 
\tAdd-ons: 
\tQuantity: 10
\tQuantity Used: 2
\tSocket Limit: 1
\tRAM Limit:%(space)s
\tCore Limit:%(space)s
\tVirt Only: False
\tStacking ID: 1
\tWarning Period: 30
\tProvides Management: False

Authorized Content URLs:
\t/foo/path/always/$releasever
\t/foo/path/never
\t/path/to/$basearch/$releasever/awesomeos
\t/path/to/awesomeos/x86_64

Content:
\tType: yum
\tName: always-enabled-content
\tLabel: always-enabled-content
\tVendor: test-vendor
\tURL: /foo/path/always/$releasever
\tGPG: /foo/path/always/gpg
\tEnabled: True
\tExpires: 200
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: awesomeos
\tLabel: awesomeos
\tVendor: Red Hat
\tURL: /path/to/$basearch/$releasever/awesomeos
\tGPG: /path/to/awesomeos/gpg/
\tEnabled: True
\tExpires: 3600
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: awesomeos-x86_64
\tLabel: awesomeos-x86_64
\tVendor: Red Hat
\tURL: /path/to/awesomeos/x86_64
\tGPG: /path/to/awesomeos/gpg/
\tEnabled: False
\tExpires: 3600
\tRequired Tags:%(space)s
\tArches:%(space)s

Content:
\tType: yum
\tName: never-enabled-content
\tLabel: never-enabled-content
\tVendor: test-vendor
\tURL: /foo/path/never
\tGPG: /foo/path/never/gpg
\tEnabled: False
\tExpires: 600
\tRequired Tags:%(space)s
\tArches:%(space)s
""" % ({'space': ' '})


ENTITLEMENT_CERT_V3_0_NO_CONTENT_OUTPUT = """
+-------------------------------------------+
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 3.3
\tSerial: 7171676047375717294
\tStart Date: 2018-11-19 00:00:00+00:00
\tEnd Date: 2019-11-19 00:00:00+00:00
\tPool ID: 4028fa7a672c01e101672c06f30803c4

Subject:
\tCN: 4028fa7a672c01e101672c20d1d109be
\tO: admin

Issuer:
\tC: US
\tCN: candle.localdomain
\tL: Raleigh

Product:
\tID: 900
\tName: Multi-Attribute Limited Product
\tVersion: 1.0
\tArch: x86_64
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Order:
\tName: Multi-Attribute Stackable (2 GB)
\tNumber: order-8675309
\tSKU: ram2-multiattr
\tContract: 0
\tAccount: 12331131231
\tService Type: Level 3
\tRoles: 
\tService Level: Premium
\tUsage: 
\tAdd-ons: 
\tQuantity: 5
\tQuantity Used: 5
\tSocket Limit:%(space)s
\tRAM Limit: 2
\tCore Limit:%(space)s
\tVirt Only: False
\tStacking ID: multiattr-stack-test
\tWarning Period: 0
\tProvides Management: False

""" % ({'space': ' '})

PRODUCT_CERT_V1_0_OUTPUT = """
+-------------------------------------------+
\tProduct Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 1.0
\tSerial: 168296333
\tStart Date: 2011-08-23 17:41:39+00:00
\tEnd Date: 2021-08-23 17:41:39+00:00

Subject:
\tCN: 100000000000002

Issuer:
\tC: US
\tCN: localhost
\tL: Raleigh

Product:
\tID: 100000000000002
\tName: Awesome OS for x86_64 Bits
\tVersion: 3.11
\tArch: x86_64
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

""" % ({'space': ' '})


PRODUCT_CERT_WITH_OS_NAME_V1_0_OUTPUT = """
+-------------------------------------------+
\tProduct Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 1.0
\tSerial: 48785926
\tStart Date: 2012-04-02 18:49:59+00:00
\tEnd Date: 2022-04-02 18:49:59+00:00

Subject:
\tCN: 37060

Issuer:
\tC: US
\tCN: dhcp231-28.rdu.redhat.com
\tL: Raleigh

Product:
\tID: 37060
\tName: Awesome OS Server Bits
\tVersion: 6.1
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

""" % ({'space': ' '})

IDENTITY_CERT_OUTPUT = """
+-------------------------------------------+
\tIdentity Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 1.0
\tSerial: 421616185990326931
\tStart Date: 2014-05-08 13:04:04+00:00
\tEnd Date: 2030-05-08 13:04:04+00:00
\tAlt Name: URI:CN=redhat.local.rm-rf.ca

Subject:
\tCN: 0f5d4617-d913-4a0f-be61-d8a9c88e1476

Issuer:
\tC: US
\tCN: wpoteat-desktop.usersys.redhat.com
\tL: Raleigh

""" % ({'space': ' '})

PRODUCT_CERT_V1_0_STAT_OUTPUT = \
"""Type: Product Certificate
Version: 1.0
DER size: 892b
Subject Key ID size: 20b
"""

PRODUCT_CERT_WITH_OS_NAME_V1_0_STAT_OUTPUT = \
"""Type: Product Certificate
Version: 1.0
DER size: 894b
Subject Key ID size: 20b
"""

ENTITLEMENT_CERT_V3_0_STAT_OUTPUT = \
"""Type: Entitlement Certificate
Version: 3.0
DER size: 915b
Subject Key ID size: 20b
Content sets: 4
"""
