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

import unittest
import gtk
from datetime import datetime
from subscription_manager.managerlib import LocalTz

from subscription_manager.gui.storage import MappedTreeStore
from subscription_manager.gui.widgets import MachineTypeColumn, MultiEntitlementColumn, \
                                             QuantitySelectionColumn, SubDetailsWidget


class TestSubDetailsWidget(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testVirtOnly(self):
        d = datetime(2011, 4, 16, tzinfo=LocalTz())
        start_date = datetime(d.year, d.month, d.day, tzinfo=LocalTz())
        end_date = datetime(d.year + 1, d.month, d.day, tzinfo=LocalTz())
        details = SubDetailsWidget(show_contract=True)
        details.show('noname', contract='c', start=start_date, end=end_date, account='a',
                     management='m', support_level='s_l',
                     support_type='s_t', virt_only='v_o')
        s_iter = details.virt_only_text.get_buffer().get_start_iter()
        e_iter = details.virt_only_text.get_buffer().get_end_iter()
        self.assertEquals(details.virt_only_text.get_buffer().get_text(s_iter, e_iter), 'v_o')


class BaseColumnTest(unittest.TestCase):

    def _assert_column_value(self, column_class, model_bool_val, expected_text):
        model = gtk.ListStore(bool)
        model.append([model_bool_val])

        column = column_class(0)
        column._render_cell(None, column.renderer, model, model.get_iter_first())
        self.assertEquals(expected_text, column.renderer.get_property("text"))


class TestMachineTypeColumn(BaseColumnTest):

    def test_render_virtual_when_virt_only(self):
        self._assert_column_value(MachineTypeColumn, True,
                                  MachineTypeColumn.VIRTUAL_MACHINE)

    def test_render_physical_when_not_virt_only(self):
        self._assert_column_value(MachineTypeColumn, False,
                                   MachineTypeColumn.PHYSICAL_MACHINE)


class TestMultiEntitlementColumn(BaseColumnTest):

    def test_render_astrisk_when_multi_entitled(self):
        self._assert_column_value(MultiEntitlementColumn, True,
                                  MultiEntitlementColumn.MULTI_ENTITLEMENT_STRING)

    def test_render_empty_string_when_not_multi_entitled(self):
        self._assert_column_value(MultiEntitlementColumn, False,
                                  MultiEntitlementColumn.NOT_MULTI_ENTITLEMENT_STRING)


class TestQuantitySelectionColumnTests(unittest.TestCase):

    def test__update_cell_based_on_data_clears_cell_when_row_has_children(self):
        column, tree_model, iter = self._setup_column(1, False)
        tree_model.add_map(iter, self._create_store_map(1, False))

        column.quantity_renderer.set_property("text", "22")
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, iter)

        self.assertEquals("", column.quantity_renderer.get_property("text"))

    def test_update_cell_based_on_data_does_not_clear_cell_when_row_has_no_children(self):
        column, tree_model, iter = self._setup_column(1, False)

        # Manually set the text value here to make sure that the value is not reset.
        column.quantity_renderer.set_property("text", "12")
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, iter)

        self.assertNotEquals("", column.quantity_renderer.get_property("text"))

    def test_editor_is_disabled_when_not_multi_entitlement(self):
        is_multi_entitled = False
        column, tree_model, iter = self._setup_column(1, is_multi_entitled)
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, iter)
        self.assertEquals(is_multi_entitled, column.quantity_renderer.get_property("editable"))

    def test_editor_is_enabled_when_multi_entitlement(self):
        is_multi_entitled = True
        column, tree_model, iter = self._setup_column(1, is_multi_entitled)
        column._update_cell_based_on_data(None, column.quantity_renderer, tree_model, iter)
        self.assertEquals(is_multi_entitled, column.quantity_renderer.get_property("editable"))

    def test_value_not_changed_when_editor_has_invalid_text(self):
        expected_initial_value = 12
        column, tree_model, iter = self._setup_column(expected_initial_value, False)
        column._on_edit(column.quantity_renderer, tree_model.get_path(iter), "aaa",
                        tree_model)
        self.assertEquals(expected_initial_value,
                          tree_model.get_value(iter, column.quantity_store_idx))

    def test_value_changed_when_editor_has_valid_text(self):
        column, tree_model, iter = self._setup_column(1, False)
        column._on_edit(column.quantity_renderer, tree_model.get_path(iter), "20",
                        tree_model)
        self.assertEquals(20, tree_model.get_value(iter, column.quantity_store_idx))

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

    def test_filter_spinner_value_does_not_accept_value_under_lower_limit(self):
        self._run_filter_value_test("2", False, lower=3.0)

    def test_filter_spinner_value_allows_value_on_bounds(self):
        self._run_filter_value_test("1", True, upper=10, lower=1)
        self._run_filter_value_test("10", True, upper=10, lower=1)

    def _run_filter_value_test(self, test_input_value, is_allowed, upper=15, lower=1):
        column, tree_model, iter = self._setup_column(1, True)

        adjustment = gtk.Adjustment(upper=upper, lower=lower, value=7.0)
        # Simulate the editable created by the CellRendererSpin object.
        editable = gtk.SpinButton()
        editable.set_property("adjustment", adjustment)

        self.stopped = False

        def ensure_stopped(name):
            self.stopped = True

        editable.emit_stop_by_name = ensure_stopped

        column._filter_spinner_value("test-event", editable, test_input_value)

        self.assertEquals(not is_allowed, self.stopped)

    def _create_store_map(self, quantity, multi_entitlement):
        return {"quantity": quantity, "multi-entitlement": multi_entitlement}

    def _setup_column(self, initial_quantity, inital_multi_entitlement):
        tree_model = MappedTreeStore(self._create_store_map(int, bool))
        column = QuantitySelectionColumn("test-col", tree_model, tree_model['quantity'],
                                         tree_model['multi-entitlement'])
        iter = tree_model.add_map(None, self._create_store_map(initial_quantity,
                                                               inital_multi_entitlement))
        return (column, tree_model, iter)
