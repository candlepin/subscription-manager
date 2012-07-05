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

    # TODO: test exception when cert major version is newer than we can handle
