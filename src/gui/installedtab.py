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
from certlib import EntitlementDirectory, ProductDirectory
from certificate import GMT
from managerlib import formatDate

import gettext
_ = gettext.gettext
gettext.textdomain('subscription-manager')
gtk.glade.bindtextdomain('subscription-manager')

class InstalledProductsTab(widgets.SubscriptionManagerTab):

    def __init__(self, backend, consumer, facts):
    
        super(InstalledProductsTab, self).__init__('installed.glade')
        
        self.product_dir = ProductDirectory()
        self.entitlement_dir = EntitlementDirectory()
        
        self.add_text_column(_('Product'), 'product', True)
        self.add_text_column(_('Version'), 'version')
        self.add_text_column(_('Compliance Status'), 'status')
        self.add_text_column(_('Contract'), 'contract')
        self.add_text_column(_('Start Date'), 'start_date')
        self.add_text_column(_('Expiration Date'), 'expiration_date')
 
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

    def get_type_map(self):
        return {
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

    def get_label(self):
        return _('My Installed Software')
