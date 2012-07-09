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
from rhsm.certificate2 import *


class ProductCert10Tests(unittest.TestCase):

    def setUp(self):
        self.factory = CertFactory()

    def test_factory_method_on_product_cert(self):
        cert = self.factory.create_from_pem(certdata.PRODUCT_CERT_V1_0)
        self.assertEquals("1.0", str(cert.version))
        self.assertTrue(isinstance(cert, ProductCertificate1))

    def test_factory_method_on_ent_cert(self):
        cert = self.factory.create_from_pem(certdata.ENTITLEMENT_CERT_V1_0)
        self.assertEquals("1.0", str(cert.version))
        self.assertTrue(isinstance(cert, EntitlementCertificate1))
        self.assertEquals(666017019617507769L, cert.serial)
        self.assertEquals(2012, cert.start.year)
        self.assertEquals(2013, cert.end.year)
        self.assertEquals("Awesome OS for x86_64", cert.order.name)

    def test_is_valid(self):
        cert = self.factory.create_from_pem(certdata.ENTITLEMENT_CERT_V1_0)
        self.assertTrue(cert.is_valid(on_date=datetime(2012, 12, 1)))
        self.assertFalse(cert.is_valid(on_date=datetime(2014, 12, 1)))

    # TODO: test exception when cert major version is newer than we can handle
