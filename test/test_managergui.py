import unittest

from subscription_manager.gui import managergui, registergui
import stubs


class StubBackend:
    def __init__(self):
        pass

    def monitor_certs(self, callback):
        pass

    def monitor_identity(self, callback):
        pass


class StubConsumer:
    def __init__(self):
        self.uuid = None

    def reload(self):
        pass

class StubFacts:
    def __init__(self):
        pass

    def get_facts(self):
        return {}


class TestManagerGuiMainWindow(unittest.TestCase):
    def test_main_window(self):
        managergui.ConsumerIdentity = stubs.StubConsumerIdentity
        managergui.Backend = StubBackend
        managergui.Consumer = StubConsumer
        managergui.Facts = StubFacts
        managergui.MainWindow()


class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        registergui.RegisterScreen(StubBackend(), StubConsumer())

    def test_register_screen_register(self):
        rs = registergui.RegisterScreen(StubBackend(), StubConsumer())
        rs.register(testing=True)
