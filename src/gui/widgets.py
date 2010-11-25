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

import os
import gobject
import gtk

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

import managerlib
import storage
from certlib import ProductDirectory

GLADE_DIR = os.path.join(os.path.dirname(__file__), "data")

class GladeWidget(object):

    def __init__(self, glade_file, initial_widget_names=None):
        """
        Create a new widget backed by the give glade file (assumed to be in data/).
        The initial_widget_names is a list of widgets to pull in as instance
        variables.
        """
        self.glade = gtk.glade.XML(os.path.join(GLADE_DIR, glade_file))

        if initial_widget_names:
            self.pull_widgets(initial_widget_names)

    def pull_widgets(self, names):
        """
        This is a convenience method to pull the widgets from the 'names' list
        out of the given glade file, and make them available as variables on self.

        For example:  a widget with the name age_input could be accessed via self.age_input
        """

        for name in names:
            setattr(self, name, self.glade.get_widget(name))

class SubscriptionManagerTab(GladeWidget):

    def __init__(self, glade_file, initial_widget_names=[]):
        """
        Creates a new tab widget, given the specified glade file and a list of
        widget names to extract to instance variables.
        """
        # Mix the specified widgets with standard names in the
        # glade file by convention
        widgets = ['top_view', 'content'] + initial_widget_names
        super(SubscriptionManagerTab, self).__init__(glade_file, widgets)
        self.content.unparent()

        self.store = storage.MappedListStore(self.get_type_map())
        self.top_view.set_model(self.store)

        selection = self.top_view.get_selection()
        selection.connect('changed', self._selection_callback)

    def add_text_column(self, name, store_key, expand=False):
        text_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name,
                                    text_renderer,
                                    text=self.store[store_key])
        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(text_renderer, 'xalign', self.store['align'])

        column.add_attribute(text_renderer, 'cell-background',
                             self.store['background'])

        self.top_view.append_column(column)

    def add_date_column(self, name, store_key, expand=False):
        date_renderer = CellRendererDate()
        column = gtk.TreeViewColumn(name,
                                    date_renderer,
                                    date=self.store[store_key])
        if expand:
            column.set_expand(True)
        else:
            column.add_attribute(date_renderer, 'xalign', self.store['align'])

        column.add_attribute(date_renderer, 'cell-background',
                             self.store['background'])

        self.top_view.append_column(column)

    def get_content(self):
        return self.content

    def _selection_callback(self, treeselection):
        selection = SelectionWrapper(treeselection, self.store)

        if selection.is_valid():
            self.on_selection(selection)

    def on_selection(self, selection):
        pass

class SelectionWrapper(object):

    def __init__(self, treeselection, store):
        self.model, self.tree_iter = treeselection.get_selected()
        self.store = store

    def is_valid(self):
        return self.tree_iter is not None

    def __getitem__(self, key):
        return self.model.get_value(self.tree_iter, self.store[key])


class ProductsTable(object):

    def __init__(self, table_widget, yes_id=gtk.STOCK_APPLY,
                 no_id=gtk.STOCK_REMOVE):
        """
        Create a new products table, populating the gtk.TreeView.

        yes_id and no_id are GTK constants that specify the icon to
        use for representing if a product is installed.
        """

        self.table_widget = table_widget
        self.product_store = gtk.ListStore(str, gtk.gdk.Pixbuf)
        table_widget.set_model(self.product_store)

        self.yes_icon = self._render_icon(yes_id)
        self.no_icon = self._render_icon(no_id)
        self.product_dir = ProductDirectory()

        name_column = gtk.TreeViewColumn(_("Product"),
                                         gtk.CellRendererText(),
                                         text=0)
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

    def _render_icon(self, icon_id):
        return self.table_widget.render_icon(icon_id, gtk.ICON_SIZE_MENU)

    def _get_icon(self, product_id):
        if self.product_dir.findByProduct(product_id):
            return self.yes_icon
        else:
            return self.no_icon

class SubDetailsWidget(GladeWidget):

    def __init__(self, show_contract=True):
        widget_names = ["sub_details_vbox", "subscription_text", "products_view"]
        super(SubDetailsWidget, self).__init__("subdetails.glade", widget_names)

        self.show_contract = show_contract
        self.sub_details_vbox.unparent()

        # Clean out contract and date widgets if not showing contract info
        if not show_contract:
            def destroy(widget_name):
                self.glade.get_widget(widget_name).destroy()

            destroy('contract_number_label')
            destroy('contract_number_text')
            destroy('start_date_label')
            destroy('start_date_text')
            destroy('expiration_date_label')
            destroy('expiration_date_text')
            destroy('account_label')
            destroy('account_text')
        else:
            self.pull_widgets(["contract_number_text", "start_date_text",
                               "expiration_date_text", "account_text"])

        self.bundled_products = ProductsTable(self.products_view)

    def show(self, name, contract=None, start=None, end=None, account=None,
            products=[]):
        """
        Show subscription details.

        Start and end should be formatted strings, not actual date objects.
        Products is a list of tuples in the format (name, id)
        """
        self.subscription_text.get_buffer().set_text(name)

        if self.show_contract:
            self._set(self.contract_number_text, contract)
            self._set(self.start_date_text,
                    managerlib.formatDate(start).strftime("%x"))
            self._set(self.expiration_date_text,
                    managerlib.formatDate(end).strftime("%x"))
            self._set(self.account_text, account)

        self.bundled_products.clear()
        for product in products:
            self.bundled_products.add_product(product[0], product[1])

    def _set(self, text_view, text):
        """Set the buffer of the given TextView to contain the text"""
        if text:
            text_view.get_buffer().set_text(text)

    def clear(self):
        """ No subscription to display. """
        pass

    def get_widget(self):
        """ Returns the widget to be packed into a parent window. """
        return self.sub_details_vbox


class CellRendererDate(gtk.CellRendererText):

    """
    Custom cell renderer to display the date in the user's locale.
    """

    __gproperties__ = {
            'date' : (gobject.TYPE_STRING, 'date', 'date displayed', '',
                gobject.PARAM_READWRITE)
    }

    def __init__(self):
        self.__gobject_init__()

    def do_set_property(self, property, value):
        """
        called to set the date property for rendering in a cell.
        we convert to display in the user's locale, then pass on to the cell
        renderer.
        """

        if value:
            date = managerlib.formatDate(value).strftime("%x")
        else:
            date = value
        gtk.CellRendererText.set_property(self, 'text', date)
