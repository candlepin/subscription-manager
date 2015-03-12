#
# Copyright (c) 2010 Red Hat, Inc.
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

import datetime
import gettext
import logging
import os
import time
import warnings

from gi.repository import GObject
from gi.repository import Gtk
import gtk
import pango


from rhsm.certificate import GMT
from dateutil.tz import tzlocal

from subscription_manager.gui import messageWindow
from subscription_manager.gui import storage
from subscription_manager.gui import utils
from subscription_manager import managerlib

_ = gettext.gettext

GLADE_DIR = os.path.join(os.path.dirname(__file__), "data")

WARNING_COLOR = '#FFFB82'
EXPIRED_COLOR = '#FFAF99'

# Some versions of gtk has incorrect translations for the calendar widget
# and gtk itself complains about this with errors like:
#
# "GtkWarning: Whoever translated calendar:MY did so wrongly."
#
# We can't fix that (it's the shipped translations for gtk itself), so just
# ignore it.
warnings.filterwarnings(action="ignore",
                        category=Warning,
                        message=".*Whoever translated.*wrongly.")
# Ignore warnings about "Attempt to add property * after class was initialised"
# we get with glib2-2.40
# See https://bugzilla.gnome.org/show_bug.cgi?id=698614 for why we can
# ignore this warning (it was reverted in glib2-2.42 and later...)
warnings.filterwarnings(action="ignore",
                        category=Warning,
                        message=".*ttempt to add property.*after class.*")


class FileBasedGui(object):
    widget_names = []
    file_dir = None
    gui_file = None

    def gui_file_path(self):
        return os.path.join(self.file_dir, self.gui_file)


class BuilderFileBasedWidget(FileBasedGui):
    widget_names = []
    file_dir = GLADE_DIR

    @classmethod
    def from_file(cls, builder_file):
        builder_based_widget = cls()
        builder_based_widget.gui_file = builder_file

        builder_based_widget._load_file()

        return builder_based_widget

    def _load_file(self):
        path = self.gui_file_path()
        self.log.debug("gui_file_path=%s", path)
        self.builder.add_from_file(self.gui_file_path())

    def __init__(self):
        """
        Create a new widget backed by the give glade file (assumed to be in data/).
        The initial_widget_names is a list of widgets to pull in as instance
        variables.
        """
        self.log = logging.getLogger('rhsm-app.' + __name__ +
                                     '.' + self.__class__.__name__)

        self.builder = gtk.Builder()

    def get_object(self, name):
        return self.builder.get_object(name)

    def connect_signals(self, handlers_dict):
        return self.builder.connect_signals(handlers_dict)


class SubmanBaseWidget(object):
    widget_names = []
    gui_file = None

    def __init__(self):
        self.gui = self._gui_factory()
        self.pull_widgets(self.gui, self.widget_names)

    def _gui_factory(self):
        gui = BuilderFileBasedWidget.from_file(self.gui_file)
        return gui

    def pull_widgets(self, file_based_gui, widget_names):
        """
        This is a convenience method to pull the widgets from the 'names' list
        out of the given glade file, and make them available as variables on self.

        For example:  a widget with the name age_input could be accessed via self.age_input
        """

        for name in widget_names:
            setattr(self, name, file_based_gui.get_object(name))

    def connect_signals(self, signals):
        return self.gui.connect_signals(signals)

    # glade version -> get_widget
    def get_object(self, object_name):
        return self.gui.get_object(object_name)


class HasSortableWidget(object):

    def set_sorts(self, store, columns):
        # columns is a list of tuples where the tuple is in the format
        # (column object, column type, column key)
        for index, column_data in enumerate(columns):
            column_data[0].set_sort_column_id(index)
            sort_func = getattr(self, 'sort_' + column_data[1])
            store.set_sort_func(index, sort_func, column_data[2])
            # We want to re-stripe the model after the default class signal handler
            column_data[0].connect_after('clicked', self._stripe_rows, store)

    def sort_text(self, model, row1, row2, key):
        # model is a MappedListStore which maps column names to
        # column indexes.  The column name is passed in through 'key'.
        str1 = model.get_value(row1, model[key])
        str2 = model.get_value(row2, model[key])
        return cmp(str1, str2)

    def sort_date(self, model, row1, row2, key):
        date1 = model.get_value(row1, model[key]) \
            or datetime.date(datetime.MINYEAR, 1, 1)
        date2 = model.get_value(row2, model[key]) \
            or datetime.date(datetime.MINYEAR, 1, 1)
        epoch1 = time.mktime(date1.timetuple())
        epoch2 = time.mktime(date2.timetuple())
        return cmp(epoch1, epoch2)

    def _stripe_rows(self, column, store):
        """
        This method repaints the row stripes when the rows are re-arranged
        due to the user sorting a column
        """
        if 'background' in store:
            iter = store.get_iter_first()
            i = 0
            rows = []

            # Making changes to a TreeModel while you are iterating over it can lead
            # to weird behavior so we save all the rows that need to be recolored as
            # TreeRowReferences and set the color on them after the iteration is finished.
            while iter:
                bg_color = utils.get_cell_background_color(i)
                rows += [(ref, bg_color) for ref in utils.gather_group(store, iter, [])]
                i += 1
                iter = store.iter_next(iter)

            for r in rows:
                model = r[0].get_model()
                iter = model.get_iter(r[0].get_path())
                model.set_value(iter, model['background'], r[1])


class SubscriptionManagerTab(SubmanBaseWidget, HasSortableWidget):
    widget_names = ['top_view', 'content']
    # approx gtk version we need for grid lines to work
    # and not throw errors, this relates to basically rhel6
    MIN_GTK_MAJOR_GRID = 2
    MIN_GTK_MINOR_GRID = 18
    MIN_GTK_MICRO_GRID = 0

    gui_file = None

    def __init__(self):
        """
        Creates a new tab widget, given the specified glade file and a list of
        widget names to extract to instance variables.
        """
        # Mix the specified widgets with standard names in the
        # glade file by convention
        super(SubscriptionManagerTab, self).__init__()

#        self.builder = BuilderFileGui.from_file(glade_file)

        self.content.unparent()

        # In the allsubs tab, we don't show the treeview until it is populated
        if self.top_view is None:
            self.top_view = gtk.TreeView()

        # grid lines seem busted in rhel5, so we disable
        # in glade and turn on here for unbroken versions
        if gtk.check_version(self.MIN_GTK_MAJOR_GRID,
                             self.MIN_GTK_MINOR_GRID,
                             self.MIN_GTK_MICRO_GRID) is None:
            self.top_view.set_enable_tree_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)

        self.store = self.get_store()
        self.top_view.set_model(self.store)

        selection = self.top_view.get_selection()
        selection.connect('changed', self._selection_callback)

    def get_store(self):
        return storage.MappedListStore(self.get_type_map())

    def add_text_column(self, name, store_key, expand=False, markup=False):
        text_renderer = gtk.CellRendererText()

        if markup:
            column = gtk.TreeViewColumn(name,
                                        text_renderer,
                                        markup=self.store[store_key])
        else:
            column = gtk.TreeViewColumn(name,
                                        text_renderer,
                                        text=self.store[store_key])

        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(text_renderer, 'xalign', self.store['align'])

        if 'background' in self.store:
            column.add_attribute(text_renderer, 'cell-background',
                                self.store['background'])

        self.top_view.append_column(column)
        return column

    def add_date_column(self, name, store_key, expand=False):
        date_renderer = CellRendererDate()
        column = gtk.TreeViewColumn(name,
                                    date_renderer,
                                    date=self.store[store_key])
        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(date_renderer, 'xalign', self.store['align'])

        if 'background' in self.store:
            column.add_attribute(date_renderer, 'cell-background',
                                 self.store['background'])

        self.top_view.append_column(column)
        return column

    def get_content(self):
        return self.content

    def _selection_callback(self, treeselection):
        selection = SelectionWrapper(treeselection, self.store)

        if selection.is_valid():
            self.on_selection(selection)
        else:
            self.on_no_selection()

    def on_selection(self, selection):
        pass

    def on_no_selection(self):
        pass

    def refresh(self):
        pass


class SelectionWrapper(object):
    def __init__(self, treeselection, store):
        self.model, self.tree_iter = treeselection.get_selected()
        self.store = store

    def is_valid(self):
        return self.tree_iter is not None

    def __getitem__(self, key):
        return self.model.get_value(self.tree_iter, self.store[key])


class OverridesTable(object):
    def __init__(self, table_widget):
        table_widget.get_selection().set_mode(gtk.SELECTION_NONE)
        self.override_store = gtk.ListStore(str, str)
        table_widget.set_model(self.override_store)

        for idx, colname in enumerate([_("Name"), _("Value")]):
            column = gtk.TreeViewColumn(colname, gtk.CellRendererText(), markup=0, text=idx)
            column.set_expand(True)
            table_widget.append_column(column)

    def clear(self):
        self.override_store.clear()

    def add_override(self, key, value):
        self.override_store.append((key, value))


class ProductsTable(object):
    def __init__(self, table_widget, product_dir, yes_id=gtk.STOCK_APPLY,
                 no_id=gtk.STOCK_REMOVE):
        """
        Create a new products table, populating the gtk.TreeView.

        yes_id and no_id are GTK constants that specify the icon to
        use for representing if a product is installed.
        """

        table_widget.get_selection().set_mode(gtk.SELECTION_NONE)
        self.table_widget = table_widget
        self.product_store = gtk.ListStore(str, gtk.gdk.Pixbuf)
        table_widget.set_model(self.product_store)

        self.yes_icon = self._render_icon(yes_id)
        self.no_icon = self._render_icon(no_id)
        self.product_dir = product_dir

        name_column = gtk.TreeViewColumn(_("Product"),
                                         gtk.CellRendererText(),
                                         markup=0)
        name_column.set_expand(True)
        installed_column = gtk.TreeViewColumn(_("Installed"),
                                              gtk.CellRendererPixbuf(),
                                              pixbuf=1)

        table_widget.append_column(name_column)
        table_widget.append_column(installed_column)

    def clear(self):
        """
        Remove all products from the table.
        """
        self.product_store.clear()

    def add_product(self, product_name, product_id):
        """
        Add a product with the given name and id to the table.
        """
        self.product_store.append([product_name, self._get_icon(product_id)])

    def set_accessibility_name(self, accessibility_name):
        self.table_widget.get_accessible().set_name(accessibility_name)

    def _render_icon(self, icon_id):
        return self.table_widget.render_icon(icon_id, gtk.ICON_SIZE_MENU)

    def _get_icon(self, product_id):
        if self.product_dir.find_by_product(product_id):
            return self.yes_icon
        else:
            return self.no_icon


class SubDetailsWidget(SubmanBaseWidget):
    widget_names = ["sub_details_vbox", "subscription_text", "products_view",
                    "support_level_and_type_text", "sku_text", "pool_type_text"]
    gui_file = "subdetails.glade"

    def __init__(self, product_dir):
        super(SubDetailsWidget, self).__init__()

        self.sub_details_vbox.unparent()

        self.bundled_products = ProductsTable(self.products_view, product_dir)

        self.expired_color = gtk.gdk.color_parse(EXPIRED_COLOR)
        self.warning_color = gtk.gdk.color_parse(WARNING_COLOR)

        self._set_accessibility_names()

    def show(self, name, contract=None, start=None, end=None, account=None,
            management=None, support_level="", support_type="",
            virt_only=None, products=None, highlight=None, sku=None,
            reasons=[], expiring=False, pool_type=""):
        """
        Show subscription details.

        Start and end should be datetime objects.
        Products is a list of tuples in the format (name, id)
        """
        products = products or []
        # set a new buffer to clear out all the old tag information
        self.subscription_text.set_buffer(gtk.TextBuffer())
        self._set(self.subscription_text, name)
        buf = self.subscription_text.get_buffer()
        tag = buf.create_tag("highlight-tag", weight=pango.WEIGHT_BOLD)

        for index in utils.find_text(name, highlight):
            buf.apply_tag(tag, buf.get_iter_at_offset(index),
                    buf.get_iter_at_offset(index + len(highlight)))

        self._set(self.sku_text, sku)
        self._set(self.pool_type_text, pool_type)

        display_level = support_level
        if support_level == "":
            display_level = _("Not Set")
        if support_type != "":
            display_level_and_type = ", ".join([display_level, support_type])
        else:
            display_level_and_type = display_level

        self._set(self.support_level_and_type_text, display_level_and_type)

        self._show_other_details(name, contract, start, end, account,
                                 management, support_level, support_type,
                                 virt_only, products, highlight, sku,
                                 reasons, expiring)

        self.bundled_products.clear()
        for product in products:
            self.bundled_products.add_product(utils.apply_highlight(product[0],
                highlight), product[1])

    def _show_other_details(self, name, contract=None, start=None, end=None, account=None,
                           management=None, support_level="", support_type="",
                           virt_only=None, products=None, highlight=None, sku=None,
                           reasons=[], expiring=False):
        pass

    def _set(self, text_view, text):
        """Set the buffer of the given TextView to contain the text"""
        if text is None:
            text = _("None")
        text_view.get_buffer().set_text(text)

    def clear(self):
        """ No subscription to display. """
        self.bundled_products.clear()
        self.subscription_text.get_buffer().set_text("")

        self._set(self.sku_text, "")
        self._set(self.pool_type_text, "")

        self._set(self.support_level_and_type_text, "")

        self._clear_other_details()

    def _clear_other_details(self):
        pass

    def get_widget(self):
        """ Returns the widget to be packed into a parent window. """
        return self.sub_details_vbox

    # fix me, probably not needed. base class for Details Widget
    # and sub class for all_available and mysubs?
    def _set_accessibility_names(self):
        # Since all the tabs have the same parent window, the accessibility
        # names must be unique among all three tabs to allow unambiguous
        # access to the widgets.  Since the SubDetails widget is used
        # under two different tabs, we must programatically override the
        # accessibility name for duplicated widgets in one of the tabs.
        # See BZ 803374.

        self.subscription_text.get_accessible().set_name(
                "All Available Subscription Text")
        self.sku_text.get_accessible().set_name(
                "All Available SKU Text")
        self.support_level_and_type_text.get_accessible().set_name(
                "All Available Support Level And Type Text")
        self.bundled_products.set_accessibility_name(
                "All Available Bundled Product Table")
        self.pool_type_text.get_accessible().set_name(
                "All Available Subscription Type Text")


# also show contract info on this details widget
class ContractSubDetailsWidget(SubDetailsWidget):
    widget_names = SubDetailsWidget.widget_names + \
                    ["contract_number_text",
                     "start_end_date_text",
                     "account_text",
                     "provides_management_text",
                     "virt_only_text",
                     "details_view"]

    gui_file = "subdetailscontract.glade"

    def __init__(self, product_dir):
        super(ContractSubDetailsWidget, self).__init__(product_dir)
        # Save the original background color for the
        # start_end_date_text widget so we can restore it in the
        # clear() function.




        # FIXME
        #self.original_bg = self.start_end_date_text.rc_get_style().base[gtk.STATE_NORMAL]
        # FIXME



    def _show_other_details(self, name, contract=None, start=None, end=None, account=None,
                           management=None, support_level="", support_type="",
                           virt_only=None, products=None, highlight=None, sku=None,
                           reasons=[], expiring=False):
        products = products or []
        reasons = reasons or []

        self._set(self.details_view, '\n'.join(reasons))

        self.start_end_date_text.modify_base(gtk.STATE_NORMAL,
                self._get_date_bg(end, expiring))

        self._set(self.contract_number_text, contract)
        self._set(self.start_end_date_text, "%s - %s" % (
                    managerlib.format_date(start), managerlib.format_date(end)))
        self._set(self.account_text, account)
        self._set(self.provides_management_text, management)
        self._set(self.virt_only_text, virt_only)

    def _clear_other_details(self):
        #Clear row highlighting


        # FIXME
        #self.start_end_date_text.modify_base(gtk.STATE_NORMAL, self.original_bg)
        # FIXME


        self._set(self.contract_number_text, "")
        self._set(self.start_end_date_text, "")
        self._set(self.account_text, "")
        self._set(self.provides_management_text, "")
        self._set(self.virt_only_text, "")
        self._set(self.details_view, "")

    def _set_accessibility_names(self):
        # already set in glade
        pass

    def _get_date_bg(self, end, expiring):
        now = datetime.datetime.now(GMT())

        if end < now:
            return self.expired_color

        if expiring:
            return self.warning_color


        # FIXME, try to return the orig color, or remove this?
        #return self.original_bg
        return self.expired_color
        # FIXME



class CellRendererDate(gtk.CellRendererText):

    """
    Custom cell renderer to display the date in the user's locale.
    """

    __gproperties__ = {
            'date': (GObject.TYPE_PYOBJECT, 'date', 'date displayed',
                GObject.PARAM_READWRITE)
    }

    def __init__(self):
        GObject.GObject.__init__(self)

    def do_set_property(self, prop, value):
        """
        called to set the date property for rendering in a cell.
        we convert to display in the user's locale, then pass on to the cell
        renderer.
        """

        if value:
            date = managerlib.format_date(value)
        else:
            date = value

        gtk.CellRendererText.set_property(self, 'text', date)


class DatePicker(gtk.HBox):

    __gsignals__ = {
            'date-picked-cal': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, tuple()),
            'date-picked-text': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, tuple())
    }

    def __init__(self, date):
        """
        Initialize the DatePicker. date is a python datetime.date object.
        """
        gtk.HBox.__init__(self)

        image = Gtk.Image.new_from_icon_name('x-office-calendar', Gtk.IconSize.MENU)
        image.show()

        # set the timezone so we can sent it to the server
        self._date = datetime.datetime(date.year, date.month, date.day,
                tzinfo=tzlocal())
        self._date_entry = gtk.Entry()
        self._date_entry.set_width_chars(10)

        self._date_entry.set_text(self._date.date().isoformat())

        atk_entry = self._date_entry.get_accessible()
        atk_entry.set_name('date-entry')

        self._cal_button = gtk.Button()
        self._cal_button.set_image(image)
        atk_entry = self._cal_button.get_accessible()
        atk_entry.set_name("Calendar")

        self.pack_start(self._date_entry)
        self.pack_start(self._cal_button)
        self._cal_button.connect("clicked", self._button_clicked)
        self.connect('date-picked-cal', self._date_update_cal)
        self.connect('date-picked-text', self._date_update_text)

        self._calendar = gtk.Calendar()
        atk_entry = self._calendar.get_accessible()
        atk_entry.set_name("Calendar")

        self.show()
        self._date_entry.show()
        self._cal_button.show()

    @property
    def date(self):
        # if the selected date is today, set the time to be None
        # then we can avoid any time zone issues by letting
        # the server get time.
        return utils.make_today_none(self._date)

    def date_entry_validate(self):
        """
        validate the date and pop up a box if not valid
        """
        try:
            self._date_validate(self._date_entry.get_text())
            self.emit('date-picked-text')
            return True
        except ValueError:
            today = datetime.date.today()
            messageWindow.ErrorDialog(messageWindow.wrap_text(
                                "%s %s" % (_("Invalid date format. Please re-enter a valid date. Example: "), today.isoformat())))
            return False

    def _date_validate(self, date_str):
        # try this as a iso8601 date format, aka, 2012-12-25
        try:
            date = datetime.datetime(
                    *(time.strptime(date_str, '%Y-%m-%d')[0:6]))
            self._date = datetime.datetime(date.year, date.month, date.day,
                    tzinfo=tzlocal())
        except ValueError:
            raise

    def _date_entry_box_grab_focus(self, dummy2=None, dummy3=None):
        self._date_entry.grab_focus()

    def _date_update_cal(self, dummy=None):
        # set the text box to the date from the calendar
        self._date_entry.set_text(self._date.date().isoformat())

    def _date_update_text(self, dummy=None):
        # set the cal to the date from the text box, and set self._date

        try:
            self._date_validate(self._date_entry.get_text())
        except ValueError:
            today = datetime.date.today()
            self._date = datetime.datetime(today.year, today.month, today.day,
                tzinfo=tzlocal())

        self._calendar.select_month(self._date.month - 1, self._date.year)
        self._calendar.select_day(self._date.day)

    def _button_clicked(self, button):
        self._calendar_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self._calendar_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self._calendar_window.set_modal(True)
        self._calendar_window.set_title(_("Date Selection"))
        self._calendar_window.set_transient_for(
                self.get_parent_window().get_user_data())

        self._calendar.select_month(self._date.month - 1, self._date.year)
        self._calendar.select_day(self._date.day)

        vbox = gtk.VBox(spacing=3)
        vbox.set_border_width(2)
        vbox.pack_start(self._calendar)

        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        vbox.pack_start(button_box)

        button = gtk.Button(_("Today"))
        button.connect("clicked", self._today_clicked)
        button_box.pack_start(button)

        frame = gtk.Frame()
        frame.add(vbox)
        self._calendar_window.add(frame)
        self._calendar_window.set_position(gtk.WIN_POS_MOUSE)
        self._calendar_window.show_all()

        self._calendar.connect("day-selected-double-click",
                self._calendar_clicked)

    def _destroy(self):
        self._calendar_window.destroy()

    def _calendar_clicked(self, calendar):
        (year, month, day) = self._calendar.get_date()
        self._date = datetime.datetime(year, month + 1, day,
                tzinfo=tzlocal())
        self.emit('date-picked-cal')
        self._destroy()

    def _today_clicked(self, button):
        day = datetime.date.today()
        self._date = datetime.datetime(day.year, day.month, day.day,
                tzinfo=tzlocal())
        self.emit('date-picked-cal')
        self._destroy()


class CheckBoxColumn(gtk.TreeViewColumn):

    def __init__(self, column_title, store, store_key, toggle_callback=None):
        self.store = store
        self.store_key = store_key
        self._toggle_callback = toggle_callback
        self.renderer = gtk.CellRendererToggle()
        self.renderer.set_radio(False)
        gtk.TreeViewColumn.__init__(self, column_title, self.renderer, active=self.store[self.store_key])
        self.renderer.connect("toggled", self._on_toggle)

    def _on_toggle(self, widget, path):
        tree_iter = self.store.get_iter(path)
        if not tree_iter:
            return

        column = self.store[self.store_key]
        new_state = not self.store.get_value(tree_iter, column)
        self.store.set(tree_iter, column, new_state)

        if self._toggle_callback:
            self._toggle_callback(tree_iter, new_state)


class ToggleTextColumn(gtk.TreeViewColumn):
    """
    A gtk.TreeViewColumn that toggles between two text values based on a boolean
    value in the store.
    """
    def __init__(self, column_title, model_idx):
        gtk.TreeViewColumn.__init__(self, column_title)
        self.model_idx = model_idx
        self.renderer = gtk.CellRendererText()
        self.renderer.set_property('xalign', 0.5)
        self.pack_start(self.renderer, False)
        self.set_cell_data_func(self.renderer, self._render_cell)

    def _render_cell(self, column, cell_renderer, tree_model, tree_iter):
        # Clear the cell if we are a parent row.
        if tree_model.iter_n_children(tree_iter) > 0:
            cell_renderer.set_property("text", "")
            return

        bool_val = tree_model.get_value(tree_iter, self.model_idx)
        if bool_val is None:
            text = self._get_none_text()
        elif bool(bool_val):
            text = self._get_true_text()
        else:
            text = self._get_false_text()
        cell_renderer.set_property("text", text)

    def _get_true_text(self):
        raise NotImplementedError("Subclasses must implement _get_true_text(self).")

    def _get_false_text(self):
        raise NotImplementedError("Subclasses must implement _get_false_text(self).")

    def _get_none_text(self):
        raise NotImplementedError("Subclasses must implement _get_none_text(self).")


class MachineTypeColumn(ToggleTextColumn):

    PHYSICAL_MACHINE = _("Physical")
    VIRTUAL_MACHINE = _("Virtual")
    BOTH_MACHINES = _("Both")

    def __init__(self, virt_only_model_idx):
        ToggleTextColumn.__init__(self, _("Type"), virt_only_model_idx)
        # Center the column header text.
        self.set_alignment(0.5)

    def _get_true_text(self):
        return self.VIRTUAL_MACHINE

    def _get_false_text(self):
        return self.PHYSICAL_MACHINE

    def _get_none_text(self):
        return self.BOTH_MACHINES


class QuantitySelectionColumn(gtk.TreeViewColumn):
    def __init__(self, column_title, tree_model, quantity_store_idx, is_multi_entitled_store_idx,
                 available_store_idx=None, quantity_increment_idx=None, editable=True):
        self.quantity_store_idx = quantity_store_idx
        self.is_multi_entitled_store_idx = is_multi_entitled_store_idx
        self.available_store_idx = available_store_idx
        self.quantity_increment_idx = quantity_increment_idx

        self.quantity_renderer = gtk.CellRendererSpin()
        self.quantity_renderer.set_property("xalign", 0)
        self.quantity_renderer.set_property("adjustment",
            gtk.Adjustment(lower=1, upper=100, step_incr=1))
        self.quantity_renderer.set_property("editable", editable)
        self.quantity_renderer.connect("edited", self._on_edit, tree_model)
        self.quantity_renderer.connect("editing-started", self._setup_editor)

        gtk.TreeViewColumn.__init__(self, column_title, self.quantity_renderer,
                                    text=self.quantity_store_idx)
        self.set_cell_data_func(self.quantity_renderer, self._update_cell_based_on_data)

    def _setup_editor(self, cellrenderer, editable, path):
        # Only allow numeric characters.
        editable.set_property("numeric", True)
        editable.connect("insert-text", self._text_inserted_in_spinner)

    def _text_inserted_in_spinner(self, widget, text, length, position):
        # if you don't do this, garbage comes in with text
        text = text[:length]
        pos = widget.get_position()
        orig_text = widget.get_text()
        new_text = orig_text[:pos] + text + orig_text[pos:]
        self._filter_spinner_value("insert-text", widget, new_text)

    def _filter_spinner_value(self, triggering_event, editable, new_value):
        adj = editable.get_property("adjustment")
        upper = int(adj.get_property("upper"))

        # Ensure that a digit was entered.
        if len(new_value) >= 1 and not new_value.isdigit():
            editable.emit_stop_by_name(triggering_event)
            return

        # Allow entering 0 as it is a possible default.
        # Do not allow values such as 001, 012 ...
        if len(new_value) > 1 and new_value[0] == '0':
            editable.emit_stop_by_name(triggering_event)
            return

        # Check to make sure they aren't over the upper bound here.
        # We will check that they aren't under the lower bound once they have
        # finished entering text in _on_edit so that we don't prevent people
        # from temporarily entering values that are too low.  E.g. a person
        # entering '12' must type '1' first which might be below the lower bound.
        if int(new_value) > upper:
            editable.emit_stop_by_name(triggering_event)
            return

    def get_column_legend_text(self):
        return "<b><small>* %s</small></b>" % (_("Click to Adjust Quantity"))

    def _on_edit(self, renderer, path, new_text, model):
        """
        Handles when a quantity is changed in the cell. Stores new value in
        model.
        """
        try:
            new_quantity = int(new_text)
            tree_iter = model.get_iter(path)

            if self.quantity_increment_idx is not None:
                increment = model.get_value(tree_iter, self.quantity_increment_idx)
            else:
                increment = 1

            # Don't allow quantities that aren't divisible by the increment.  This
            # also serves to prevent values that are lower than the lower bound.
            # Since the lower bound is the increment itself, any number smaller
            # than the lower bound modulo the lower bound will be the smaller number.
            # E.g. If the increment is 4 and the person enters 3, 3 % 4 is 3 and we
            # will reset to the previous value.
            if new_quantity % increment != 0:
                return

            model.set_value(tree_iter, self.quantity_store_idx, new_quantity)
        except ValueError:
            # Do nothing... The value entered in the grid will be reset.
            pass

    def _update_cell_based_on_data(self, column, cell_renderer, tree_model, tree_iter):
        # Clear the cell if we are a parent row.
        if tree_model.iter_n_children(tree_iter) > 0:
            cell_renderer.set_property("text", "")

        # Disable editor if not multi-entitled.
        is_multi_entitled = tree_model.get_value(tree_iter, self.is_multi_entitled_store_idx)
        cell_renderer.set_property("editable", is_multi_entitled)

        if is_multi_entitled:
            quantity = tree_model.get_value(tree_iter, self.quantity_store_idx)
            cell_renderer.set_property("text", "%s *" % quantity)

        if self.available_store_idx is not None:
            available = tree_model.get_value(tree_iter, self.available_store_idx)
            if available and available != -1:
                if self.quantity_increment_idx is not None:
                    increment = tree_model.get_value(tree_iter, self.quantity_increment_idx)
                else:
                    increment = 1

                cell_renderer.set_property("adjustment",
                    gtk.Adjustment(lower=int(increment), upper=int(available), step_incr=int(increment)))


class TextTreeViewColumn(gtk.TreeViewColumn):
    def __init__(self, store, column_title, store_key, expand=False, markup=False):
        self.column_title = column_title
        self.text_renderer = gtk.CellRendererText()
        self.store_key = store_key

        if markup:
            gtk.TreeViewColumn.__init__(self, self.column_title,
                                        self.text_renderer,
                                        markup=store[store_key])
        else:
            gtk.TreeViewColumn.__init__(self, self.column_title,
                                        self.text_renderer,
                                        text=store[store_key])

        if expand:
            self.set_expand(True)
        elif 'align' in store:
            self.add_attribute(self.text_renderer, 'xalign', store['align'])

        if 'background' in store:
            self.add_attribute(self.text_renderer, 'cell-background',
                                store['background'])


class WidgetSwitcher(object):

    def __init__(self, parent, *widgets):
        self.container = parent
        self.widgets = widgets

    def set_active(self, activate_index=0):
        current_children = self.container.get_children()
        to_add = self.widgets[activate_index]
        if to_add not in current_children:
            for widget in current_children:
                self.container.remove(widget)
            self.container.add(to_add)
        self.container.show_all()


def expand_collapse_on_row_activated_callback(treeview, path, view_column):
    """
    A gtk.TreeView callback allowing row expand/collapse on double-click or key
    press (space, return, enter).
    """
    if treeview.row_expanded(path):
        treeview.collapse_row(path)
    else:
        treeview.expand_row(path, True)

    return True


def get_scrollable_label():
    label = gtk.Label()
    label.set_use_markup(True)
    label.set_line_wrap(True)
    label.set_line_wrap_mode(pango.WRAP_WORD)
    viewport = gtk.Viewport()
    viewport.add(label)
    viewport.show_all()
    return label, viewport
