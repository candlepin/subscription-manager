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

import stubs
import fixture

from subscription_manager import certlib, managerlib

CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'},
                 'idCert': {'serial': {'serial': 3787455826750723380}}}


def getConsumerData(cls):
    return CONSUMER_DATA


def getSerialNumber(cls):
    return 3787455826750723380


def getDifferentSerialNumber(cls):
    return 3787455826750723381


class InvalidConsumerIdentity(certlib.ConsumerIdentity):
    @classmethod
    def existsAndValid(cls):
        return False


class TestIdentityCertlib(fixture.SubManFixture):

    def setUp(self):
        self.old_ci = certlib.ConsumerIdentity

    def _get_idcertlib(self):
        self.stub_uep = stubs.StubUEP()
        self.stub_uep.getConsumer = getConsumerData
        self.stub_uep.getSerialNumber = getSerialNumber
        return certlib.IdentityCertLib(uep=self.stub_uep)

    def test_idcertlib_persists_cert(self):
        idcertlib = self._get_idcertlib()
        certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        certlib.ConsumerIdentity.getSerialNumber = getDifferentSerialNumber
        managerlib.persist_consumer_cert = Mock()
        idcertlib._do_update()
        managerlib.persist_consumer_cert.assert_called_once_with(CONSUMER_DATA)

    def test_idcertlib_noops_when_serialnum_is_same(self):
        idcertlib = self._get_idcertlib()
        certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        certlib.ConsumerIdentity.getSerialNumber = getSerialNumber
        managerlib.persist_consumer_cert = Mock()
        idcertlib._do_update()
        self.assertFalse(managerlib.persist_consumer_cert.called)

    def test_idcertlib_no_id_cert(self):
        certlib.ConsumerIdentity = InvalidConsumerIdentity
        idcertlib = self._get_idcertlib()
        ret = idcertlib._do_update()
        self.assertEquals(ret, 0)

    def tearDown(self):
        certlib.ConsumerIdentity = self.old_ci
