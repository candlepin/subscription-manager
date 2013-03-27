import zipfile
from zipfile import ZipFile
from rct.manifest_commands import ZipExtractAll
from cStringIO import StringIO

correct_manifest_output = """
+-------------------------------------------+
	Manifest
+-------------------------------------------+

General:
	Server: access.stage.redhat.com/management/distributors/
	Server Version: 0.7.13.13-1
	Date Created: 2013-02-21T15:31:44.058+0000
	Creator: stage_test_6

Consumer:
	Name: sam_org
	UUID: ba5ac769-207e-421c-bfd2-a23c767114af
	Type: sam

Subscription:
	Name: RHN Monitoring (Up to 1 guest)
	Quantity: 1
	Created: 2013-02-21T15:31:13.000+0000
	Start Date: 2012-12-31T05:00:00.000+0000
	End Date: 2013-12-31T04:59:59.000+0000
	Service Level: Layered
	Service Type: L1-L3
	Architectures: 
	SKU: RH1569626
	Contract: 
	Order: 
	Account: 5206743
	Entitlement File: export/entitlements/8a99f9833cf86efc013cfd613be066cb.json
	Certificate File: export/entitlement_certificates/2414805806930829936.pem
	Certificate Version: 1.0
	Provided Products:
	Content Sets:

"""


def _build_valid_manifest():

    zip_file_object1 = StringIO()
    archive1 = ZipExtractAll(zip_file_object1, "w", compression=zipfile.ZIP_STORED)
    archive1.writestr("signature", "dummy")

    zip_file_object2 = StringIO()
    archive2 = ZipExtractAll(zip_file_object2, "w", compression=zipfile.ZIP_STORED)
    archive2.writestr("export/consumer.json", 
            """{"uuid":"ba5ac769-207e-421c-bfd2-a23c767114af","""
            """"name":"sam_org","type":{"id":"5","label":"sam","manifest":true}}""")
        
    archive2.writestr("export/meta.json",
            """{"version":"0.7.13.13-1","created":"2013-02-21T15:31:44.058+0000","""
            """"principalName":"stage_test_6","webAppPrefix":"""
            """"access.stage.redhat.com/management/distributors/"}""")

    archive2.writestr("export/entitlements/8a99f9833cf86efc013cfd613be066cb.json",
            """{"created":"2013-02-21T15:31:13.000+0000","updated":"2013-02-21T15:31:13.000+0000","id":"8a99f9833cf86efc013cfd613be066cb","pool":{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-02-21T15:31:13.000+0000","id":"8a99f9833c01cc09013c037ace480344","owner":{"created":"2012-10-23T05:05:02.000+0000","updated":"2012-10-23T05:05:02.000+0000","parentOwner":null,"id":"8a99f9833a7a39f2013a8c0277dd7242","key":"6752568","displayName":"6752568","contentPrefix":null,"defaultServiceLevel":null,"upstreamUuid":null,"href":"/owners/6752568"},"activeSubscription":true,"subscriptionId":"2677371","subscriptionSubKey":"master","sourceEntitlement":null,"quantity":100,"startDate":"2012-12-31T05:00:00.000+0000","endDate":"2013-12-31T04:59:59.000+0000","productId":"RH1569626","providedProducts":[],"attributes":[],"productAttributes":[{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace480345","name":"support_type","value":"L1-L3","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace490346","name":"name","value":"RHN Monitoring (Up to 1 guest)","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace490347","name":"variant","value":"Smart Management","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace490348","name":"type","value":"MKT","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace490349","name":"support_level","value":"Layered","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace49034a","name":"product_family","value":"Red Hat Applications","productId":"RH1569626"},"""
"""{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace49034b","name":"support_level_exempt","value":"true","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace49034c","name":"description","value":"Red Hat Applications","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace49034e","name":"option_code","value":"0","productId":"RH1569626"},{"created":"2013-01-04T02:54:05.000+0000","updated":"2013-01-04T02:54:05.000+0000","id":"8a99f9833c01cc09013c037ace49034d","name":"subtype","value":"Layered","productId":"RH1569626"}],"restrictedToUsername":null,"contractNumber":null,"accountNumber":"5206743","consumed":1,"exported":1,"productName":"RHN Monitoring (Up to 1 guest)","href":"/pools/8a99f9833c01cc09013c037ace480344"},"startDate":"2012-12-31T05:00:00.000+0000","endDate":"2013-12-31T04:59:59.000+0000","certificates":[{"created":"2013-02-21T15:31:14.000+0000","updated":"2013-02-21T15:31:14.000+0000","key":"-----BEGIN RSA PRIVATE KEY-----"""
"""MIIEowIBAAKCAQEAox/RWlLuCi+6L84tdDx4CDEN9J2S1BzuoKdW6CLbQxLMJ/YW"""
"""miNX+Z8ox9ucCjA9aLrpkB+JH4lr7/dBlyPMJP5H6gQ9kMz/Y75lvl98E9Gh/09E"""
"""bjAu2ZkTmLB+IV/xPDZVHfugRnCy7sV1ElTkklYtGpfDTZ97eIhcSiLaLG1OT2rn"""
"""1DqMDYF5YLFkk2Wr7DK619gIGMY6XW7uBzIj+xmOYn2R4m5PAnNhFRJ8MdHfjTwg"""
"""EkA9w8r/KcqydsJ6/xCZOBBZlLHq0+CF3pbR9fuN+sGBL43BU+0Kd2MqPF64JTVa"""
"""Bkz2TZta+KUAHVhDKmGDEtuWnlcenOyJXpOg5QIDAQABAoIBAQCQUxZnU/hICvIw"""
"""WbrdnKKWnNA8HS5LfU2j1mqN+EkGjxsSQCi/N4Ye1TK/oQ3t9cBfaQA9A6nOvUdC"""
"""iQD/OCzmjhQSeK3/72AGX+6lANZGsrMhsIBa/UZ2P3mXHpB59uj43Rlx7a9go1Ws"""
"""7AcosPOKhbRiUuP5SaF0gzEkZrGhm6p4IJSEvWOmupBw2z21bnjyrlg0YQ+uBPFI"""
"""xmalD7do4Yw99ef3DoCyL8iEehv/N2McPP61tsToxwpLqw2Q4ELxtbxAkDVUXu9q"""
"""4RIbNm+OUcZZB46NxW/sk6nX/9LBlRG/1S8oTO4G6f2AK98ltWxNm/0BoV/KkxpN"""
"""eCI07/ABAoGBANE/ITxTtnrRlpvpn0qvOWCr/HIS8xurTk5vTnwHIys4vvwv23p7"""
"""nc3DuaLYIeqs0sujJaBY6mZ8QnAnMO4UUozHksFx+CTs6Dx/RqeF/vJoOb+YvmcM"""
"""3QrGZD+nCUHrBOVRfWGBttvqDh1rObOEXlWzWsim4Doo27IwhtwAYevdAoGBAMeS"""
"""f92iD8Gszu46IJa1o1Rt0DtV4KrOlAoahoXewkWl/M8Xf3OZt60J9IoEIiffDDTj"""
"""KijBAsq1HT4dfa6lM6hYTQocySIgomNolw5l1f0znUO9N8QklHeahCwaw2V8aCYX"""
"""FCkhJGpEFNmfUgNWM32OuYrSIn1TEUzqVn2y4dypAoGAbDUMV+kmjb8C9p/K21Fg"""
"""B6kJBGjeRWnCNfeDi8oZGsneogWRp3ZztavIvPiuGXDEFcDJvXEdzl/l75+kwwnJ"""
"""Yrn2H4lzfIzy0A41mH5HyE2zx2wS0rGpQWA1CWG0/NyvjHMmtpzg1jrkj7wae8Yx"""
"""DnqQsQDzJcBpVG2Z3/1mphUCgYABiB9RHShPzTq9W1basUQyprEdc3hI91LtjOyR"""
"""ZHdLP43kLQL+aSSewF/PG18DvVODqGavb2PNGHzD+Ef5qizuUtcsh7IHgAafCrN2"""
"""GdP9oILJfU9LQxicnmP7Tq1HPyAxgqXV9vonkqQyU2W2vtegVBMafKhlG9kbJQVK"""
"""66+OGQKBgEBpo/BpYXNifIuxZqX4CBpBNSez4p04T1rVN4epCpE8+Lc8zZLLWd4Y"""
"""SdHfu5F7EFQ+KERyvi4v31HQkdT99+4D7PZq43DzfosKCseaGT12GxWxlVJP5MZR"""
"""PNe6469nI+tuqa+9+Vbe6eUsvAePcb7Mbc3JCzzzHJLvJsMEcJgo"""
"""-----END RSA PRIVATE KEY-----"""
"""","cert":"-----BEGIN CERTIFICATE-----"""
"""MIIHJDCCBQygAwIBAgIIIYMdFlOponAwDQYJKoZIhvcNAQEFBQAwgaQxCzAJBgNV"""
"""BAYTAlVTMRcwFQYDVQQIDA5Ob3J0aCBDYXJvbGluYTEWMBQGA1UECgwNUmVkIEhh"""
"""dCwgSW5jLjEYMBYGA1UECwwPUmVkIEhhdCBOZXR3b3JrMSQwIgYDVQQDDBtSZWQg"""
"""SGF0IENhbmRsZXBpbiBBdXRob3JpdHkxJDAiBgkqhkiG9w0BCQEWFWNhLXN1cHBv"""
"""cnRAcmVkaGF0LmNvbTAeFw0xMjEyMzEwNTAwMDBaFw0xMzEyMzEwNDU5NTlaMCsx"""
"""KTAnBgNVBAMTIDhhOTlmOTgzM2NmODZlZmMwMTNjZmQ2MTNiZTA2NmNiMIIBIjAN"""
"""BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAox/RWlLuCi+6L84tdDx4CDEN9J2S"""
"""1BzuoKdW6CLbQxLMJ/YWmiNX+Z8ox9ucCjA9aLrpkB+JH4lr7/dBlyPMJP5H6gQ9"""
"""kMz/Y75lvl98E9Gh/09EbjAu2ZkTmLB+IV/xPDZVHfugRnCy7sV1ElTkklYtGpfD"""
"""TZ97eIhcSiLaLG1OT2rn1DqMDYF5YLFkk2Wr7DK619gIGMY6XW7uBzIj+xmOYn2R"""
"""4m5PAnNhFRJ8MdHfjTwgEkA9w8r/KcqydsJ6/xCZOBBZlLHq0+CF3pbR9fuN+sGB"""
"""L43BU+0Kd2MqPF64JTVaBkz2TZta+KUAHVhDKmGDEtuWnlcenOyJXpOg5QIDAQAB"""
"""o4IC0DCCAswwEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDCB3gYDVR0j"""
"""BIHWMIHTgBR3LqXNNw2o4dPqYcVWZ0PokcdtHKGBt6SBtDCBsTELMAkGA1UEBhMC"""
"""VVMxFzAVBgNVBAgMDk5vcnRoIENhcm9saW5hMRYwFAYDVQQKDA1SZWQgSGF0LCBJ"""
"""bmMuMRgwFgYDVQQLDA9SZWQgSGF0IE5ldHdvcmsxMTAvBgNVBAMMKFJlZCBIYXQg"""
"""RW50aXRsZW1lbnQgT3BlcmF0aW9ucyBBdXRob3JpdHkxJDAiBgkqhkiG9w0BCQEW"""
"""FWNhLXN1cHBvcnRAcmVkaGF0LmNvbYIBPzAdBgNVHQ4EFgQUH4sIAAAAAAAAAAMAAAAAAAAAAAAwEwYDVR0lBAwwCgYIKwYBBQUHAwIwLgYKKwYBBAGSCAkEAQQgDB5SSE4gTW9uaXRvcmluZyAoVXAgdG8gMSBndWVzdCkwFwYKKwYBBAGSCAkEAgQJDAcyNjc3MzcxMBkGCisGAQQBkggJBAMECwwJUkgxNTY5NjI2MBMGCisGAQQBkggJBAUEBQwDMTAwMCQGCisGAQQBkggJBAYEFgwUMjAxMi0xMi0zMVQwNTowMDowMFowJAYKKwYBBAGSCAkEBwQWDBQyMDEzLTEyLTMxVDA0OjU5OjU5WjARBgorBgEEAZIICQQMBAMMATAwGAYKKwYBBAGSCAkECgQKDAgxMDAxNDcxMDAXBgorBgEEAZIICQQNBAkMBzUyMDY3NDMwEQYKKwYBBAGSCAkEDgQDDAEwMBcGCisGAQQBkggJBA8ECQwHTGF5ZXJlZDAVBgorBgEEAZIICQQQBAcMBUwxLUwzMBEGCisGAQQBkggJBAsEAwwBMTA0BgorBgEEAZIICQUBBCYMJGJhNWFjNzY5LTIwN2UtNDIxYy1iZmQyLWEyM2M3NjcxMTRhZjANBgkqhkiG9w0BAQUFAAOCAgEAr3exvJrshLkavm8ZLij7fazB7rTL2cFGzDINHsGIDXWkwFFchwQ/FmyB86fcqjfTescb2AmQ9zKAnOgD3qC4WtWD9YkRTN3aVIE6TV9wcMIX3ZyP1Ix4tExGGjdcwGs3cY/oxYWDmBjLeYptLPM70LABMPIycRUU4eCVPl6QYUG+diKZ4ZnB+sdqQ91DFg0E9LXPxnv5iawzEyEAl+2JfKQXA8y55r5Nh5MdIiCNpnZagmiXkjG2zigldYwgDisvEcoNgRLDTZq/P1DcwhqDaGYOZa5rHp3dTsA10tqT7B193uxqW0hyCSmGE6Li9UZAahU7Yp0+AvQ8BvtNsNIB1GBXrA1bqe+fUZ8kofO6tEHDoP3E5YDY9lNYslntOIF1DOZbVVjj2Do0qYryTUUWMx/BzGtk60QQNOJpQoVRt41HxZr5pYzYD5mn5GNlk1M7BXJt8ZAHXzPhZM7jF8HzjzkmirZKEDn+VP5bxNMWOm5YFtn1M7rux45VZ2Vj7mJ1yczNgPfP0ZfIfI+Iy9Ldx5Amm8nwHB5LbdD4O+ZBZKHLPWkl/XNRjfO6ul+l2RSMQNyh9J15DD4vovewQ0dp4edgcDl6VWOcm9mMQyolp9QK0IeK2bGIE9ELQig2Feq94wI3lwjQ9jiDvFhqGUsX3r0tUaIvgYO6vuJ/meoatbc="""
"""-----END CERTIFICATE-----","id":"8a99f9833cf86efc013cfd613f2266cc","serial":{"created":"2013-02-21T15:31:14.000+0000","updated":"2013-02-21T15:31:14.000+0000","id":2414805806930829936,"revoked":false,"collected":false,"expiration":"2013-12-31T04:59:59.000+0000","serial":2414805806930829936}}],"quantity":1,"accountNumber":"5206743","contractNumber":null,"href":"/entitlements/8a99f9833cf86efc013cfd613be066cb"}""")

    archive2.writestr("export/entitlement_certificates/2414805806930829936.pem",
            """-----BEGIN CERTIFICATE-----
MIIHJDCCBQygAwIBAgIIIYMdFlOponAwDQYJKoZIhvcNAQEFBQAwgaQxCzAJBgNV
BAYTAlVTMRcwFQYDVQQIDA5Ob3J0aCBDYXJvbGluYTEWMBQGA1UECgwNUmVkIEhh
dCwgSW5jLjEYMBYGA1UECwwPUmVkIEhhdCBOZXR3b3JrMSQwIgYDVQQDDBtSZWQg
SGF0IENhbmRsZXBpbiBBdXRob3JpdHkxJDAiBgkqhkiG9w0BCQEWFWNhLXN1cHBv
cnRAcmVkaGF0LmNvbTAeFw0xMjEyMzEwNTAwMDBaFw0xMzEyMzEwNDU5NTlaMCsx
KTAnBgNVBAMTIDhhOTlmOTgzM2NmODZlZmMwMTNjZmQ2MTNiZTA2NmNiMIIBIjAN
BgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAox/RWlLuCi+6L84tdDx4CDEN9J2S
1BzuoKdW6CLbQxLMJ/YWmiNX+Z8ox9ucCjA9aLrpkB+JH4lr7/dBlyPMJP5H6gQ9
kMz/Y75lvl98E9Gh/09EbjAu2ZkTmLB+IV/xPDZVHfugRnCy7sV1ElTkklYtGpfD
TZ97eIhcSiLaLG1OT2rn1DqMDYF5YLFkk2Wr7DK619gIGMY6XW7uBzIj+xmOYn2R
4m5PAnNhFRJ8MdHfjTwgEkA9w8r/KcqydsJ6/xCZOBBZlLHq0+CF3pbR9fuN+sGB
L43BU+0Kd2MqPF64JTVaBkz2TZta+KUAHVhDKmGDEtuWnlcenOyJXpOg5QIDAQAB
o4IC0DCCAswwEQYJYIZIAYb4QgEBBAQDAgWgMAsGA1UdDwQEAwIEsDCB3gYDVR0j
BIHWMIHTgBR3LqXNNw2o4dPqYcVWZ0PokcdtHKGBt6SBtDCBsTELMAkGA1UEBhMC
VVMxFzAVBgNVBAgMDk5vcnRoIENhcm9saW5hMRYwFAYDVQQKDA1SZWQgSGF0LCBJ
bmMuMRgwFgYDVQQLDA9SZWQgSGF0IE5ldHdvcmsxMTAvBgNVBAMMKFJlZCBIYXQg
RW50aXRsZW1lbnQgT3BlcmF0aW9ucyBBdXRob3JpdHkxJDAiBgkqhkiG9w0BCQEW
FWNhLXN1cHBvcnRAcmVkaGF0LmNvbYIBPzAdBgNVHQ4EFgQUH4sIAAAAAAAAAAMA
AAAAAAAAAAAwEwYDVR0lBAwwCgYIKwYBBQUHAwIwLgYKKwYBBAGSCAkEAQQgDB5S
SE4gTW9uaXRvcmluZyAoVXAgdG8gMSBndWVzdCkwFwYKKwYBBAGSCAkEAgQJDAcy
Njc3MzcxMBkGCisGAQQBkggJBAMECwwJUkgxNTY5NjI2MBMGCisGAQQBkggJBAUE
BQwDMTAwMCQGCisGAQQBkggJBAYEFgwUMjAxMi0xMi0zMVQwNTowMDowMFowJAYK
KwYBBAGSCAkEBwQWDBQyMDEzLTEyLTMxVDA0OjU5OjU5WjARBgorBgEEAZIICQQM
BAMMATAwGAYKKwYBBAGSCAkECgQKDAgxMDAxNDcxMDAXBgorBgEEAZIICQQNBAkM
BzUyMDY3NDMwEQYKKwYBBAGSCAkEDgQDDAEwMBcGCisGAQQBkggJBA8ECQwHTGF5
ZXJlZDAVBgorBgEEAZIICQQQBAcMBUwxLUwzMBEGCisGAQQBkggJBAsEAwwBMTA0
BgorBgEEAZIICQUBBCYMJGJhNWFjNzY5LTIwN2UtNDIxYy1iZmQyLWEyM2M3Njcx
MTRhZjANBgkqhkiG9w0BAQUFAAOCAgEAr3exvJrshLkavm8ZLij7fazB7rTL2cFG
zDINHsGIDXWkwFFchwQ/FmyB86fcqjfTescb2AmQ9zKAnOgD3qC4WtWD9YkRTN3a
VIE6TV9wcMIX3ZyP1Ix4tExGGjdcwGs3cY/oxYWDmBjLeYptLPM70LABMPIycRUU
4eCVPl6QYUG+diKZ4ZnB+sdqQ91DFg0E9LXPxnv5iawzEyEAl+2JfKQXA8y55r5N
h5MdIiCNpnZagmiXkjG2zigldYwgDisvEcoNgRLDTZq/P1DcwhqDaGYOZa5rHp3d
TsA10tqT7B193uxqW0hyCSmGE6Li9UZAahU7Yp0+AvQ8BvtNsNIB1GBXrA1bqe+f
UZ8kofO6tEHDoP3E5YDY9lNYslntOIF1DOZbVVjj2Do0qYryTUUWMx/BzGtk60QQ
NOJpQoVRt41HxZr5pYzYD5mn5GNlk1M7BXJt8ZAHXzPhZM7jF8HzjzkmirZKEDn+
VP5bxNMWOm5YFtn1M7rux45VZ2Vj7mJ1yczNgPfP0ZfIfI+Iy9Ldx5Amm8nwHB5L
bdD4O+ZBZKHLPWkl/XNRjfO6ul+l2RSMQNyh9J15DD4vovewQ0dp4edgcDl6VWOc
m9mMQyolp9QK0IeK2bGIE9ELQig2Feq94wI3lwjQ9jiDvFhqGUsX3r0tUaIvgYO6
vuJ/meoatbc=
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAox/RWlLuCi+6L84tdDx4CDEN9J2S1BzuoKdW6CLbQxLMJ/YW
miNX+Z8ox9ucCjA9aLrpkB+JH4lr7/dBlyPMJP5H6gQ9kMz/Y75lvl98E9Gh/09E
bjAu2ZkTmLB+IV/xPDZVHfugRnCy7sV1ElTkklYtGpfDTZ97eIhcSiLaLG1OT2rn
1DqMDYF5YLFkk2Wr7DK619gIGMY6XW7uBzIj+xmOYn2R4m5PAnNhFRJ8MdHfjTwg
EkA9w8r/KcqydsJ6/xCZOBBZlLHq0+CF3pbR9fuN+sGBL43BU+0Kd2MqPF64JTVa
Bkz2TZta+KUAHVhDKmGDEtuWnlcenOyJXpOg5QIDAQABAoIBAQCQUxZnU/hICvIw
WbrdnKKWnNA8HS5LfU2j1mqN+EkGjxsSQCi/N4Ye1TK/oQ3t9cBfaQA9A6nOvUdC
iQD/OCzmjhQSeK3/72AGX+6lANZGsrMhsIBa/UZ2P3mXHpB59uj43Rlx7a9go1Ws
7AcosPOKhbRiUuP5SaF0gzEkZrGhm6p4IJSEvWOmupBw2z21bnjyrlg0YQ+uBPFI
xmalD7do4Yw99ef3DoCyL8iEehv/N2McPP61tsToxwpLqw2Q4ELxtbxAkDVUXu9q
4RIbNm+OUcZZB46NxW/sk6nX/9LBlRG/1S8oTO4G6f2AK98ltWxNm/0BoV/KkxpN
eCI07/ABAoGBANE/ITxTtnrRlpvpn0qvOWCr/HIS8xurTk5vTnwHIys4vvwv23p7
nc3DuaLYIeqs0sujJaBY6mZ8QnAnMO4UUozHksFx+CTs6Dx/RqeF/vJoOb+YvmcM
3QrGZD+nCUHrBOVRfWGBttvqDh1rObOEXlWzWsim4Doo27IwhtwAYevdAoGBAMeS
f92iD8Gszu46IJa1o1Rt0DtV4KrOlAoahoXewkWl/M8Xf3OZt60J9IoEIiffDDTj
KijBAsq1HT4dfa6lM6hYTQocySIgomNolw5l1f0znUO9N8QklHeahCwaw2V8aCYX
FCkhJGpEFNmfUgNWM32OuYrSIn1TEUzqVn2y4dypAoGAbDUMV+kmjb8C9p/K21Fg
B6kJBGjeRWnCNfeDi8oZGsneogWRp3ZztavIvPiuGXDEFcDJvXEdzl/l75+kwwnJ
Yrn2H4lzfIzy0A41mH5HyE2zx2wS0rGpQWA1CWG0/NyvjHMmtpzg1jrkj7wae8Yx
DnqQsQDzJcBpVG2Z3/1mphUCgYABiB9RHShPzTq9W1basUQyprEdc3hI91LtjOyR
ZHdLP43kLQL+aSSewF/PG18DvVODqGavb2PNGHzD+Ef5qizuUtcsh7IHgAafCrN2
GdP9oILJfU9LQxicnmP7Tq1HPyAxgqXV9vonkqQyU2W2vtegVBMafKhlG9kbJQVK
66+OGQKBgEBpo/BpYXNifIuxZqX4CBpBNSez4p04T1rVN4epCpE8+Lc8zZLLWd4Y
SdHfu5F7EFQ+KERyvi4v31HQkdT99+4D7PZq43DzfosKCseaGT12GxWxlVJP5MZR
PNe6469nI+tuqa+9+Vbe6eUsvAePcb7Mbc3JCzzzHJLvJsMEcJgo
-----END RSA PRIVATE KEY-----""")

    archive2.close()

    archive1.writestr("consumer_export.zip", zip_file_object2.getvalue())
    archive1.close()
    return zip_file_object1
