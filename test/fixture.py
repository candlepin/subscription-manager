import unittest

from mock import Mock, NonCallableMock
import subscription_manager.injection as inj
import stubs


class SubManFixture(unittest.TestCase):
    """
    Can be extended by any subscription manager test case to make
    sure nothing on the actual system is read/touched, and appropriate
    mocks/stubs are in place.
    """
    def setUp(self):
        # By default mock that we are registered. Individual test cases
        # can override if they are testing disconnected scenario.
        id_mock = Mock()
        id_mock.exists_and_valid = Mock(return_value=True)

        # Don't really care about date ranges here:
        self.mock_calc = NonCallableMock()
        self.mock_calc.calculate.return_value = None

        inj.FEATURES.provide(inj.IDENTITY, id_mock)
        inj.FEATURES.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR, self.mock_calc)

        # By default set up an empty stub entitlement and product dir.
        # Tests need to modify or create their own but nothing should hit
        # the system.
        self.ent_dir = stubs.StubEntitlementDirectory()
        inj.FEATURES.provide(inj.ENT_DIR, self.ent_dir)
        self.prod_dir = stubs.StubProductDirectory()
        inj.FEATURES.provide(inj.PROD_DIR, self.prod_dir)
