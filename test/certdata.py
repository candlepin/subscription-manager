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


ENTITLEMENT_CERT_V3_2 = """
-----BEGIN CERTIFICATE-----
MIIDvzCCAyigAwIBAgIIRc0LPzgyLGkwDQYJKoZIhvcNAQEFBQAwTDErMCkGA1UE
Awwid3BvdGVhdC1kZXNrdG9wLnVzZXJzeXMucmVkaGF0LmNvbTELMAkGA1UEBhMC
VVMxEDAOBgNVBAcMB1JhbGVpZ2gwHhcNMTYwMjI0MDAwMDAwWhcNMTYwMjI1MTQ1
NTM3WjArMSkwJwYDVQQDEyA4YThkMDkwMTUzMTNjNWM3MDE1MzEzYzc2NGI1MTNm
OTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKjdIp/Pa0pqdV+y60GE
PqiGt3BtHFSYjftwNZ6UtSgjih8/iqyZWp2l1xdr+4fJTADqUnKQ6JvyzCoseFaM
R8TNecb8R06E2qKaiEZVY4hOSQ08h950n0TOgSVABzvGd3tVGTEzYXhhvNAaARPZ
5jtCOGThELi90y3AUINjO/8mFWOJj5t238hkL3/ZR9puRSznJTKUre1r+Ba5plp9
T9Z9GWBdk7brjGoGZwCSPxmMPqQ1CHvd/cuPK2gLLw5oGo7Sk/dhT8towJZsTiBt
TmCyUyPJfbwwkXg6jP0nt7FjZgwUJfPC8zzd6bUyH0giphH9tnPtgtUZgEINpqDi
KvkCAwEAAaOCAUUwggFBMBEGCWCGSAGG+EIBAQQEAwIFoDALBgNVHQ8EBAMCBLAw
fAYDVR0jBHUwc4AUP/y+GXDcoUN2KX68Eo3YOhNPzYmhUKROMEwxKzApBgNVBAMM
Indwb3RlYXQtZGVza3RvcC51c2Vyc3lzLnJlZGhhdC5jb20xCzAJBgNVBAYTAlVT
MRAwDgYDVQQHDAdSYWxlaWdoggkAvDi6Ws2GP54wHQYDVR0OBBYEFIcL5Tayc/Lc
1coZTCFEbWrtFnU+MBMGA1UdJQQMMAoGCCsGAQUFBwMCMBIGCSsGAQQBkggJBgQF
DAMzLjIwWQYJKwYBBAGSCAkHBEwESnjaDcrBDYAwDANALwQDsE0ErlqpwRGpKGwP
9z7r097EyZsX6hixoUjgYx6d6y6HTaacysV1tNL+GDYqPoLhFUUGj4dpmZNT7/qA
MA0GCSqGSIb3DQEBBQUAA4GBAAD6nUzJgSIcx03cxLN0hbjK0PSMOl3ITH45ckgs
YI1RWMRs3Vd019DM+H85wIZ8clkCiU7GFt6GuNy/aYj3pLb1Y8Baewz5Z9lkp7JQ
nU8TVNndsbZ82tnQF6wnHnHu4Y8EwiA4w0hI0Ez3RW3BhfXKI0+cbO3MILr8o5QJ
QzGj
-----END CERTIFICATE-----
-----BEGIN ENTITLEMENT DATA-----
eJzFVV1vmzAU/SuRnzYpLjYkQPLWadpeOu2hfVpVRY65SVANpv5IG0X577sG0qht
0nadpklIxveee+85BwNbInVtfQWGTEmWF5BKHtMilSkdCTahYg6MCgFykuX5aJJm
ZEjuvKhd6TZkyofE+rmVpmxcqWsy3RJ767GTuAerK9CWWjBrMHQubCnpupBYX4sK
EHPeYQY/LweXLWjwJYAGnwoElsZ9RqjV8hacJdN4SIyo2lVqAxgZYRbLSglhrII1
KGz6zStFL/v4kLhNE0Z9NeUa6NXKaL9ckd2QhP4zXSvU4IwHjGhTBA+2pPbVvHWj
jdA8zcYJmzyRTYNuJ4xDVMx4SllM49EVY9P2+oVgqIsumbXJ5EkSLXdGyFDOcCuk
1L4OOx4nCecJLpw8t5ZwxuPAvTG68DKYcr0lZRiTZCxnR439oYtyUQZrSyxA3WBs
1y09CyOEkavSgXS+9fSanF9ckJuOIQRK+xGc4/BHPze+Oow7POuqn4Y5hQdHnUqu
0R0dLHZgHe13KEy4FQZXzjXTKIIHUTUKzqSuoqNdoBZzBUhuIZSFTssTEctmOfNG
vbdlhHiyu9kND66mx13dH9e/95Sf8HSPPRjZR2i3f8vDaKF11N7/kU+PZcGLCGsr
cKIQTszgoSkNMmOP9sTJ+HXyFKrGbYKpJ1R0ANoh/ometxSM3lBQ69fo1/o/cj/B
3InlEgr68vy8SLyTdCTUvdjYj56jrjrqfDJw51FHMUMybeHV+ffwBuASk8OLx05o
qyH8SXoaRySeyr9XaVv/UaFtca/zxXNLGcMPC1Y2Wqvwk2l15iIv2ITxccITOZZZ
f5fm80XBxhkju91v8ZVy9g==
-----END ENTITLEMENT DATA-----
-----BEGIN RSA SIGNATURE-----
LvIgKpAzQavNym0DkA2UxoQqA8LQdEwb+x+6BGOs0meZuVuebIw5BjWAiUADmyxO
nID3SAuNrg5IPmRr4a4/Y24EC/shObFkkVh+3EUPjGAx4yL/R/ePrSlD0LZGct7j
x5Vyo49z4GS7ww3ByciI2cUnaVA2axVBmscgZ7nAlKE=
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
\tSubscription: 
\tService Level: Premium
\tService Type: Level 3
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

ENTITLEMENT_CERT_V3_2_OUTPUT = """
+-------------------------------------------+
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
\tPath:%(space)s
\tVersion: 3.2
\tSerial: 5029688724996369513
\tStart Date: 2016-02-24 00:00:00+00:00
\tEnd Date: 2016-02-25 14:55:37+00:00
\tPool ID: 8a8d09015313c5c7015313c68bfd0570

Subject:
\tCN: 8a8d09015313c5c7015313c764b513f9

Issuer:
\tC: US
\tCN: wpoteat-desktop.usersys.redhat.com
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
\tID: 37080
\tName: Awesome OS Modifier Bits
\tVersion: 6.1
\tArch: ALL
\tTags:%(space)s
\tBrand Type:%(space)s
\tBrand Name:%(space)s

Order:
\tName: Awesome OS Server Basic (dc-virt)
\tNumber: order-8675309
\tSKU: awesomeos-server-basic-vdc
\tContract: 0
\tAccount: 12331131231
\tSubscription: 1012
\tService Level: Full-Service
\tService Type: Drive-Through
\tQuantity: Unlimited
\tQuantity Used: 1
\tSocket Limit: 2
\tRAM Limit: 2
\tCore Limit: 4
\tVirt Only: True
\tStacking ID:%(space)s
\tWarning Period: 0
\tProvides Management: False

Content:
\tType: yum
\tName: awesomeos-modifier
\tLabel: awesomeos-modifier
\tVendor: test-vendor
\tURL: http://example.com/awesomeos-modifier
\tGPG: http://example.com/awesomeos-modifier/gpg
\tEnabled: False
\tExpires:%(space)s
\tRequired Tags:%(space)s
\tArches: ALL

Content:
\tType: yum
\tName: content
\tLabel: content-label
\tVendor: test-vendor
\tURL: /foo/path
\tGPG: /foo/path/gpg/
\tEnabled: False
\tExpires: 0
\tRequired Tags:%(space)s
\tArches: ALL

Content:
\tType: yum
\tName: content-emptygpg
\tLabel: content-label-empty-gpg
\tVendor: test-vendor
\tURL: /foo/path
\tGPG:%(space)s
\tEnabled: False
\tExpires: 0
\tRequired Tags:%(space)s
\tArches: ALL

Content:
\tType: yum
\tName: content-nogpg
\tLabel: content-label-no-gpg
\tVendor: test-vendor
\tURL: /foo/path
\tGPG:%(space)s
\tEnabled: False
\tExpires: 0
\tRequired Tags:%(space)s
\tArches: ALL

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
\tArches: ALL

Content:
\tType: yum
\tName: tagged-content
\tLabel: tagged-content
\tVendor: test-vendor
\tURL: /foo/path/always
\tGPG: /foo/path/always/gpg
\tEnabled: False
\tExpires:%(space)s
\tRequired Tags: TAG1, TAG2
\tArches: ALL
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

ENTITLEMENT_CERT_V3_2_STAT_OUTPUT = \
"""Type: Entitlement Certificate
Version: 3.2
DER size: 963b
Subject Key ID size: 20b
Content sets: 6
"""
