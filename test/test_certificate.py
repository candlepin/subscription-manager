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

import time
import datetime
import unittest

import M2Crypto

import certificate

class StubOrder(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.end


def yesterday():
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    now = datetime.datetime.now()
    then = now - datetime.timedelta(days=1)
    return then.strftime(fmt)

class EntitlementCertificateTests(unittest.TestCase):

    def test_valid_order_date_gives_valid_cert(self):
        def getStubOrder():
            return StubOrder("2010-07-27T16:06:52Z",
                    "2011-07-26T20:00:00Z")

        cert = certificate.EntitlementCertificate()
        cert.getOrder = getStubOrder

        self.assertTrue(cert.valid())

    def test_expired_order_date_gives_invalid_cert(self):
        def getStubOrder():
            return StubOrder("2010-07-27T16:06:52Z",
                    yesterday())

        cert = certificate.EntitlementCertificate()
        cert.getOrder = getStubOrder

        self.assertFalse(cert.valid())

    def test_invalid_order_date_gives_valid_cert_with_grace(self):
        def getStubOrder():
            return StubOrder("2010-07-27T16:06:52Z",
                    yesterday())

        cert = certificate.EntitlementCertificate()
        cert.getOrder = getStubOrder

        begin = M2Crypto.ASN1.ASN1_UTCTIME()
        begin.set_time(long(time.time()) - 200)

        end = M2Crypto.ASN1.ASN1_UTCTIME()
        end.set_time(long(time.time()) + 1000)

        cert.x509.set_not_before(begin)
        cert.x509.set_not_after(end)

        self.assertTrue(cert.validWithGracePeriod())

    def test_invalid_x509_date_gives_invalid_cert_with_grace(self):
        def getStubOrder():
            return StubOrder("2010-07-27T16:06:52Z",
                    yesterday())

        cert = certificate.EntitlementCertificate()
        cert.getOrder = getStubOrder

        begin = M2Crypto.ASN1.ASN1_UTCTIME()
        begin.set_time(long(time.time()) - 200)

        end = M2Crypto.ASN1.ASN1_UTCTIME()
        end.set_time(long(time.time()) - 100)

        cert.x509.set_not_before(begin)
        cert.x509.set_not_after(end)

        self.assertFalse(cert.validWithGracePeriod())
