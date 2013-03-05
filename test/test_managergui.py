import unittest

import rhsm_display
rhsm_display.set_display()

from fixture import SubManFixture
import mock

import stubs
from subscription_manager.gui import managergui, registergui
from subscription_manager.injection import FEATURES, IDENTITY, CERT_SORTER
from fixture import SubManFixture


class TestManagerGuiMainWindow(SubManFixture):
    def setUp(self):
        super(TestManagerGuiMainWindow, self).setUp()
        id_mock = mock.Mock()
        id_mock.name = "John Q Consumer"
        id_mock.uuid = "211211381984"
        id_mock.exists_and_valid = mock.Mock(return_value=True)
        FEATURES.provide(IDENTITY, id_mock)

    def test_main_window(self):

        managergui.Backend = stubs.StubBackend
        managergui.Facts = stubs.StubFacts()

        stub_sorter = stubs.StubCertSorter(stubs.StubProductDirectory([]))
        FEATURES.provide(CERT_SORTER, stub_sorter)

        managergui.MainWindow(backend=stubs.StubBackend(), facts=stubs.StubFacts(),
                              ent_dir=stubs.StubCertificateDirectory([]),
                              prod_dir=stubs.StubProductDirectory([]))


class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        registergui.RegisterScreen(stubs.StubBackend())

    def test_register_screen_register(self):
        rs = registergui.RegisterScreen(stubs.StubBackend())
        rs.register()
