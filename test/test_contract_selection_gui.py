import unittest

from subscription_manager.gui import contract_selection

def stubSelectedCallback(self, pool):
    print pool

def stubCancelCallback(self):
    print "canceled"


class ContractSelection(unittest.TestCase):
    pool = {'productName':'SomeProduct',
            'consumed':"consumed",
            'quantity':'quantity',
            'startDate':'stateDate',
            'endDate':'endDate',
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
