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

# This module contains wrappers for JSON returned from the CP server.
from subscription_manager.utils import is_true_value


class PoolWrapper(object):

    def __init__(self, pool_json):
        self.data = pool_json

    def get_id(self):
        return self.data.get('id')

    def is_virt_only(self):
        attributes = self.data['attributes']
        virt_only = False
        for attribute in attributes:
            name = attribute['name']
            value = attribute['value']
            if name == "virt_only":
                virt_only = is_true_value(value)
                break

        return virt_only

    def management_enabled(self):
        return is_true_value(self._get_attribute_value('productAttributes', 'management_enabled'))

    def get_stacking_id(self):
        return self._get_attribute_value('productAttributes', 'stacking_id')

    def get_service_level(self):
        return self._get_attribute_value('productAttributes', 'support_level')

    def get_service_type(self):
        return self._get_attribute_value('productAttributes', 'support_type')

    def get_product_attributes(self, *attribute_names):
        attrs = {}

        if 'productAttributes' not in self.data:
            return attrs

        # Initialize all requested attribute names to have a value
        # of None
        for attr_name in attribute_names:
            attrs[attr_name] = None

        for attr in self.data['productAttributes']:
            name = attr['name']
            if name in attribute_names:
                attrs[name] = attr['value']
        return attrs

    def get_suggested_quantity(self):
        result = None

        try:
            result = int(self.data['calculatedAttributes']['suggested_quantity'])
        except:
            pass

        return result

    def get_pool_type(self):
        return (self.data.get('calculatedAttributes') or {}).get('compliance_type', '')

    def _get_attribute_value(self, attr_list_name, attr_name):
        product_attrs = self.data[attr_list_name]
        for attribute in product_attrs:
            name = attribute['name']
            value = attribute['value']
            if name == attr_name and value:
                return value
        return None

    def get_provided_products(self):
        products = self.data.get('providedProducts', [])
        return [prod.get('productName') for prod in products]
