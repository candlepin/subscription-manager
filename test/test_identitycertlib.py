from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import mock
from subscription_manager.identity import Identity

from . import fixture

from subscription_manager import identity
from subscription_manager import identitycertlib

CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'},
                 'idCert': {'serial': {'serial': 3787455826750723380}}}


mock_consumer_identity = mock.Mock(spec=identity.ConsumerIdentity)
mock_consumer_identity.getSerialNumber.return_value = 3787455826750723380
mock_consumer_identity.getConsumerName.return_value = "Mock Consumer Identity"
mock_consumer_identity.getConsumerId.return_value = "11111-00000-11111-0000"


# Identities to inject for testing
class StubIdentity(identity.BaseIdentity):
    _consumer = None

    def _get_consumer_identity(self):
        return self._consumer


class InvalidIdentity(StubIdentity):
    pass


class ValidIdentity(StubIdentity):
    _consumer = mock_consumer_identity


different_mock_consumer_identity = mock.Mock(spec=identity.ConsumerIdentity)
different_mock_consumer_identity.getSerialNumber.return_value = 123123123123
different_mock_consumer_identity.getConsumerName.return_value = "A Different Mock Consumer Identity"
different_mock_consumer_identity.getConsumerId.return_value = "AAAAAA-BBBBB-CCCCCC-DDDDD"


class DifferentValidConsumerIdentity(StubIdentity):
    _consumer = different_mock_consumer_identity


class TestIdentityUpdateAction(fixture.SubManFixture):

    def setUp(self):
        super(TestIdentityUpdateAction, self).setUp()

        mock_uep = mock.Mock()
        mock_uep.getConsumer.return_value = CONSUMER_DATA

        self.set_consumer_auth_cp(mock_uep)

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    def test_idcertlib_persists_cert(self, mock_persist):
        id_update_action = identitycertlib.IdentityUpdateAction()

        Identity.getInstance = staticmethod(lambda: DifferentValidConsumerIdentity())
        id_update_action.perform()
        mock_persist.assert_called_once_with(CONSUMER_DATA)

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    def test_idcertlib_noops_when_serialnum_is_same(self, mock_persist):
        id_update_action = identitycertlib.IdentityUpdateAction()
        #certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        #certlib.ConsumerIdentity.getSerialNumber = getSerialNumber

        Identity.getInstance = staticmethod(lambda: InvalidIdentity())

        id_update_action.perform()
        self.assertFalse(mock_persist.called)

    def test_idcertlib_no_id_cert(self):
        Identity.getInstance = staticmethod(lambda: InvalidIdentity())
        id_update_action = identitycertlib.IdentityUpdateAction()
        report = id_update_action.perform()
        self.assertEqual(report._status, 0)


class TestIdentityCertActionInvoker(fixture.SubManFixture):
    def setUp(self):
        super(TestIdentityCertActionInvoker, self).setUp()

        mock_uep = mock.Mock()
        mock_uep.getConsumer.return_value = CONSUMER_DATA

        self.set_consumer_auth_cp(mock_uep)

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    def test(self, mock_persist):
        id_cert_lib = identitycertlib.IdentityCertActionInvoker()
        report = id_cert_lib.update()
        self.assertEqual(report._status, 1)
        self.assertTrue(mock_persist.called)
