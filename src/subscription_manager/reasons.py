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

import gettext
_ = gettext.gettext


class Reasons(object):
    """
    Holds reasons and parses them for
    the client.
    """

    def __init__(self, reasons, sorter):
        self.reasons = reasons
        self.sorter = sorter

    def get_subscription_reasons_map(self):
        """
        returns a dictionary that maps
        subscriptions to lists of reasons
        """
        result = {}
        for s in self.sorter.valid_entitlement_certs:
            result[s.subject['CN']] = []

        for reason in self.reasons:
            if 'entitlement_id' in reason['attributes']:
                if reason['message'] not in result[reason['attributes']['entitlement_id']]:
                    result[reason['attributes']['entitlement_id']].append(reason['message'])
            elif 'stack_id' in reason['attributes']:
                for s in self.get_stack_subscriptions(reason['attributes']['stack_id']):
                    if reason['message'] not in result[s]:
                        result[s].append(reason['message'])
        return result

    def get_name_message_map(self):
        result = {}
        for reason in self.reasons:
            if reason['attributes']['name'] not in result:
                result[reason['attributes']['name']] = []
            if reason['message'] not in result[reason['attributes']['name']]:
                result[reason['attributes']['name']].append(reason['message'])
        return result

    def get_stack_subscriptions(self, stack_id):
        result = set([])
        for s in self.sorter.valid_entitlement_certs:
            if s.order.stacking_id:
                if s.order.stacking_id == stack_id:
                    result.add(s.subject['CN'])
        return list(result)

    def get_reasons_messages(self):
        # Returns a list of tuples (offending name, message)
        # we want non-covered (red) reasons first,
        # then arch-mismatch, then others (sockets/ram/cores/etc...)
        order = ['NOTCOVERED', 'ARCH']
        result_map = {}
        result = []
        for reason in self.reasons:
            if reason['key'] not in result_map:
                result_map[reason['key']] = []
            if 'name' in reason['attributes']:
                name = reason['attributes']['name']
            else:
                name = self.get_reason_id(reason)
            result_map[reason['key']].append((name, reason['message']))
        for item in order:
            if item in result_map:
                for message in result_map[item]:
                    if message not in result:
                        result.append(message)
                del result_map[item]
        for key, messages in result_map.items():
            for message in messages:
                if message not in result:
                    result.append(message)
        return result

    def get_reason_id(self, reason):
        # returns ent/prod/stack id
        # ex: Subscription 123456
        if 'product_id' in reason['attributes']:
            return _('Product ') + reason['attributes']['product_id']
        elif 'entitlement_id' in reason['attributes']:
            return _('Subscription ') + reason['attributes']['entitlement_id']
        elif 'stack_id' in reason['attributes']:
            return _('Stack ') + reason['attributes']['stack_id']
        else:
            # Shouldn't be reachable.
            # Reason has no id attr
            return _('Unknown')

    def get_product_reasons(self, prod):
        """
        Returns a list of reason messages that
        apply to the installed product
        """
        # If the prod is in valid_prod, we don't want
        # reasons here.  If they exist, they're from
        # overconsumption.
        if prod.id in self.sorter.valid_products:
            return []

        result = set([])
        subscriptions = self.get_product_subscriptions(prod)

        sub_ids = []
        stack_ids = []

        for s in subscriptions:
            if 'CN' in s.subject:
                sub_ids.append(s.subject['CN'])
            if s.order.stacking_id:
                stack_ids.append(s.order.stacking_id)
        for reason in self.reasons:
            if 'product_id' in reason['attributes']:
                if reason['attributes']['product_id'] == prod.id:
                    result.add(reason['message'])
            elif 'entitlement_id' in reason['attributes']:
                if reason['attributes']['entitlement_id'] in sub_ids:
                    result.add(reason['message'])
            elif 'stack_id' in reason['attributes']:
                if reason['attributes']['stack_id'] in stack_ids:
                    result.add(reason['message'])
        return list(result)

    def get_product_subscriptions(self, prod):
        """
        Returns a list of subscriptions that provide
        the product.
        """
        results = []
        for valid_ent in self.sorter.valid_entitlement_certs:
            if prod in valid_ent.products:
                results.append(valid_ent)
        return results
