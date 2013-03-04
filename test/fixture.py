import unittest

from mock import Mock, NonCallableMock
from subscription_manager.injection import FEATURES, IDENTITY, \
        PRODUCT_DATE_RANGE_CALCULATOR


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

        FEATURES.provide(IDENTITY, id_mock)
        FEATURES.provide(PRODUCT_DATE_RANGE_CALCULATOR, self.mock_calc)
