from __future__ import print_function, division, absolute_import

# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
try:
    import unittest2 as unittest
except ImportError:
    import unittest

#from gi.repository import Gtk
from datetime import datetime, timedelta
from rhsm.certificate import GMT

from subscription_manager.ga import Gtk as ga_Gtk
from subscription_manager.gui.storage import MappedTreeStore
from subscription_manager.gui.widgets import MachineTypeColumn, QuantitySelectionColumn, \
                                             SubDetailsWidget, ContractSubDetailsWidget, \
                                             DatePicker, HasSortableWidget
from dateutil.tz import tzlocal
from nose.plugins.attrib import attr


@attr('gui')
class TestSubDetailsWidget(unittest.TestCase):
    widget = SubDetailsWidget
    sku_text = "Some SKU"
    expected_sub_text = "All Available Subscription Text"

    def show(self, details):
        details.show(name="Some Product", contract="123123",
                     start=datetime.now(GMT()), end=datetime.now(GMT()) + timedelta(days=365),
                     highlight="some filter", support_level="Standard",
                     support_type="L1",
                     sku=self.sku_text)

    def test_show(self):
        details = self.widget(None)
        self.show(details)

    def test_clear(self):
        details = self.widget(None)
        self.show(details)
        details.clear()

    def test_a11y(self):
        details = self.widget(None)
        self.show(details)
        sub_text = details.subscription_text.get_accessible().get_name()
        self.assertEqual(self.expected_sub_text, sub_text)


@attr('gui')
class TestContractSubDetailsWidget(TestSubDetailsWidget):
    widget = ContractSubDetailsWidget
    expected_sub_text = "Subscription Text"

    def test_get_expired_bg(self):
        details = self.widget(None)
        self.show(details)
        yesterday = datetime.now(GMT()) - timedelta(days=1)
        bg_color = details._get_date_bg(yesterday, True)
        self.assertEqual(details.expired_color, bg_color)

    def test_get_warning_bg(self):
        details = self.widget(None)
        self.show(details)
        tomorrow = datetime.now(GMT()) + timedelta(days=1)
        bg_color = details._get_date_bg(tomorrow, True)
        self.assertEqual(details.warning_color, bg_color)

    def test_get_details(self):
        details = self.widget(None)
        reasons = ['reason 1', 'reason 2']
        details.show("Some Product", reasons=reasons, start=datetime.now(GMT()), end=datetime.now(GMT()) + timedelta(days=365))
        buff = details.details_view.get_buffer()
        result_list = buff.get_text(buff.get_bounds()[0],
                                    buff.get_bounds()[1],
                                    include_hidden_chars=False).split("\n")
        self.assertEqual(reasons, result_list)

    def testVirtOnly(self):
        details = self.widget(None)
        self.show(details)
        d = datetime(2011, 4, 16, tzinfo=tzlocal())
        start_date = datetime(d.year, d.month, d.day, tzinfo=tzlocal())
        end_date = datetime(d.year + 1, d.month, d.day, tzinfo=tzlocal())
        details.show('noname', contract='c', start=start_date, end=end_date, account='a',
                     management='m', support_level='s_l',
                     support_type='s_t', virt_only='v_o')
        s_iter = details.virt_only_text.get_buffer().get_start_iter()
        e_iter = details.virt_only_text.get_buffer().get_end_iter()
        self.assertEqual(details.virt_only_text.get_buffer().get_text(s_iter, e_iter, False), 'v_o')


@attr('gui')
class TestDatePicker(unittest.TestCase):
    def test_date_picker_date(self):
        d = datetime(2033, 12, 29, tzinfo=tzlocal())
        self._assert_is_isoformat(d)

    def test_date_validate_2000_12_1(self):
        d = datetime(2000, 12, 1, tzinfo=tzlocal())
        self._assert_is_isoformat(d)

    def test_date_validate_2000_1_22(self):
        d = datetime(2000, 1, 12, tzinfo=tzlocal())
        self._assert_is_isoformat(d)

    def test_date_validate_1_1_2000(self):
        d = datetime(2000, 1, 1, tzinfo=tzlocal())
        self._assert_is_isoformat(d)

    # why? because some locales fail to parse in dates with
    # double digt months
    def test_date_validate_12_29_2020(self):
        #with Capture(silent=True):
        d = datetime(2020, 12, 29, tzinfo=tzlocal())
        self._assert_is_isoformat(d)

    def _assert_is_isoformat(self, d):
        date_picker = DatePicker(d)
        valid = date_picker.date_entry_validate()
        self.assertTrue(valid)
        self.assertEqual(date_picker._date_entry.get_text(), d.date().isoformat())


class BaseColumnTest(unittest.TestCase):

    def _assert_column_value(self, column_class, model_bool_val, expected_text):
        model = ga_Gtk.ListStore(bool)
        model.append([model_bool_val])

        column = column_class(0)
        column._render_cell(None, column.renderer, model, model.get_iter_first())
        self.assertEqual(expected_text, column.renderer.get_property("text"))


@attr('gui')
class TestHasSortableWidget(unittest.TestCase):

    def _run_cases(self, cases, expected):
        for index, case in enumerate(cases):
            result = HasSortableWidget.compare_text(*case)
            self.assertEqual(result, expected[index])

    def test_compare_text_ints(self):
        # Two string representations of ints
        str1 = '1'
        str2 = '2'
        cases = [
            (str1, str2),  # x < y should return -1
            (str2, str1),  # x > y should return 1
            (str1, str1)  # x == y should return 0
        ]
        expected = [
            -1,
            1,
            0
        ]

        self._run_cases(cases, expected)

    def test_compare_text_unlimited(self):
        # Test unlimited comparison
        unlimited = 'Unlimited'
        str1 = '1'
        cases = [
            (unlimited, str1),  # Unlimited, 1 should return 1
            (str1, unlimited),  # 1, Unlimited should return -1
            (unlimited, unlimited)  # Unlimited, Unlimited should return 0
        ]
        expected = [
            1,
            -1,
            0
        ]

        self._run_cases(cases, expected)

    def test_compare_alphabetic_text(self):
        cases = [
            ('a', 'b'),
            ('b', 'a'),
            ('a', 'a')
        ]

        def _cmp(x1, x2):
            if x1 < x2:
                return -1
            elif x1 == x2:
                return 0
            else:
                return 1

        expected = [_cmp(*case) for case in cases]

        self._run_cases(cases, expected)


@attr('gui')
class TestMachineTypeColumn(BaseColumnTest):

    def test_render_virtual_when_virt_only(self):
        self._assert_column_value(MachineTypeColumn, True,
                                  MachineTypeColumn.VIRTUAL_MACHINE)

    def test_render_physical_when_not_virt_only(self):
        self._assert_column_value(MachineTypeColumn, False,
                                   MachineTypeColumn.PHYSICAL_MACHINE)


@attr('gui')
class TestQuantitySelectionColumnTests(unittest.TestCase):

    def test__update_cell_based_on_data_clears_cell_when_row_has_children(self):
        column, tree_model, tree_iter = self._setup_column(1, False)
        tree_model.add_map(tree_iter, self._create_store_map(1, False, 15, 2))

        column.quantity_renderer.set_property("text", "22")
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, tree_iter)

        self.assertEqual("", column.quantity_renderer.get_property("text"))

    def test_update_cell_based_on_data_does_not_clear_cell_when_row_has_no_children(self):
        column, tree_model, tree_iter = self._setup_column(1, False)

        # Manually set the text value here to make sure that the value is not reset.
        column.quantity_renderer.set_property("text", "12")
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, tree_iter)

        self.assertNotEqual("", column.quantity_renderer.get_property("text"))

    def test_editor_is_disabled_when_not_multi_entitlement(self):
        is_multi_entitled = False
        column, tree_model, tree_iter = self._setup_column(1, is_multi_entitled)
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, tree_iter)
        self.assertEqual(is_multi_entitled, column.quantity_renderer.get_property("editable"))

    def test_editor_is_enabled_when_multi_entitlement(self):
        is_multi_entitled = True
        column, tree_model, tree_iter = self._setup_column(1, is_multi_entitled)
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, tree_iter)
        self.assertEqual(is_multi_entitled, column.quantity_renderer.get_property("editable"))

    def test_value_not_changed_when_editor_has_invalid_text(self):
        expected_initial_value = 12
        column, tree_model, tree_iter = self._setup_column(expected_initial_value, False)
        column._on_edit(column.quantity_renderer, tree_model.get_path(tree_iter), "aaa",
                        tree_model)
        self.assertEqual(expected_initial_value,
                          tree_model.get_value(tree_iter, column.quantity_store_idx))

    def test_value_changed_when_editor_has_valid_text(self):
        column, tree_model, tree_iter = self._setup_column(1, False)
        column._on_edit(column.quantity_renderer, tree_model.get_path(tree_iter), "20",
                        tree_model)
        self.assertEqual(20, tree_model.get_value(tree_iter, column.quantity_store_idx))

    def test_filter_spinner_value_only_allows_digits(self):
        self._run_filter_value_test("4", True)
        self._run_filter_value_test("q", False)
        self._run_filter_value_test("!", False)
        self._run_filter_value_test("1d3f", False)

    def test_filter_spinner_value_always_allows_zero(self):
        self._run_filter_value_test("0", True, upper=5, lower=1)

    # Tests for values like 01, 002, 00003 ...
    def test_filter_spinner_value_does_not_allow_zero_at_start_of_value(self):
        self._run_filter_value_test("02", False)
        self._run_filter_value_test("004", False)
        self._run_filter_value_test("0", True)

    def test_filter_spinner_value_does_not_accept_value_over_upper_limit(self):
        self._run_filter_value_test("13", False, upper=12.0)

    def test_filter_spinner_value_allows_value_on_bounds(self):
        self._run_filter_value_test("1", True, upper=10, lower=1)
        self._run_filter_value_test("10", True, upper=10, lower=1)

    def _run_filter_value_test(self, test_input_value, is_allowed, upper=15, lower=1, step_incr=1):
        column, tree_model, tree_iter = self._setup_column(1, True)

        adjustment = ga_Gtk.Adjustment(upper=upper, lower=lower, value=7.0, step_incr=step_incr)
        # Simulate the editable created by the CellRendererSpin object.
        editable = ga_Gtk.SpinButton()
        editable.set_property("adjustment", adjustment)

        self.stopped = False

        def ensure_stopped(name):
            self.stopped = True

        editable.emit_stop_by_name = ensure_stopped

        column._filter_spinner_value("test-event", editable, test_input_value)

        self.assertEqual(not is_allowed, self.stopped)

    def _create_store_map(self, quantity, multi_entitlement, available, increment):
        return {"quantity": quantity, "multi-entitlement": multi_entitlement, "available_store": available,
                "quantity_increment": increment}

    def _setup_column(self, initial_quantity, inital_multi_entitlement, initial_available=15,
            initial_increment=2):
        tree_model = MappedTreeStore(self._create_store_map(int, bool, int, int))
        column = QuantitySelectionColumn("test-col", tree_model, tree_model['quantity'],
                                         tree_model['multi-entitlement'], tree_model['available_store'],
                                         tree_model['quantity_increment'])
        tree_iter = tree_model.add_map(None, self._create_store_map(initial_quantity,
                                                               inital_multi_entitlement, initial_available,
                                                               initial_increment))
        return (column, tree_model, tree_iter)

    def test_increment_based_on_provided_data(self):
        (column, tree_model, tree_iter) = self._setup_column(15, True, 15, 2)
        column._update_cell_based_on_data(column, column.quantity_renderer, tree_model, tree_iter)
        adj = column.quantity_renderer.get_property("adjustment")
        self.assertEqual(2, int(adj.get_property("step-increment")))
        self.assertEqual(2, int(adj.get_property("lower")))

    def test_on_edit_refuses_non_multiples_of_increment(self):
        (column, tree_model, tree_iter) = self._setup_column(10, True, 15, 2)
        column._on_edit(None, 0, 7, tree_model)
        self.assertEqual(10, int(tree_model.get_value(tree_iter, tree_model['quantity'])))

    def test_on_edit_allows_multiples_of_increment(self):
        (column, tree_model, tree_iter) = self._setup_column(10, True, 15, 2)
        column._on_edit(None, 0, 8, tree_model)
        self.assertEqual(8, tree_model.get_value(tree_iter, tree_model['quantity']))

    def test_on_edit_refuses_value_lower_than_increment(self):
        (column, tree_model, tree_iter) = self._setup_column(10, True, 15, 4)
        column._on_edit(None, 0, 2, tree_model)
        self.assertEqual(10, tree_model.get_value(tree_iter, tree_model['quantity']))
