from __future__ import print_function, division, absolute_import

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import datetime
from dateutil.tz import tzutc

from subscription_manager.gui import contract_selection
from nose.plugins.attrib import attr


def stubSelectedCallback(self, pool):
    pass


def stubCancelCallback(self):
    pass


@attr('gui')
class ContractSelection(unittest.TestCase):
    pool = {'productName': 'SomeProduct',
            'consumed': 3,
            'quantity': 10,
            'startDate': datetime.datetime.now(tz=tzutc()).isoformat(),
            'endDate': datetime.datetime.now(tz=tzutc()).isoformat(),
            'contractNumber': 'contractNumber',
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
