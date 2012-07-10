import unittest
import stubs
import modelhelpers
from subscription_manager.gui import autobind


class AutobindControllerBase(unittest.TestCase):
    def setUp(self):
        self.stub_backend = stubs.StubBackend()
        self.stub_consumer = stubs.StubConsumer()
        self.stub_facts = stubs.StubFacts()

        self.stub_backend.uep.getConsumer = self._getConsumerData

        self.stub_product = stubs.StubProduct("rhel-6")
        self.stub_pool = modelhelpers.create_pool(product_id=self.stub_product.id,
                                                  product_name=self.stub_product.id)
        self.stub_backend.uep.stub_pool = self.stub_pool

        self.stub_backend.product_dir = stubs.StubCertificateDirectory([stubs.StubProductCertificate(self.stub_product)])
        self.stub_backend.entitlement_dir = stubs.StubEntitlementDirectory([])
        self.stub_backend.uep.dryRunBind = self._dryRunBind

    def _dryRunBind(self, uuid, sla):
        return [{'pool': self.stub_pool, 'quantity': 1}]

    def _dryRunBindEmpty(self, uuid, sla):
        return []

    @staticmethod
    def _getConsumerData(cls):
        return  {'releaseVer': {'is': 1, 'releaseVer': '123123'},
                 'serviceLevel': "",
                 'owner': {'key': 'admin'}}

    @staticmethod
    def _getConsumerDataPro(cls):
        return  {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro",
                 'owner': {'key': 'admin'}}

    def _get_autobind_controller(self):
        autobind_controller = autobind.AutobindController(self.stub_backend,
                                                          self.stub_consumer,
                                                          self.stub_facts)
        return autobind_controller


class TestAutobindWizard(AutobindControllerBase):
    def setUp(self):
        AutobindControllerBase.setUp(self)
        self.autobind_wizard = autobind.AutobindWizard(self.stub_backend,
                                                       self.stub_consumer,
                                                       self.stub_facts)

        self.autobind_wizard.show()

    def test_show_confirm_subs(self):
        self.autobind_wizard.show_confirm_subs("Pro")

    def test_show_select_sla(self):
        self.autobind_wizard.show_select_sla()

    def test_previous_screen(self):
        self.assertRaises(RuntimeError,
                          self.autobind_wizard.previous_screen)


class TestConfirmSubscriptionScreen(AutobindControllerBase):
    def test_load(self):
        autobind_controller = self._get_autobind_controller()
        css = autobind.ConfirmSubscriptionsScreen(autobind_controller)
        self.assertTrue(css is not None)

    def test_load_data(self):
        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        css = autobind.ConfirmSubscriptionsScreen(autobind_controller)
        css.load_data(autobind_controller.suitable_slas['Pro'])


class TestAutobindController(AutobindControllerBase):
    def test_autobind_init(self):
        autobind_controller = self._get_autobind_controller()
        self.assertTrue(autobind_controller is not None)

    def test_autobind_no_installed_product(self):
        self.stub_backend.product_dir = stubs.StubCertificateDirectory([])
        autobind_controller = self._get_autobind_controller()
        self.assertRaises(autobind.NoProductsException,
                          autobind_controller.load)

    def test_autobind_all_products_covered(self):
        self.stub_backend.entitlement_dir = stubs.StubEntitlementDirectory([stubs.StubEntitlementCertificate(self.stub_product)])
        autobind_controller = self._get_autobind_controller()
        self.assertRaises(autobind.AllProductsCoveredException,
                          autobind_controller.load)

    def test_autobind_current_sla_matches(self):
        self.stub_backend.uep.getConsumer = self._getConsumerDataPro

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        self.assertTrue('Pro' in autobind_controller.suitable_slas)

    def test_autobind_dry_run_no_matches(self):
        self.stub_backend.uep.dryRunBind = self._dryRunBindEmpty
        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        self.assertEquals(autobind_controller.suitable_slas, {})

    def test_autobind_dry_run_no_matches_current_sla_set(self):
        self.stub_backend.uep.getConsumer = self._getConsumerDataPro
        self.stub_backend.uep.dryRunBind = self._dryRunBindEmpty

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        self.assertEquals(len(autobind_controller.suitable_slas), 1)
        self.assertTrue('Pro' in autobind_controller.suitable_slas)

    def test_autobind_current_sla_no_match(self):

        def getConsumerData(self):
            return  {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                     'serviceLevel': "NotReallyAServiceLevel",
                     'owner': {'key': 'admin'}}

        self.stub_backend.uep.getConsumer = getConsumerData
        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        self.assertEquals(autobind_controller.selected_sla, None)

    def test_autobind_load(self):
        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()

    def test_autobind_load_provided_products(self):
        self.stub_product = stubs.StubProduct("some_random_product")
        self.stub_pool = modelhelpers.create_pool(product_id=self.stub_product.id,
                                                  product_name=self.stub_product.name,
                                                  provided_products=['rhel-6'])
        self.stub_backend.uep.stub_pool = self.stub_pool

        self.stub_installed_product = stubs.StubProduct("rhel-6")
        self.stub_backend.product_dir = stubs.StubCertificateDirectory([stubs.StubProductCertificate(self.stub_installed_product)])

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        self.assertTrue('Pro' in autobind_controller.suitable_slas)

    def test_autobind_no_service_level(self):

        def getConsumerData(self):
            return  {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                     'owner': {'key': 'admin'}}

        self.stub_backend.uep.getConsumer = getConsumerData
        autobind_controller = self._get_autobind_controller()
        self.assertRaises(autobind.ServiceLevelNotSupportedException,
                          autobind_controller.load)

    def test_autobind_can_add_more_subs(self):
        # in this case, we don't set a current sla, so
        # we shouldn't be able to add more subs

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        can_add_more_subs = autobind_controller.can_add_more_subs()
        self.assertFalse(can_add_more_subs)

    def test_autobind_can_add_more_subs_current_sla(self):
        # in this case, we don't set a current sla, so
        # we shouldn't be able to add more subs
        self.stub_backend.uep.getConsumer = self._getConsumerDataPro

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        can_add_more_subs = autobind_controller.can_add_more_subs()
        self.assertTrue(can_add_more_subs)

    # can we add more subs if don't match any sla's except the
    # the current one, that has no pools
    def test_autobind_can_add_more_subs_current_sla_no_matches(self):
        self.stub_backend.uep.getConsumer = self._getConsumerDataPro
        self.stub_backend.uep.dryRunBind = self._dryRunBindEmpty

        autobind_controller = self._get_autobind_controller()
        autobind_controller.load()
        can_add_more_subs = autobind_controller.can_add_more_subs()
        self.assertFalse(can_add_more_subs)
