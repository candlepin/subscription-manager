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

# Test entitlement to the product cert above:
ENTITLEMENT_CERT_V1_0 = """
-----BEGIN CERTIFICATE-----
MIIJSzCCCLSgAwIBAgIICT4q81yqebkwDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MDUwMDAwMDBaFw0xMzA3MDUwMDAwMDBaMCsxKTAnBgNVBAMTIGZmODA4
MDgxMzg1NzRiZDIwMTM4NTc0ZDg1YTUwYjJmMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAlUV2otyTyQbhSV77Od1qoZMwr2Xz1gvgQUN5/0b7HREutMCT
4okqvDkYkt50pu76M0CatAK89A716plMjzcFyyWvUuR9adxzD6VXTSxORabL1hto
30a6hERNdwt7ma43ezvouY0tvjQ8MDFMQb2MC5yhKAq3H1mdZEtDdjlU7MQ1ujX3
wK2We0HW4sMkZXM/ZtiqXU5vB9h5hVFeZo4E7d+HayopsQoB5cKMu9MAGCg75rdD
i3pO/9za1q2fQsUjnzImMPBCVfpN2K7CuI7098MxDyjvNrU/Vql6rYhDbdGOJTWD
GZf40j/j/T+CReEMZsKHNRgLtMK+dcg4GuD+DQIDAQABo4IG5zCCBuMwEQYJYIZI
AYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDBmBgNVHSMEXzBdgBREQHYTNskB3AHY
/8EcmROo5jrOoqE6pDgwNjEVMBMGA1UEAwwMMTkyLjE2OC4xLjI1MQswCQYDVQQG
EwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAPMeoqmMwB3XMB0GA1UdDgQWBBSsreit
gWXwXzIMZ3JIMdUOEkylIDATBgNVHSUEDDAKBggrBgEFBQcDAjAxBhErBgEEAZII
CQGW3rGD6YACAQQcDBpBd2Vzb21lIE9TIGZvciB4ODZfNjQgQml0czAdBhErBgEE
AZIICQGW3rGD6YACAwQIDAZ4ODZfNjQwGwYRKwYBBAGSCAkBlt6xg+mAAgIEBgwE
My4xMTAUBgsrBgEEAZIICQIBAQQFDAN5dW0wKAYMKwYBBAGSCAkCAQEBBBgMFmFs
d2F5cy1lbmFibGVkLWNvbnRlbnQwKAYMKwYBBAGSCAkCAQECBBgMFmFsd2F5cy1l
bmFibGVkLWNvbnRlbnQwHQYMKwYBBAGSCAkCAQEFBA0MC3Rlc3QtdmVuZG9yMC4G
DCsGAQQBkggJAgEBBgQeDBwvZm9vL3BhdGgvYWx3YXlzLyRyZWxlYXNldmVyMCYG
DCsGAQQBkggJAgEBBwQWDBQvZm9vL3BhdGgvYWx3YXlzL2dwZzATBgwrBgEEAZII
CQIBAQgEAwwBMTAVBgwrBgEEAZIICQIBAQkEBQwDMjAwMBUGDCsGAQQBkggJAtZ0
AQQFDAN5dW0wIwYNKwYBBAGSCAkC1nQBAQQSDBBhd2Vzb21lb3MteDg2XzY0MCMG
DSsGAQQBkggJAtZ0AQIEEgwQYXdlc29tZW9zLXg4Nl82NDAaBg0rBgEEAZIICQLW
dAEFBAkMB1JlZCBIYXQwLAYNKwYBBAGSCAkC1nQBBgQbDBkvcGF0aC90by9hd2Vz
b21lb3MveDg2XzY0MCoGDSsGAQQBkggJAtZ0AQcEGQwXL3BhdGgvdG8vYXdlc29t
ZW9zL2dwZy8wFAYNKwYBBAGSCAkC1nQBCAQDDAEwMBcGDSsGAQQBkggJAtZ0AQkE
BgwEMzYwMDAUBgsrBgEEAZIICQIAAQQFDAN5dW0wJwYMKwYBBAGSCAkCAAEBBBcM
FW5ldmVyLWVuYWJsZWQtY29udGVudDAnBgwrBgEEAZIICQIAAQIEFwwVbmV2ZXIt
ZW5hYmxlZC1jb250ZW50MB0GDCsGAQQBkggJAgABBQQNDAt0ZXN0LXZlbmRvcjAh
BgwrBgEEAZIICQIAAQYEEQwPL2Zvby9wYXRoL25ldmVyMCUGDCsGAQQBkggJAgAB
BwQVDBMvZm9vL3BhdGgvbmV2ZXIvZ3BnMBMGDCsGAQQBkggJAgABCAQDDAEwMBUG
DCsGAQQBkggJAgABCQQFDAM2MDAwFQYMKwYBBAGSCAkC1mkBBAUMA3l1bTAcBg0r
BgEEAZIICQLWaQEBBAsMCWF3ZXNvbWVvczAcBg0rBgEEAZIICQLWaQECBAsMCWF3
ZXNvbWVvczAaBg0rBgEEAZIICQLWaQEFBAkMB1JlZCBIYXQwOwYNKwYBBAGSCAkC
1mkBBgQqDCgvcGF0aC90by8kYmFzZWFyY2gvJHJlbGVhc2V2ZXIvYXdlc29tZW9z
MCoGDSsGAQQBkggJAtZpAQcEGQwXL3BhdGgvdG8vYXdlc29tZW9zL2dwZy8wFAYN
KwYBBAGSCAkC1mkBCAQDDAExMBcGDSsGAQQBkggJAtZpAQkEBgwEMzYwMDAlBgor
BgEEAZIICQQBBBcMFUF3ZXNvbWUgT1MgZm9yIHg4Nl82NDAwBgorBgEEAZIICQQC
BCIMIGZmODA4MDgxMzg1NzRiZDIwMTM4NTc0YzdmMWYwMjNjMCAGCisGAQQBkggJ
BAMEEgwQYXdlc29tZW9zLXg4Nl82NDARBgorBgEEAZIICQQFBAMMATUwEQYKKwYB
BAGSCAkECQQDDAExMCQGCisGAQQBkggJBAYEFgwUMjAxMi0wNy0wNVQwMDowMDow
MFowJAYKKwYBBAGSCAkEBwQWDBQyMDEzLTA3LTA1VDAwOjAwOjAwWjASBgorBgEE
AZIICQQMBAQMAjMwMBIGCisGAQQBkggJBAoEBAwCNjYwGwYKKwYBBAGSCAkEDQQN
DAsxMjMzMTEzMTIzMTARBgorBgEEAZIICQQOBAMMATAwEQYKKwYBBAGSCAkEEQQD
DAExMBEGCisGAQQBkggJBAsEAwwBMjA0BgorBgEEAZIICQUBBCYMJDQwOTJlYzcz
LTE5MGUtNGY0Ny1iMmEzLWUxZTg4OWVkOGE5ODANBgkqhkiG9w0BAQUFAAOBgQA4
BLbyoRumbzf3/UXZfzkQbUPeN1CYBP64soVdIe8Wp0Dp3H6ZF8CFR6+w1R3Q7asL
Ej4AxyURBnHhQCz5UleHnMBdLU9BK2Z0BTHCrkke8tDFxsIQ2oz2Ny/+gqegyJS/
AOY8AMtVsQ9LuANGqNf42hcpFsAWy5kboT+gIXFxmw==
-----END CERTIFICATE-----
"""

ENTITLEMENT_CERT_V2_0 = """
-----BEGIN CERTIFICATE-----
MIIFQDCCBKmgAwIBAgIIVdtEBxIAQ8AwDQYJKoZIhvcNAQEFBQAwNjEVMBMGA1UE
AwwMMTkyLjE2OC4xLjI1MQswCQYDVQQGEwJVUzEQMA4GA1UEBwwHUmFsZWlnaDAe
Fw0xMjA3MTkwMDAwMDBaFw0xMzA3MTkwMDAwMDBaMCsxKTAnBgNVBAMTIGZmODA4
MDgxMzhiNDMwMDMwMTM4YjQ3YTMyNWIwMTFmMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAsQEeLAw6rQfopwa8Nhz9YgDoVzfSCPaZnp7i74G4fgj5T4Pa
f2pI4Hew8FXjlCktHfP3v/CUhYVZnFUFIPkPuRCt/SRYDigZ4T9d7hT7TCQKUfyR
io5ZLdrOyv+JiIFQ2L3ZN9ZiH6woy2WmO+MWOyVU7NEpLM8Pe7ouFVOZzHMXj53T
k8Wln6B7fpGGL2Y5CocW6ULEJLoqtpM+O+17gTXS5Kf+L3p29PfGl3QiL8CN7m/L
D4GfpJYr6zrfiQLQKqkSSeCT6g6woIxwBVUUbsSXagAErPqNTij5BniIwmSzsvhw
6i0BgKxGTy8pa0VEFhxVpq/8d0h11cg+hncWnwIDAQABo4IC3DCCAtgwEQYJYIZI
AYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDBmBgNVHSMEXzBdgBREQHYTNskB3AHY
/8EcmROo5jrOoqE6pDgwNjEVMBMGA1UEAwwMMTkyLjE2OC4xLjI1MQswCQYDVQQG
EwJVUzEQMA4GA1UEBwwHUmFsZWlnaIIJAPMeoqmMwB3XMB0GA1UdDgQWBBTaUymf
F8CznrGetK9A2WCbwaef/DATBgNVHSUEDDAKBggrBgEFBQcDAjASBgkrBgEEAZII
CQYEBQwDMi4wMIICBAYJKwYBBAGSCAkHBIIB9QSCAfF4nJ1UTY+bMBD9K5G1Ryg2
zpLArT31VqntqdUqGsyQRQE7tc1mo1X+e8fkQ+wmm40WkLCZYd5782y/MGMrtKx4
Ycpob0F5VrAsYxFzHmyYpFykMZ/FIv/NeTE8fygMSplehwSRSimEpJeg7/960L7x
W1bcR0z3XRmqs7qec7qFnOc1gCj5YaRkyrnAgIe62qPJM7QdselLp2yz9o3Rga0z
aoXesUIMTNWq0ctFEyoEEho6pOHXDTrT4eTHr0lt7OR5ni2yaZC26ikK+6hx8Smw
AaupECsk342lpFFoj+u7QQyXEkVeilhk01k8VdkszvG+jHk6n3FUPJ/JUGxtTdWr
wPHvvrsY2kXjE80OPVTgYYHP68YSY2pGxJ6oEybgeHQ+PsxOmqDdwNbFqKFssYqP
dQkO/CPFk9qYJIyTfWZyZ7FFcPiEocpyvVz0tr2USCFKaKHE9hqO364Dj23fkS9H
MUKk08HDIZsVNbQOLwiU2SuFP7GafAc/UnfuyVHXQNWb5JSSnFJGos6zKJiMdZ0j
XFLEb1GTfWyXDn2/xS19xaAh9saf9wq/Y4+Ql9bbzXZc8OGupEUFVj2OV1gy/uNT
tryR8BAdJPDxlYYDiKAbj8r3FsMeYwc/H65v/8m3xgcQIuuGs4TJL0IQ0O4/08KY
9jANBgkqhkiG9w0BAQUFAAOBgQBfW8CKiRuDoGnVIVca+CMpVc4FUnbrrWN1YITa
7BVeOL9A+MdWS2b3sNG6HTqtx+56HVQkdImvmyuQEadYiFEI2CNbzjTpenc9W6De
6u9uuTNCB3Kv8J7tRDQpAkRevQxPGx6rDDi/Dzh5zcUBbY1Y48Q4zTG0AwOCqJkc
pBNdPQ==
-----END CERTIFICATE-----
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
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
	Path: None
	Version: 1.0
	Serial: 666017019617507769
	Start Date: 2012-07-05 00:00:00+00:00
	End Date: 2013-07-05 00:00:00+00:00

Subject:
	CN: ff80808138574bd20138574d85a50b2f

Product:
	ID: 100000000000002
	Name: Awesome OS for x86_64 Bits
	Version: 3.11
	Arch: x86_64
	Tags: 

Order:
	Name: Awesome OS for x86_64
	Number: ff80808138574bd20138574c7f1f023c
	SKU: awesomeos-x86_64
	Contract: 66
	Account: 12331131231
	Service Level: None
	Service Type: None
	Quantity: 5
	Quantity Used: 2
	Socket Limit: 1
	Virt Limit: None
	Virt Only: False
	Subscription: None
	Stacking ID: 1
	Warning Period: 30
	Provides Management: 0

Content:
	Name: always-enabled-content
	Label: always-enabled-content
	Vendor: test-vendor
	URL: /foo/path/always/$releasever
	GPG: /foo/path/always/gpg
	Enabled: True
	Expires: 200
	Required Tags: 

Content:
	Name: awesomeos
	Label: awesomeos
	Vendor: Red Hat
	URL: /path/to/$basearch/$releasever/awesomeos
	GPG: /path/to/awesomeos/gpg/
	Enabled: True
	Expires: 3600
	Required Tags: 

Content:
	Name: awesomeos-x86_64
	Label: awesomeos-x86_64
	Vendor: Red Hat
	URL: /path/to/awesomeos/x86_64
	GPG: /path/to/awesomeos/gpg/
	Enabled: False
	Expires: 3600
	Required Tags: 

Content:
	Name: never-enabled-content
	Label: never-enabled-content
	Vendor: test-vendor
	URL: /foo/path/never
	GPG: /foo/path/never/gpg
	Enabled: False
	Expires: 600
	Required Tags: 
"""

ENTITLEMENT_CERT_V2_0_OUTPUT = """
+-------------------------------------------+
\tEntitlement Certificate
+-------------------------------------------+

Certificate:
	Path: None
	Version: 2.0
	Serial: 6186613310280975296
	Start Date: 2012-07-19 00:00:00+00:00
	End Date: 2013-07-19 00:00:00+00:00

Subject:
	CN: ff80808138b430030138b47a325b011f

Product:
	ID: 100000000000002
	Name: Awesome OS for x86_64 Bits
	Version: 3.11
	Arch: x86_64
	Tags: 

Order:
	Name: Awesome OS for x86_64
	Number: ff808081389faa1b01389faac32001e6
	SKU: awesomeos-x86_64
	Contract: 66
	Account: 12331131231
	Service Level: None
	Service Type: None
	Quantity: 5
	Quantity Used: 2
	Socket Limit: 1
	Virt Limit: None
	Virt Only: False
	Subscription: None
	Stacking ID: 1
	Warning Period: 30
	Provides Management: False

Content:
	Name: always-enabled-content
	Label: always-enabled-content
	Vendor: test-vendor
	URL: /foo/path/always/$releasever
	GPG: /foo/path/always/gpg
	Enabled: True
	Expires: 200
	Required Tags: 

Content:
	Name: awesomeos
	Label: awesomeos
	Vendor: Red Hat
	URL: /path/to/$basearch/$releasever/awesomeos
	GPG: /path/to/awesomeos/gpg/
	Enabled: True
	Expires: 3600
	Required Tags: 

Content:
	Name: awesomeos-x86_64
	Label: awesomeos-x86_64
	Vendor: Red Hat
	URL: /path/to/awesomeos/x86_64
	GPG: /path/to/awesomeos/gpg/
	Enabled: False
	Expires: 3600
	Required Tags: 

Content:
	Name: never-enabled-content
	Label: never-enabled-content
	Vendor: test-vendor
	URL: /foo/path/never
	GPG: /foo/path/never/gpg
	Enabled: False
	Expires: 600
	Required Tags: 
"""

PRODUCT_CERT_V1_0_OUTPUT = """
+-------------------------------------------+
\tProduct Certificate
+-------------------------------------------+

Certificate:
	Path: None
	Version: 1.0
	Serial: 168296333
	Start Date: 2011-08-23 17:41:39+00:00
	End Date: 2021-08-23 17:41:39+00:00

Subject:
	CN: 100000000000002

Product:
	ID: 100000000000002
	Name: Awesome OS for x86_64 Bits
	Version: 3.11
	Arch: x86_64
	Tags: 

"""

IDENTITY_CERT_OUTPUT = """
+-------------------------------------------+
\tIdentity Certificate
+-------------------------------------------+

Certificate:
	Path: None
	Version: None
	Serial: 5412106042110780569
	Start Date: 2012-07-10 12:21:27+00:00
	End Date: 2028-07-10 12:21:27+00:00
	Alt Name: DirName:/CN=redhat.local.rm-rf.ca

Subject:
	CN: eaadd6ea-852d-4430-94a7-73d5887d48e8

"""
