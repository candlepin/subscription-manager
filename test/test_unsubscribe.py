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
import mock

from stubs import StubEntitlementDirectory, StubProductDirectory
from stubs import StubEntActionInvoker, StubEntitlementCertificate
from stubs import StubProduct
from fixture import SubManFixture, Capture
import rhsm.connection as connection
from subscription_manager import managercli
from subscription_manager import injection as inj


# This is a dupe of test_remove
class CliUnSubscribeTests(SubManFixture):

    def setUp(self):
        super(CliUnSubscribeTests, self).setUp()

    def test_unsubscribe_registered(self):
        prod = StubProduct('stub_product')
        ent1 = StubEntitlementCertificate(prod)
        ent2 = StubEntitlementCertificate(prod)
        ent3 = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR,
                StubEntitlementDirectory([ent1, ent2, ent3]))
        inj.provide(inj.PROD_DIR,
                StubProductDirectory([]))
        cmd = managercli.UnSubscribeCommand()

        mock_identity = self._inject_mock_valid_consumer()
        managercli.EntCertActionInvoker = StubEntActionInvoker

        with Capture(silent=True) as cap:
            cmd.main(['unsubscribe', '--all'])
            self.assertEquals(cmd.cp.called_unbind_uuid, mock_identity.uuid)
            self.assertTrue('deprecated' in cap.err)

        with Capture(silent=True) as cap:
            cmd.main(['unsubscribe', '--serial=%s' % ent1.serial])
            self.assertEquals(cmd.cp.called_unbind_serial, ['%s' % ent1.serial])
            self.assertTrue('deprecated' in cap.err)

        with Capture(silent=True) as cap:
            code = cmd.main(['unsubscribe', '--serial=%s' % ent2.serial, '--serial=%s' % ent3.serial])
            self.assertEquals(cmd.cp.called_unbind_serial, ['%s' % ent2.serial, '%s' % ent3.serial])
            self.assertEquals(code, 0)
            self.assertTrue('deprecated' in cap.err)

        self.stub_cp_provider.get_consumer_auth_cp().unbindBySerial = mock.Mock(
            side_effect=connection.RestlibException("Entitlement Certificate with serial number 2300922701043065601 could not be found.")
        )

        with Capture(silent=True) as cap:
            code = cmd.main(['unsubscribe', '--serial=%s' % '2300922701043065601'])
            self.assertEquals(code, 0)
            self.assertTrue('deprecated' in cap.err)

    def test_unsubscribe_unregistered(self):
        prod = StubProduct('stub_product')
        ent = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR,
                StubEntitlementDirectory([ent]))
        inj.provide(inj.PROD_DIR,
                StubProductDirectory([]))
        cmd = managercli.UnSubscribeCommand()

        self._inject_mock_invalid_consumer()

        with Capture(silent=True) as cap:
            cmd.main(['unsubscribe', '--all'])
            self.assertTrue(cmd.entitlement_dir.list_called)
            self.assertTrue(ent.is_deleted)
            self.assertTrue('deprecated' in cap.err)

        prod = StubProduct('stub_product')
        ent1 = StubEntitlementCertificate(prod)
        ent2 = StubEntitlementCertificate(prod)
        ent3 = StubEntitlementCertificate(prod)

        inj.provide(inj.ENT_DIR,
                StubEntitlementDirectory([ent1, ent2, ent3]))
        inj.provide(inj.PROD_DIR,
                StubProductDirectory([]))
        cmd = managercli.UnSubscribeCommand()

        with Capture(silent=True) as cap:
            code = cmd.main(['unsubscribe', '--serial=%s' % ent1.serial, '--serial=%s' % ent3.serial])
            self.assertTrue(cmd.entitlement_dir.list_called)
            self.assertTrue(ent1.is_deleted)
            self.assertFalse(ent2.is_deleted)
            self.assertTrue(ent3.is_deleted)
            self.assertEquals(code, 0)
            self.assertTrue('deprecated' in cap.err)

        with Capture(silent=True) as cap:
            code = cmd.main(['unsubscribe', '--serial=%s' % '33333333'])
            self.assertEquals(code, 1)
            self.assertTrue('deprecated' in cap.err)
