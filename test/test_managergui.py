import unittest

import rhsm_display
rhsm_display.set_display()

import stubs
from subscription_manager.gui import managergui, registergui, installedtab


class TestManagerGuiMainWindow(unittest.TestCase):
    def test_main_window(self):
        managergui.ConsumerIdentity = stubs.StubConsumerIdentity
        installedtab.ConsumerIdentity = stubs.StubConsumerIdentity
        managergui.Backend = stubs.StubBackend
        managergui.Consumer = stubs.StubConsumer
        managergui.Facts = stubs.StubFacts()

        managergui.MainWindow(backend=stubs.StubBackend(), consumer=stubs.StubConsumer(),
                              facts=stubs.StubFacts(),
                              ent_dir=stubs.StubCertificateDirectory([]),
                              prod_dir=stubs.StubProductDirectory([]))


class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        registergui.RegisterScreen(stubs.StubBackend(), stubs.StubConsumer())

    def test_register_screen_register(self):
        rs = registergui.RegisterScreen(stubs.StubBackend(), stubs.StubConsumer())
        rs.register()
