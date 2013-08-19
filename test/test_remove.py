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

from stubs import StubUEP, StubEntitlementDirectory, StubProductDirectory
from stubs import StubConsumerIdentity, StubEntCertLib, StubEntitlementCertificate
from stubs import StubProduct
import rhsm.connection as connection
from subscription_manager import managercli
import subscription_manager.injection as inj
from fixture import SubManFixture


# This is a copy of CliUnSubscribeTests for the new name.
class CliRemoveTests(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.oldCI = managercli.ConsumerIdentity

    def test_unsubscribe_registered(self):
        connection.UEPConnection = StubUEP

        cmd = managercli.RemoveCommand()

        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: True)
        StubConsumerIdentity.exists = classmethod(lambda cls: True)
        managercli.EntCertLib = StubEntCertLib

        cmd.main(['remove', '--all'])
        self.assertEquals(cmd.cp.called_unbind_uuid,
                          StubConsumerIdentity.CONSUMER_ID)

        serial1 = '123456'
        cmd.main(['remove', '--serial=%s' % serial1])
        self.assertEquals(cmd.cp.called_unbind_serial, [serial1])

        serial2 = '789012'
        cmd.main(['remove', '--serial=%s' % serial1, '--serial=%s' % serial2])
        self.assertEquals(cmd.cp.called_unbind_serial, [serial1, serial2])

    def test_unsubscribe_unregistered(self):
        connection.UEPConnection = StubUEP

        prod = StubProduct('stub_product')
        ent = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR,
                StubEntitlementDirectory([ent]))
        inj.provide(inj.PROD_DIR,
                StubProductDirectory([]))
        cmd = managercli.RemoveCommand()

        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: False)
        StubConsumerIdentity.exists = classmethod(lambda cls: False)

        cmd.main(['remove', '--all'])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent.is_deleted)

        prod = StubProduct('stub_product')
        ent1 = StubEntitlementCertificate(prod)
        ent2 = StubEntitlementCertificate(prod)
        ent3 = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR,
                StubEntitlementDirectory([ent1, ent2, ent3]))
        inj.provide(inj.PROD_DIR,
                StubProductDirectory([]))
        cmd = managercli.RemoveCommand()
        managercli.ConsumerIdentity = StubConsumerIdentity
        StubConsumerIdentity.existsAndValid = classmethod(lambda cls: False)
        StubConsumerIdentity.exists = classmethod(lambda cls: False)

        cmd.main(['remove', '--serial=%s' % ent1.serial, '--serial=%s' % ent3.serial])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent1.is_deleted)
        self.assertFalse(ent2.is_deleted)
        self.assertTrue(ent3.is_deleted)

    def tearDown(self):
        managercli.ConsumerIdentity = self.oldCI
