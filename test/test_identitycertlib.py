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

from mock import Mock

import fixture

from subscription_manager import identity
from subscription_manager import identitycertlib
from subscription_manager import managerlib
from subscription_manager import cp_provider
from subscription_manager import injection as inj

CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'},
                 'idCert': {'serial': {'serial': 3787455826750723380}}}


mock_consumer_identity = Mock(spec=identity.ConsumerIdentity)
mock_consumer_identity.getSerialNumber.return_value = 3787455826750723380


# Identities to inject for testing
class InvalidConsumerIdentity(identity.Identity):
    consumer = mock_consumer_identity

    def is_valid(self):
        return False


class ValidConsumerIdentity(identity.Identity):
    consumer = mock_consumer_identity

    def is_valid(self):
        return True

different_mock_consumer_identity = Mock(spec=identity.ConsumerIdentity)
different_mock_consumer_identity.getSerialNumber.return_value = 123123123123


class DifferentValidConsumerIdentity(ValidConsumerIdentity):
    consumer = different_mock_consumer_identity

mock_cp_provider = Mock(spec=cp_provider.CPProvider)


class TestIdentityCertLib(fixture.SubManFixture):

    def setUp(self):
        super(TestIdentityCertLib, self).setUp()

    def _get_idcertlib(self):
        inj.provide(inj.CP_PROVIDER, mock_cp_provider)

        mock_cp_provider.get_consumer_auth_cp.getConsumer.return_value = CONSUMER_DATA

        return identitycertlib.IdentityCertLib(uep=mock_cp_provider.get_consumer_auth_cp)

    def test_idcertlib_persists_cert(self):
        idcertlib = self._get_idcertlib()
#        certlib.ConsumerIdentity = stubs.StubConsumerIdentity
#        certlib.ConsumerIdentity.getSerialNumber = getDifferentSerialNumber
        managerlib.persist_consumer_cert = Mock()

        inj.provide(inj.IDENTITY, DifferentValidConsumerIdentity)
        idcertlib.update()
        managerlib.persist_consumer_cert.assert_called_once_with(CONSUMER_DATA)

    def test_idcertlib_noops_when_serialnum_is_same(self):
        idcertlib = self._get_idcertlib()
        #certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        #certlib.ConsumerIdentity.getSerialNumber = getSerialNumber
        managerlib.persist_consumer_cert = Mock()

        inj.provide(inj.IDENTITY, InvalidConsumerIdentity)

        idcertlib.update()
        self.assertFalse(managerlib.persist_consumer_cert.called)

    def test_idcertlib_no_id_cert(self):
        inj.provide(inj.IDENTITY, InvalidConsumerIdentity)
        idcertlib = self._get_idcertlib()
        report = idcertlib.update()
        self.assertEquals(report._status, 0)

    def tearDown(self):
        super(TestIdentityCertLib, self).tearDown()
