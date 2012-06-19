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

import unittest
import tempfile
from mock import Mock

import stubs

from subscription_manager import certlib, managerlib

CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'},
                 'idCert': {'serial': {'serial': 3787455826750723380}}}


class MockActionLock(certlib.ActionLock):
    PATH = tempfile.mkstemp()[1]

    def __init__(self):
        certlib.ActionLock.__init__(self)


def getConsumerData(cls):
    return CONSUMER_DATA


def getSerialNumber(cls):
    return 3787455826750723380


def getDifferentSerialNumber(cls):
    return 3787455826750723381


class TestIdentityCertlib(unittest.TestCase):

    def setUp(self):
        self.stub_uep = stubs.StubUEP()
        self.stub_uep.getConsumer = getConsumerData
        self.stub_uep.getSerialNumber = getSerialNumber
        self.idcertlib = certlib.IdentityCertLib(lock=MockActionLock(), uep=self.stub_uep)

    def test_idcertlib_persists_cert(self):
        certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        certlib.ConsumerIdentity.getSerialNumber = getDifferentSerialNumber
        managerlib.persist_consumer_cert = Mock()
        self.idcertlib._do_update()
        managerlib.persist_consumer_cert.assert_called_once_with(CONSUMER_DATA)

    def test_idcertlib_noops_when_serialnum_is_same(self):
        certlib.ConsumerIdentity = stubs.StubConsumerIdentity
        certlib.ConsumerIdentity.getSerialNumber = getSerialNumber
        managerlib.persist_consumer_cert = Mock()
        self.idcertlib._do_update()
        self.assertFalse(managerlib.persist_consumer_cert.called)
