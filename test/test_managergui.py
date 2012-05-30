import unittest

import stubs
from subscription_manager.gui import managergui, registergui


class StubConsumer:
    def __init__(self):
        self.uuid = None

    def reload(self):
        pass


class TestManagerGuiMainWindow(unittest.TestCase):
    def test_main_window(self):
        managergui.ConsumerIdentity = stubs.StubConsumerIdentity
        managergui.Backend = stubs.StubBackend
        managergui.Consumer = StubConsumer
        managergui.Facts = stubs.StubFacts()

        managergui.MainWindow(backend=stubs.StubBackend(), consumer=StubConsumer(),
                              facts=stubs.StubFacts(),
                              ent_dir=stubs.StubCertificateDirectory([]),
                              prod_dir=stubs.StubProductDirectory([]))


class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        registergui.RegisterScreen(stubs.StubBackend(), StubConsumer())

    def test_register_screen_register(self):
        rs = registergui.RegisterScreen(stubs.StubBackend(), StubConsumer())
        rs.register()
