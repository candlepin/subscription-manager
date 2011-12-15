#
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

from math import ceil


class QuantityDefaultValueCalculator(object):
    """
    A class that calculates the default quantity value for a subscription.
    """
    _SOCKET_FACT_NAME = 'cpu.cpu_socket(s)'
    _SOCKETS_PROD_ATTR_NAME = 'sockets'

    _CPUS_FACT_NAME = 'cpu.cpu(s)'
    _CPUS_PROD_ATTR_NAME = 'vcpu'

    _VIRT_IS_GUEST_FACT_NAME = "virt.is_guest"

    def __init__(self, facts, current_entitlements):
        self.fact_dict = facts.get_facts()
        self.current_entitlements = current_entitlements

    def calculate(self, pool):
        product_attrs = self._flatten_attributes(pool, 'productAttributes')

        if not allows_multi_entitlement(pool):
            return 1

        pool_product_id = pool['productId']
        total_consumed = self._get_total_consumed(pool_product_id)

        if self._is_virtual_machine():
            allowed = self._get_allowed_quantity_for_virtual_machine(product_attrs)
        else:
            allowed = self._get_allowed_quantity_for_physical_machine(product_attrs)

        default_value = allowed - total_consumed
        if default_value < 0:
            default_value = 0
        return default_value

    def _is_virtual_machine(self):
        return self._VIRT_IS_GUEST_FACT_NAME in self.fact_dict and \
            self.fact_dict[self._VIRT_IS_GUEST_FACT_NAME]

    def _get_total_consumed(self, product_id):
        """
        Determines how many entitlements are currently consumed based on the specified
        product id. The product id is checked against the Order SKU in the certificate.
        """
        total_consumed = 0
        for cert in self.current_entitlements:
            order = cert.getOrder()
            if order.getSku() == product_id and cert.validRange().hasNow():
                total_consumed += int(order.getQuantityUsed())
        return total_consumed

    def _get_allowed_quantity_for_virtual_machine(self, product_attrs):
        # Default for physical machine is calculated as:
        # - if product vcpu attribute is set then, machine cpus / product vcpu
        # - if no vcpu, then, machine_sockets / product_sockets
        # - if no sockets and vcpu, then, 1
        if self._CPUS_PROD_ATTR_NAME in product_attrs:
            machine_val = self._get_float_from_dict(self.fact_dict, self._CPUS_FACT_NAME)
            product_val = self._get_float_from_dict(product_attrs, self._CPUS_PROD_ATTR_NAME)
        elif self._SOCKETS_PROD_ATTR_NAME in product_attrs:
            machine_val = self._get_float_from_dict(self.fact_dict, self._SOCKET_FACT_NAME)
            product_val = self._get_float_from_dict(product_attrs, self._SOCKETS_PROD_ATTR_NAME)
        else:
            return 1

        return ceil(machine_val / product_val)

    def _get_allowed_quantity_for_physical_machine(self, product_attrs):
        # Default for physical machine is calculated as:
        # machine sockets / product socket
        machine_sockets = self._get_float_from_dict(self.fact_dict, self._SOCKET_FACT_NAME)
        product_sockets = self._get_float_from_dict(product_attrs, self._SOCKETS_PROD_ATTR_NAME)
        return ceil(machine_sockets / product_sockets)

    def _get_float_from_dict(self, target_dict, name):
        """
        Pulls a value from a dictionary and converts it to a float. If the dictionary
        does not define the specified property, returns 1.0
        """
        value = 1
        if name in target_dict and target_dict[name]:
            value = target_dict[name]
        return float(value)

    def _flatten_attributes(self, pool_json, attribute_list_name):
        """
        Flatten the attributes in a pool's JSON data by attribute list name.
        """
        flattened = {}
        for attribute in pool_json[attribute_list_name]:
            flattened[attribute['name']] = attribute['value']

        return flattened


def valid_quantity(quantity):
    if not quantity:
        return False

    try:
        return int(quantity) > 0
    except ValueError:
        return False


def allows_multi_entitlement(pool):
    """
    Determine if this pool allows multi-entitlement based on the pool's
    top-level product's multi-entitlement attribute.
    """
    for attribute in pool['productAttributes']:
        if attribute['name'] == "multi-entitlement" and \
            (attribute['value'].lower() == "yes" or attribute['value'] == "1"):
            return True
    return False
