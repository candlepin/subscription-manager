import unittest
import datetime
from dateutil.tz import tzutc

from subscription_manager.gui import contract_selection


def stubSelectedCallback(self, pool):
    pass


def stubCancelCallback(self):
    pass


class ContractSelection(unittest.TestCase):
    pool = {'productName': 'SomeProduct',
            'consumed': '3',
            'quantity': '10',
            'startDate': datetime.datetime.now(tz=tzutc()).isoformat(),
            'endDate': datetime.datetime.now(tz=tzutc()).isoformat(),
            'contractNumber': 'contractNumber',
            'subscriptionNumber': 'subscriptionNumber',
            'attributes': [],
            'productAttributes': []}

    def test_contract_selection_show(self):
        cs = contract_selection.ContractSelectionWindow(selected_callback=stubSelectedCallback,
                                                        cancel_callback=stubCancelCallback)
        cs.show()

    def test_contract_selection_add_pool(self):
        cs = contract_selection.ContractSelectionWindow(selected_callback=stubSelectedCallback,
                                                         cancel_callback=stubCancelCallback)
        cs.add_pool(self.pool, 4)
