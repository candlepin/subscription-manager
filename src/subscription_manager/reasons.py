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

from subscription_manager.i18n import ugettext as _


class Reasons(object):
    """
    Holds reasons and parses them for
    the client.
    """

    def __init__(self, reasons, sorter):
        self.reasons = reasons
        self.sorter = sorter

    def get_subscription_reasons(self, sub_id):
        """
        returns reasons for sub_id, or empty list
        if there are none.
        """
        return self.get_subscription_reasons_map().get(sub_id, [])

    def get_subscription_reasons_map(self):
        """
        returns a dictionary that maps
        valid entitlements to lists of reasons.
        """
        result = {}
        for s in self.sorter.valid_entitlement_certs:
            result[s.subject['CN']] = []

        for reason in self.reasons:
            if 'entitlement_id' in reason['attributes']:
                # Note 'result' won't have entries for any expired certs, so
                # result['some_ent_that_has_expired'] could throw a KeyError
                ent_id = reason['attributes']['entitlement_id']
                if ent_id in result:
                    if reason['message'] in result[ent_id]:
                        continue

                    result[ent_id].append(reason['message'])

            elif 'stack_id' in reason['attributes']:
                for s_id in self.get_stack_subscriptions(reason['attributes']['stack_id']):
                    if reason['message'] in result[s_id]:
                        continue
                    result[s_id].append(reason['message'])
        return result

    def get_name_message_map(self):
        result = {}
        for reason in self.reasons:
            reason_name = reason['attributes']['name']
            if reason_name not in result:
                result[reason_name] = []
            if reason['message'] in result[reason_name]:
                continue
            result[reason_name].append(reason['message'])
        return result

    def get_stack_subscriptions(self, stack_id):
        result = set([])
        for s in self.sorter.valid_entitlement_certs:
            if s.order.stacking_id and s.order.stacking_id == stack_id:
                result.add(s.subject['CN'])
        return list(result)

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
        results = [valid_ent for valid_ent in self.sorter.valid_entitlement_certs
                if prod in valid_ent.products]
        return results
