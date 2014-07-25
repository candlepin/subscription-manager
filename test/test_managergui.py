import unittest

from fixture import SubManFixture
import mock

import stubs
from subscription_manager.gui import managergui, registergui
from subscription_manager.injection import provide, IDENTITY, \
        PRODUCT_DATE_RANGE_CALCULATOR, PROD_DIR


class TestManagerGuiMainWindow(SubManFixture):
    def setUp(self):
        super(TestManagerGuiMainWindow, self).setUp()
        id_mock = mock.Mock()
        id_mock.name = "John Q Consumer"
        id_mock.uuid = "211211381984"
        id_mock.exists_and_valid = mock.Mock(return_value=True)
        provide(IDENTITY, id_mock)

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
