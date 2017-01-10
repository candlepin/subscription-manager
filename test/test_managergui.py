from fixture import SubManFixture
import mock

import stubs
from subscription_manager.gui import managergui, registergui
from subscription_manager.injection import provide, \
        PRODUCT_DATE_RANGE_CALCULATOR, PROD_DIR


class TestManagerGuiMainWindow(SubManFixture):
    def test_main_window(self):

        provide(PROD_DIR, stubs.StubProductDirectory([]))
        provide(PRODUCT_DATE_RANGE_CALCULATOR, mock.Mock())

        managergui.MainWindow(backend=stubs.StubBackend(),
                              ent_dir=stubs.StubCertificateDirectory([]),
                              prod_dir=stubs.StubProductDirectory([]))


class TestRegisterScreen(SubManFixture):
    def test_register_screen(self):
        registergui.RegisterDialog(stubs.StubBackend())

    def test_register_screen_register(self):
        rd = registergui.RegisterDialog(stubs.StubBackend())
        #rs.initialize()
        rd.show()
        rd.register_dialog.hide()
        #rs.cancel()
