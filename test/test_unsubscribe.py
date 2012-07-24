#
# Copyright (c) 2012 Red Hat, Inc.
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
import unittest

from stubs import StubUEP, StubEntitlementDirectory, StubProductDirectory
from stubs import StubConsumerIdentity, StubCertLib, StubEntitlementCertificate
from stubs import StubProduct
import rhsm.connection as connection
from subscription_manager import managercli


class CliUnSubscribeTests(unittest.TestCase):

    def test_unsubscribe_registered(self):
        connection.UEPConnection = StubUEP

        cmd = managercli.UnSubscribeCommand(ent_dir=StubEntitlementDirectory([]),
                              prod_dir=StubProductDirectory([]))

        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: True)
        StubConsumerIdentity.exists = classmethod(lambda cls: True)
        managercli.CertLib = StubCertLib

        cmd.main(['unsubscribe', '--all'])
        self.assertEquals(cmd.cp.called_unbind_uuid,
                          StubConsumerIdentity.CONSUMER_ID)

        serial = '123456'
        cmd.main(['unsubscribe', '--serial=%s' % serial])
        self.assertEquals(cmd.cp.called_unbind_serial, serial)

    def test_unsubscribe_unregistered(self):
        connection.UEPConnection = StubUEP

        prod = StubProduct('stub_product')
        ent = StubEntitlementCertificate(prod)

        cmd = managercli.UnSubscribeCommand(ent_dir=StubEntitlementDirectory([ent]),
                              prod_dir=StubProductDirectory([]))

        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: False)
        StubConsumerIdentity.exists = classmethod(lambda cls: False)

        cmd.main(['unsubscribe', '--all'])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent.is_deleted)

        prod = StubProduct('stub_product')
        ent1 = StubEntitlementCertificate(prod)
        ent2 = StubEntitlementCertificate(prod)

        cmd = managercli.UnSubscribeCommand(ent_dir=StubEntitlementDirectory([ent1, ent2]),
                              prod_dir=StubProductDirectory([]))
        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: False)
        StubConsumerIdentity.exists = classmethod(lambda cls: False)

        cmd.main(['unsubscribe', '--serial=%s' % ent1.serial])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent1.is_deleted)
        self.assertFalse(ent2.is_deleted)
