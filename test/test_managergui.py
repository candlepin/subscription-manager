import unittest

from fixture import SubManFixture
import mock

import stubs
from subscription_manager.gui import managergui, registergui
from subscription_manager.injection import provide, \
        PRODUCT_DATE_RANGE_CALCULATOR, PROD_DIR


class TestManagerGuiMainWindow(SubManFixture):
    def test_main_window(self):

        managergui.Backend = stubs.StubBackend
        managergui.Facts = stubs.StubFacts()

        provide(PROD_DIR, stubs.StubProductDirectory([]))
        provide(PRODUCT_DATE_RANGE_CALCULATOR, mock.Mock())

        managergui.MainWindow(backend=stubs.StubBackend(), facts=stubs.StubFacts(),
                              ent_dir=stubs.StubCertificateDirectory([]),
                              prod_dir=stubs.StubProductDirectory([]))


class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        registergui.RegisterScreen(stubs.StubBackend())

    def test_register_screen_register(self):
        rs = registergui.RegisterScreen(stubs.StubBackend())
        rs.register()
