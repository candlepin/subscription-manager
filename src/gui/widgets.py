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
import gtk

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

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
        Products is a list of tuples (or lists) of the form (name, id)
        """
        self.subscription_text.get_buffer().set_text(name)

        if self.show_contract:
            self._set(self.contract_number_text, contract)
            self._set(self.start_date_text, start)
            self._set(self.expiration_date_text, end)
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

