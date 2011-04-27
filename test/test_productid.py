import unittest
import tempfile
import datetime

from subscription_manager import productid
from subscription_manager import certlib
from yum import YumBase

import stubs

class TestProductManager(unittest.TestCase):

    def setUp(self):
        self.db_dir = tempfile.mkdtemp()
        productid.DatabaseDirectory.PATH = self.db_dir
        self.pm = productid.ProductManager()
        entDir = certlib.EntitlementDirectory()
        stubCertDir = stubs.StubCertificateDirectory(entDir)
        cert1 = stubs.StubEntitlementCertificate(
            stubs.StubProduct('product1'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2050, 1, 1))
        cert2 = stubs.StubEntitlementCertificate(
            stubs.StubProduct('product2'),
            start_date=datetime.datetime(2010, 1, 1),
            end_date=datetime.datetime(2060, 1, 1))
        self.pm.pdir = stubs.StubProductDirectory([cert1, cert2])


    def test_get_active(self):
        self.pm.getActive(yb=YumBase())

    def test_get_enabled(self):
        self.pm.getEnabled(yb=YumBase())
        
    def test_update(self):
        self.pm.update(yb=YumBase())
