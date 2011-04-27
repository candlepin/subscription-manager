import unittest

from subscription_manager.gui import managergui
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

class TestManagerGuiMainWindow(unittest.TestCase):
    def test_main_window(self):
        managergui.ConsumerIdentity = stubs.StubConsumerIdentity
        managergui.Backend = StubBackend
        managergui.Consumer = StubConsumer
        mw = managergui.MainWindow()

class TestRegisterScreen(unittest.TestCase):
    def test_register_screen(self):
        rs = managergui.RegisterScreen(StubBackend(), StubConsumer())


    def test_register_screen_register(self):
        rs = managergui.RegisterScreen(StubBackend(), StubConsumer())
        result = rs.register(testing=True)
