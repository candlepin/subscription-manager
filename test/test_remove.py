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

from subscription_manager import managercli
from subscription_manager import injection as inj

from stubs import StubEntitlementDirectory, StubProductDirectory, StubEntActionInvoker, \
        StubEntitlementCertificate, StubProduct, StubPool
import fixture


# This is a copy of CliUnSubscribeTests for the new name.
class CliRemoveTests(fixture.SubManFixture):

    def setUp(self):
        super(CliRemoveTests, self).setUp()

    def test_unsubscribe_registered(self):
        cmd = managercli.RemoveCommand()

        mock_identity = self._inject_mock_valid_consumer()
        managercli.EntCertActionInvoker = StubEntActionInvoker

        cmd.main(['remove', '--all'])
        self.assertEquals(cmd.cp.called_unbind_uuid, mock_identity.uuid)

        serial1 = '123456'
        cmd.main(['remove', '--serial=%s' % serial1])
        self.assertEquals(cmd.cp.called_unbind_serial, [serial1])
        cmd.cp.reset()

        serial2 = '789012'
        cmd.main(['remove', '--serial=%s' % serial1, '--serial=%s' % serial2])
        self.assertEquals(cmd.cp.called_unbind_serial, [serial1, serial2])
        cmd.cp.reset()

        pool_id1 = '39993922b'
        cmd.main(['remove', '--serial=%s' % serial1, '--serial=%s' % serial2, '--pool=%s' % pool_id1, '--pool=%s' % pool_id1])
        self.assertEquals(cmd.cp.called_unbind_serial, [serial1, serial2])
        self.assertEquals(cmd.cp.called_unbind_pool_id, [pool_id1])

    def test_unsubscribe_unregistered(self):
        prod = StubProduct('stub_product')
        ent = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR, StubEntitlementDirectory([ent]))
        inj.provide(inj.PROD_DIR, StubProductDirectory([]))
        cmd = managercli.RemoveCommand()

        self._inject_mock_invalid_consumer()

        cmd.main(['remove', '--all'])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent.is_deleted)

        prod = StubProduct('stub_product')
        pool = StubPool('stub_pool')
        ent1 = StubEntitlementCertificate(prod)
        ent2 = StubEntitlementCertificate(prod)
        ent3 = StubEntitlementCertificate(prod)
        ent4 = StubEntitlementCertificate(prod, pool=pool)

        inj.provide(inj.ENT_DIR, StubEntitlementDirectory([ent1, ent2, ent3, ent4]))
        inj.provide(inj.PROD_DIR, StubProductDirectory([]))
        cmd = managercli.RemoveCommand()

        cmd.main(['remove', '--serial=%s' % ent1.serial, '--serial=%s' % ent3.serial, '--pool=%s' % ent4.pool.id])
        self.assertTrue(cmd.entitlement_dir.list_called)
        self.assertTrue(ent1.is_deleted)
        self.assertFalse(ent2.is_deleted)
        self.assertTrue(ent3.is_deleted)
        self.assertTrue(ent4.is_deleted)
