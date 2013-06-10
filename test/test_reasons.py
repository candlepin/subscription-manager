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

from stubs import StubEntitlementCertificate, StubProduct
from mock import Mock
import unittest
from subscription_manager.reasons import Reasons

INST_PID_1 = "100000000000002"  # awesomeos 64
ENT_ID_1 = "ff8080813e468fd8013e4690966601d7"
INST_PID_2 = "100000000000003"  # ppc64 awesomeos
ENT_ID_2 = "ff8080813e468fd8013e4694a4921179"
INST_PID_3 = "801"  # non-entitled ram limiting product
INST_PID_4 = "900"  # multiattr stack
ENT_ID_4 = "ff8080813e468fd8013e4690f041031b"
STACK_1 = 'multiattr-stack-test'  # multiattr
STACK_2 = '1'  # awesomeos 64

PARTIAL_STACK_ID = STACK_1
PROD_4 = StubProduct(INST_PID_4,
        name="Multi-Attribute Stackable")
PROD_2 = StubProduct(INST_PID_2,
        name="Awesome OS for ppc64")
PROD_1 = StubProduct(INST_PID_1,
        name="Awesome OS for x86_64")


class ReasonsTests(unittest.TestCase):

    def setUp(self):
        self.sorter = Mock()
        self.sorter.valid_products = [INST_PID_1]
        self.sorter.valid_entitlement_certs = [StubEntitlementCertificate(PROD_2, ent_id=ENT_ID_2),
                StubEntitlementCertificate(PROD_1, ent_id=ENT_ID_1),
                StubEntitlementCertificate(product=PROD_4, stacking_id=STACK_1,
                    ent_id=ENT_ID_4),
                StubEntitlementCertificate(StubProduct('not_installed_product',
                    name="Some Product"),
                    ent_id="SomeSubId")]
        reason_list = []
        reason_list.append(self.build_reason('NOTCOVERED',
            'Not covered by a valid subscription.',
            {'product_id': '801',
             'name': 'RAM Limiting Product'}))
        reason_list.append(self.build_ent_reason_with_attrs('CORES',
            'Only covers 16 of 32 cores.',
            '32', '16', name='Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)',
            stack='multiattr-stack-test'))
        reason_list.append(self.build_ent_reason_with_attrs('SOCKETS',
            'Only covers 4 of 8 sockets.',
            '8', '4', name='Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)',
            stack='multiattr-stack-test'))
        reason_list.append(self.build_ent_reason_with_attrs('RAM',
            'Only covers 8GB of 31GB of RAM.',
            '31', '8', name='Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)',
            stack='multiattr-stack-test'))
        reason_list.append(self.build_ent_reason_with_attrs('ARCH',
            'Covers architecture ppc64 but the system is x86_64.',
            'x86_64', 'ppc64', name='Awesome OS for ppc64',
            ent='ff8080813e468fd8013e4694a4921179'))

        self.sorter.reasons = Reasons(reason_list, self.sorter)

    def test_get_stack_subscriptions(self):
        subs = self.sorter.reasons.get_stack_subscriptions(PARTIAL_STACK_ID)
        self.assertEquals(1, len(subs))
        self.assertEquals(ENT_ID_4, subs[0])

    def test_get_product_subscriptions(self):
        subs = self.sorter.reasons.get_product_subscriptions(PROD_4)
        self.assertEquals(1, len(subs))
        self.assertEquals(ENT_ID_4, subs[0].subject['CN'])

    def test_get_product_reasons(self):
        messages = self.sorter.reasons.get_product_reasons(PROD_4)
        self.assertEquals(3, len(messages))
        expectations = []
        expectations.append("Only covers 16 of 32 cores.")
        expectations.append("Only covers 8GB of 31GB of RAM.")
        expectations.append("Only covers 4 of 8 sockets.")
        for expected in expectations:
            self.assertTrue(expected in messages)
        messages = self.sorter.reasons.get_product_reasons(PROD_2)
        self.assertEquals(1, len(messages))
        expected = "Covers architecture ppc64 but the system is x86_64."
        self.assertEquals(expected, messages[0])
        reason = self.build_ent_reason_with_attrs('SOCKETS', 'some message', '8', '6',
                prod=INST_PID_1, name="Awesome OS for x86_64")
        self.sorter.reasons.reasons.append(reason)
        messages = self.sorter.reasons.get_product_reasons(PROD_1)
        self.assertEquals(0, len(messages))
        self.sorter.reasons.reasons.remove(reason)

    def test_get_subscription_reasons_map(self):
        sub_reason_map = self.sorter.reasons.get_subscription_reasons_map()
        self.assertEquals(3, len(sub_reason_map[ENT_ID_4]))
        self.assertEquals(0, len(sub_reason_map[ENT_ID_1]))
        self.assertEquals(1, len(sub_reason_map[ENT_ID_2]))
        expected = "Covers architecture ppc64 but the system is x86_64."
        actual = sub_reason_map[ENT_ID_2][0]
        self.assertEquals(expected, actual)

    def test_get_reason_id(self):
        reason = self.build_ent_reason_with_attrs(
                'SOCKETS', 'some message', '8', '6', ent='1234')
        reason_id = self.sorter.reasons.get_reason_id(reason)
        self.assertEquals("Subscription 1234", reason_id)
        reason = self.build_ent_reason_with_attrs(
                'SOCKETS', 'some message', '8', '6', stack='1234')
        reason_id = self.sorter.reasons.get_reason_id(reason)
        self.assertEquals("Stack 1234", reason_id)
        reason = self.build_ent_reason_with_attrs(
                'SOCKETS', 'some message', '8', '6', prod='1234')
        reason_id = self.sorter.reasons.get_reason_id(reason)
        self.assertEquals("Product 1234", reason_id)

    def test_get_name_message_map(self):
        name_message_map = self.sorter.reasons.get_name_message_map()
        self.assertEquals(3, len(name_message_map))
        expected = ['Only covers 16 of 32 cores.',
            'Only covers 4 of 8 sockets.',
            'Only covers 8GB of 31GB of RAM.']
        self.assortEquals(expected, name_message_map[
            'Multi-Attribute Stackable (16 cores, 4 sockets, 8GB RAM)'])

    def set_up_duplicates(self):
        self.sorter.reasons.reasons = []
        self.sorter.reasons.reasons.append(self.build_ent_reason_with_attrs(
            'SOCKETS', 'some message', '8', '6', ent='1234', name='testing'))
        self.sorter.reasons.reasons.append(self.build_ent_reason_with_attrs(
            'SOCKETS', 'some message', '8', '6', ent='2345', name='testing'))
        self.sorter.reasons.reasons.append(self.build_ent_reason_with_attrs(
            'SOCKETS', 'some message', '8', '6', ent='3345', name='testing'))

    def build_ent_reason_with_attrs(self, key, message, has,
            covered, name=None, ent=None, stack=None, prod=None):
        attrs = {'has': has,
                'covered': covered}
        if name:
            attrs['name'] = name
        if ent:
            attrs['entitlement_id'] = ent
        elif stack:
            attrs['stack_id'] = stack
        elif prod:
            attrs['product_id'] = prod
        return self.build_reason(key, message, attrs)

    def build_reason(self, key, message, attrs):
        return {'key': key,
                'message': message,
                'attributes': attrs}

    def assortEquals(self, list_a, list_b):
        self.assertTrue(isinstance(list_a, list) and isinstance(list_b, list))
        self.assertEquals(sorted(list_a), sorted(list_b))
