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

# A product cert from Candlepin's test data (product 37060, Awesome 
# OS server bits", this one with the "os_name" oid added.
PRODUCT_CERT_WITH_OS_NAME_V1_0 = """
-----BEGIN CERTIFICATE-----
MIIDpTCCAw6gAwIBAgIEAuhqBjANBgkqhkiG9w0BAQUFADBDMSIwIAYDVQQDDBlk
aGNwMjMxLTI4LnJkdS5yZWRoYXQuY29tMQswCQYDVQQGEwJVUzEQMA4GA1UEBwwH
UmFsZWlnaDAeFw0xMzA4MDcxOTIxMTRaFw0yMzA4MDcxOTIxMTRaMBAxDjAMBgNV
BAMTBTM3MDYwMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAltwl2LOz
wz/mVLJcMsOFKNOF76ZVn+U+ghYZcjoTBs51Z3SHQtxtuNl8qzIyYG+8WtBn+IRP
0R7E18aMpjTBwH12GmvAvXbGs0dl2DkTy9U1ABWGBH5zoXuOQgYngTgFTQFsezj2
+COCqMWoxIoo6f+wAOjdOQjXRoQY++1xiV2vUcjrBNnJP5uQ8rR/i93O9LnJwwZb
jOmPXth7j7Z+BbMF8Qlpcjzek5CgD9e9nXwGnXHEQOLYcNlrNdZ9ol0GZU4UgRPH
l5QPl5tJb2x8vvucVPi6BePwtdnPb6LrkAYIs3+1sz96eW7rH/whoXgkYwlFzYTp
f6nOFHq0FDMLOwIDAQABo4IBUzCCAU8wEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1Ud
DwQEAwIEsDBzBgNVHSMEbDBqgBSDdvsVOoqGnbd6CZpTN+h0abcYsKFHpEUwQzEi
MCAGA1UEAwwZZGhjcDIzMS0yOC5yZHUucmVkaGF0LmNvbTELMAkGA1UEBhMCVVMx
EDAOBgNVBAcMB1JhbGVpZ2iCCQCivgxh/4ZSUDAdBgNVHQ4EFgQU6beHs3n6KTqe
7AHev5a6Ip0IB/4wEwYDVR0lBAwwCgYIKwYBBQUHAwIwKQYNKwYBBAGSCAkBgqFE
AQQYDBZBd2Vzb21lIE9TIFNlcnZlciBCaXRzMBYGDSsGAQQBkggJAYKhRAMEBQwD
QUxMMBYGDSsGAQQBkggJAYKhRAIEBQwDNi4xMCkGDSsGAQQBkggJAYKhRAUEGAwW
QXdlc29tZSBPUyBTZXJ2ZXIgQml0czANBgkqhkiG9w0BAQUFAAOBgQA3XyscDR5Y
UK5MXD4DPEGwJq1mFa34DgAPJR3THybLVeRSfZxEFk4zjcM2woDmJNMal2KR57uB
3RaxHkdYtpu4HGrwZElJTMTXwHx4N3VQGCOGzUy7NJIIN5VFTgzuQnwXkuHOCry/
Q8zxGCc+NSWiEtQIsjhegMIp8qSuuPCPHg==
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


IDENTITY_CERT = """
-----BEGIN CERTIFICATE-----
MIIDVTCCAr6gAwIBAgIISxupxU7CJJkwDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MTAxMjIxMjdaFw0yODA3MTAxMjIxMjdaMC8xLTArBgNVBAMTJGVhYWRk
NmVhLTg1MmQtNDQzMC05NGE3LTczZDU4ODdkNDhlODCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAIwkCSdEYYRBD6uHC20Wh3491i4OfkQKtufOkBiMw6Rv
90tqsiolC4bGgRk1vwgSfyaeTITu92tnRM2mxbZ/xzbV7B+r/LW5DLnAUufZWwpF
B/Bpv2+hJAZh927MaxaYWhtMuX7rxiz77TpVtxhEnC1M8xj0/3dqOEOABD5x3yVs
KQBA+3eDu/ocptyoHxoEsR9RYdmdAxxIKm29NtlqG+lXoHDqjckXiPxFWDLLjFnF
T7oE6zoZQ+5aBgoOu5bTpHW4jQc7ddKOo33NUF1x9lTQKG4How8XkMdy4/EjeaE9
fWa1dSahgDyMeKNZkW0PI9OPOVsV7Yg7oaBEjCX0FDsCAwEAAaOB7jCB6zARBglg
hkgBhvhCAQEEBAMCBaAwCwYDVR0PBAQDAgSwMGYGA1UdIwRfMF2AFERAdhM2yQHc
Adj/wRyZE6jmOs6ioTqkODA2MRUwEwYDVQQDDAwxOTIuMTY4LjEuMjUxCzAJBgNV
BAYTAlVTMRAwDgYDVQQHDAdSYWxlaWdoggkA8x6iqYzAHdcwHQYDVR0OBBYEFLO4
v3v+LWsotuGi0n1kxcQ7L7YkMBMGA1UdJQQMMAoGCCsGAQUFBwMCMC0GA1UdEQQm
MCSkIjAgMR4wHAYDVQQDDBVyZWRoYXQubG9jYWwucm0tcmYuY2EwDQYJKoZIhvcN
AQEFBQADgYEAfQgG0q88GELGHLhk3HI3Ygnqy7XqccSF4WWC1YsxQMpT2QLwAcAK
X6IYCJfN6Y6ywZDD0o+ISr2gpEh24nW+ZSHRpPxgirlm1/SFN4gT+UQrCRn5as6v
t3EKmOyL75TqMEhhNiKuEd0sfIkBqgVh9+980hXBGruIANL2syxDeYY=
-----END CERTIFICATE-----
"""


# Cert contents
# NOTE: Must match the contents of the certs above.
# NOTE: Some editors will automatically replace tabs/spaces
#       and remove trailing whitespace. This will cause
#       test errors if this happens.

ENTITLEMENT_CERT_V1_0_OUTPUT = """
+-------------------------------------------+
	Entitlement Certificate
+-------------------------------------------+

Certificate:
	Path: 
	Version: 1.0
	Serial: 60063758564076674
	Start Date: 2012-09-07 00:00:00+00:00
	End Date: 2013-09-07 00:00:00+00:00
	Pool ID: Not Available

Subject:
	CN: ff80808139affbb50139b5841809706e

Issuer:
	C: US
	CN: boogady
	L: Raleigh

Product:
	ID: 37060
	Name: Awesome OS Server Bits
	Version: 6.1
	Arch: ALL
	Tags: 

Product:
	ID: 37065
	Name: Clustering Bits
	Version: 1.0
	Arch: ALL
	Tags: 

Product:
	ID: 37067
	Name: Shared Storage Bits
	Version: 1.0
	Arch: ALL
	Tags: 

Product:
	ID: 37068
	Name: Large File Support Bits
	Version: 1.0
	Arch: ALL
	Tags: 

Product:
	ID: 37069
	Name: Management Bits
	Version: 1.0
	Arch: ALL
	Tags: 

Product:
	ID: 37070
	Name: Load Balancing Bits
	Version: 1.0
	Arch: ALL
	Tags: 

Order:
	Name: Awesome OS Server Bundled
	Number: ff80808139a0a7160139a0a8501d0295
	SKU: awesomeos-server
	Contract: 359
	Account: 12331131231
	Service Level: Premium
	Service Type: Level 3
	Quantity: 10
	Quantity Used: 1
	Socket Limit: 2
	RAM Limit: 
	Core Limit: 
	Virt Only: False
	Subscription: 
	Stacking ID: 
	Warning Period: 30
	Provides Management: 1

Content:
	Type: yum
	Name: always-enabled-content
	Label: always-enabled-content
	Vendor: test-vendor
	URL: /foo/path/always/$releasever
	GPG: /foo/path/always/gpg
	Enabled: True
	Expires: 200
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: content
	Label: content-label
	Vendor: test-vendor
	URL: /foo/path
	GPG: /foo/path/gpg/
	Enabled: True
	Expires: 0
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: content-emptygpg
	Label: content-label-empty-gpg
	Vendor: test-vendor
	URL: /foo/path
	GPG: 
	Enabled: True
	Expires: 0
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: content-nogpg
	Label: content-label-no-gpg
	Vendor: test-vendor
	URL: /foo/path
	GPG: 
	Enabled: True
	Expires: 0
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: never-enabled-content
	Label: never-enabled-content
	Vendor: test-vendor
	URL: /foo/path/never
	GPG: /foo/path/never/gpg
	Enabled: False
	Expires: 600
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: tagged-content
	Label: tagged-content
	Vendor: test-vendor
	URL: /foo/path/always
	GPG: /foo/path/always/gpg
	Enabled: True
	Expires: 
	Required Tags: TAG1, TAG2
	Arches: 
"""

ENTITLEMENT_CERT_V3_0_OUTPUT = """
+-------------------------------------------+
	Entitlement Certificate
+-------------------------------------------+

Certificate:
	Path: 
	Version: 3.0
	Serial: 1306183239866671852
	Start Date: 2012-09-18 00:00:00+00:00
	End Date: 2013-09-18 00:00:00+00:00
	Pool ID: Not Available

Subject:
	CN: ff80808139d9e26c0139da23489a0066

Issuer:
	C: US
	CN: pipboy
	L: Raleigh

Product:
	ID: 100000000000002
	Name: Awesome OS for x86_64 Bits
	Version: 3.11
	Arch: x86_64
	Tags: 

Order:
	Name: Awesome OS for x86_64
	Number: ff80808139d94b400139d94c018c0164
	SKU: awesomeos-x86_64
	Contract: 67
	Account: 12331131231
	Service Level: 
	Service Type: 
	Quantity: 10
	Quantity Used: 2
	Socket Limit: 1
	RAM Limit: 
	Core Limit: 
	Virt Only: False
	Subscription: 
	Stacking ID: 1
	Warning Period: 30
	Provides Management: False

Content:
	Type: yum
	Name: always-enabled-content
	Label: always-enabled-content
	Vendor: test-vendor
	URL: /foo/path/always/$releasever
	GPG: /foo/path/always/gpg
	Enabled: True
	Expires: 200
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: awesomeos
	Label: awesomeos
	Vendor: Red Hat
	URL: /path/to/$basearch/$releasever/awesomeos
	GPG: /path/to/awesomeos/gpg/
	Enabled: True
	Expires: 3600
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: awesomeos-x86_64
	Label: awesomeos-x86_64
	Vendor: Red Hat
	URL: /path/to/awesomeos/x86_64
	GPG: /path/to/awesomeos/gpg/
	Enabled: False
	Expires: 3600
	Required Tags: 
	Arches: 

Content:
	Type: yum
	Name: never-enabled-content
	Label: never-enabled-content
	Vendor: test-vendor
	URL: /foo/path/never
	GPG: /foo/path/never/gpg
	Enabled: False
	Expires: 600
	Required Tags: 
	Arches: 
"""

PRODUCT_CERT_V1_0_OUTPUT = """
+-------------------------------------------+
\tProduct Certificate
+-------------------------------------------+

Certificate:
	Path: 
	Version: 1.0
	Serial: 168296333
	Start Date: 2011-08-23 17:41:39+00:00
	End Date: 2021-08-23 17:41:39+00:00

Subject:
	CN: 100000000000002

Issuer:
	C: US
	CN: localhost
	L: Raleigh

Product:
	ID: 100000000000002
	Name: Awesome OS for x86_64 Bits
	Version: 3.11
	Arch: x86_64
	Tags: 

"""

PRODUCT_CERT_WITH_OS_NAME_V1_0_OUTPUT = """
+-------------------------------------------+
	Product Certificate
+-------------------------------------------+

Certificate:
	Path: 
	Version: 1.0
	Serial: 48785926
	Start Date: 2013-08-07 19:21:14+00:00
	End Date: 2023-08-07 19:21:14+00:00

Subject:
	CN: 37060

Issuer:
	C: US
	CN: dhcp231-28.rdu.redhat.com
	L: Raleigh

Product:
	ID: 37060
	Name: Awesome OS Server Bits
	Version: 6.1
	Arch: ALL
	Tags: 

"""

IDENTITY_CERT_OUTPUT = """
+-------------------------------------------+
\tIdentity Certificate
+-------------------------------------------+

Certificate:
	Path: 
	Version: 1.0
	Serial: 5412106042110780569
	Start Date: 2012-07-10 12:21:27+00:00
	End Date: 2028-07-10 12:21:27+00:00
	Alt Name: DirName:/CN=redhat.local.rm-rf.ca

Subject:
	CN: eaadd6ea-852d-4430-94a7-73d5887d48e8

Issuer:
	C: US
	CN: 192.168.1.25
	L: Raleigh

"""

PRODUCT_CERT_V1_0_STAT_OUTPUT = \
"""Type: Product Certificate
Version: 1.0
DER size: 892b
Subject Key ID size: 20b
"""

PRODUCT_CERT_WITH_OS_NAME_V1_0_STAT_OUTPUT = \
"""Type: Product Certificate
Version: 1.0
DER size: 937b
Subject Key ID size: 20b
"""

ENTITLEMENT_CERT_V3_0_STAT_OUTPUT = \
"""Type: Entitlement Certificate
Version: 3.0
DER size: 915b
Subject Key ID size: 20b
Content sets: 4
"""
