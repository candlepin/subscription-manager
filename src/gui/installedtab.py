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

import gtk

from datetime import datetime

import widgets
import storage
from certlib import EntitlementDirectory, ProductDirectory
from certificate import GMT
from managerlib import formatDate

import gettext
_ = gettext.gettext
gettext.textdomain('subscription-manager')
gtk.glade.bindtextdomain('subscription-manager')

class InstalledProductsTab(widgets.GladeWidget):

    def __init__(self, backend, consumer, facts):
    
        widget_names = ['product_view', 'content']
        super(InstalledProductsTab, self).__init__('installed.glade', widget_names)
        
        self.product_dir = ProductDirectory()
        self.entitlement_dir = EntitlementDirectory()
        
        type_map = {
            'product': str,
            'version': str,
            'status': str,
            'contract': str,
            'start_date': str,
            'expiration_date': str,
            'serial': str,
            'align': float,
            'background': str
        }
        
        self.store = storage.MappedListStore(type_map)
        self.product_view.set_model(self.store)
        
        # TODO:  copy-paste from mysubstab - refactor this!
        def add_column(name, column_number, expand=False):
            text_renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name, text_renderer, text=column_number)
            if expand:
                column.set_expand(True)
            else:
                column.add_attribute(text_renderer, 'xalign', self.store['align'])

            column.add_attribute(text_renderer, 'cell-background', 
                                 self.store['background'])

            self.product_view.append_column(column)
            
        add_column(_('Product'), self.store['product'], True)
        add_column(_('Version'), self.store['version'])
        add_column(_('Compliance Status'), self.store['status'])
        add_column(_('Contract'), self.store['contract'])
        add_column(_('Start Date'), self.store['start_date'])
        add_column(_('Expiration Date'), self.store['expiration_date'])
 
        self.update_products()
        
    def update_products(self):
        for product_cert in self.product_dir.list():
            for product in product_cert.getProducts():
                product_hash = product.getHash()
                entitlement_cert = self.entitlement_dir.findByProduct(product_hash)
                   
                entry = {}
                entry['product'] = product.getName()
                entry['version'] = product.getVersion()
                # Common properties
                entry['align'] = 0.5
                
                if entitlement_cert:
                    order = entitlement_cert.getOrder()
                
                    entry['contract'] = order.getContract()
                    entry['start_date'] = formatDate(order.getStart())
                    entry['expiration_date'] = formatDate(order.getEnd())
                    
                    # TODO:  Pull this date logic out into a separate lib!
                    #        This is also used in mysubstab...
                    date_range = entitlement_cert.validRange()
                    now = datetime.now(GMT())
                    
                    if now < date_range.begin():
                        entry['status'] = _('Future Subscription')
                    elif now > date_range.end():
                        entry['status'] = _('Out of Compliance')                    
                    else:
                        entry['status'] = _('In Compliance')
                else:
                    entry['status'] = _('Out of Compliance')
                
                self.store.add_map(entry)
    
    def get_content(self):
        return self.content

    def get_label(self):
        return _('My Installed Software')
