import unittest
import datetime

from subscription_manager.gui import contract_selection
from subscription_manager import managerlib

def stubSelectedCallback(self, pool):
    #print pool
    pass

def stubCancelCallback(self):
    #print "canceled"
    pass

class ContractSelection(unittest.TestCase):
    pool = {'productName':'SomeProduct',
            'consumed':"consumed",
            'quantity':'quantity',
            'startDate': datetime.datetime.now(tz=managerlib.ServerTz(0)).isoformat(),
            'endDate': datetime.datetime.now(tz=managerlib.ServerTz(0)).isoformat(),
            'contractNumber':'contractNumber'}

    def test_contract_selection(self):
        cs = contract_selection.ContractSelectionWindow(selected_callback=stubSelectedCallback,
                                                        cancel_callback=stubCancelCallback)

    def test_contract_selection_show(self):
        cs = contract_selection.ContractSelectionWindow(selected_callback=stubSelectedCallback,
                                                        cancel_callback=stubCancelCallback)
        cs.show()

    def test_contract_selection_add_pool(self):
        cs = contract_selection.ContractSelectionWindow(selected_callback=stubSelectedCallback,
                                                         cancel_callback=stubCancelCallback)
        cs.add_pool(self.pool)
