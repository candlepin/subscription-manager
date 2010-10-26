
#
# GUI Module for standalone subscription-manager - 'Bundled Products' table
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Justin Harris <jharris@redhat.com>
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

import gtk

from certlib import EntitlementDirectory, ProductDirectory

import logutil
log = logutil.getLogger(__name__)

import gettext
_ = gettext.gettext
gettext.textdomain("subscription-manager")
gtk.glade.bindtextdomain("subscription-manager")

class ProductsTable:

    def __init__(self, table_widget, yes_id=gtk.STOCK_APPLY, no_id=gtk.STOCK_REMOVE):
        self.table_widget = table_widget
        self.yes_icon = self._render_icon(yes_id)
        self.no_icon = self._render_icon(no_id)

        self.product_store = gtk.ListStore(str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf)
        table_widget.set_model(self.product_store)

        name_column = gtk.TreeViewColumn(_("Product"), \
                                         gtk.CellRendererText(), \
                                         text=0)
        name_column.set_expand(True)

        pix_renderer = gtk.CellRendererPixbuf()
        installed_column = gtk.TreeViewColumn(_("Installed"), pix_renderer, pixbuf=1)
        hardware_column = gtk.TreeViewColumn(_("H/W Compatible"), pix_renderer, pixbuf=2)

        table_widget.append_column(name_column)
        table_widget.append_column(installed_column)
        table_widget.append_column(hardware_column)

        # Temp sample data
        self.product_store.append(['Some Product', self.no_icon, self.yes_icon])
        self.product_store.append(['Another', self.no_icon, self.no_icon])
        self.product_store.append(['Installed Product', self.yes_icon, self.yes_icon])

    def _render_icon(self, icon_id):
        return self.table_widget.render_icon(icon_id, gtk.ICON_SIZE_MENU)
        
