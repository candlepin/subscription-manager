#
# Copyright (c) 2010 Red Hat, Inc.
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
from mock import Mock

from stubs import StubUEP, StubEntitlementDirectory, StubProductDirectory
import rhsm.connection as connection
from subscription_manager.certlib import ConsumerIdentity
from subscription_manager.cache import CacheManager
from subscription_manager import managercli, managerlib, certmgr

class CliUnRegistrationTests(unittest.TestCase):

    def test_unregister_removes_consumer_cert(self):
        connection.UEPConnection = StubUEP

        # When
        cmd = managercli.UnRegisterCommand(ent_dir=StubEntitlementDirectory([]),
                              prod_dir=StubProductDirectory([]))

        ConsumerIdentity.existsAndValid = classmethod(lambda cls: True)
        ConsumerIdentity.exists = classmethod(lambda cls: True)

        CacheManager.delete_cache = classmethod(lambda cls: None)

        def stub_consumer(): return {'consumer_name': 'stub_name', 'uuid': 'stub_uuid'}

        managercli.check_registration = stub_consumer
        cmd.main(['unregister'])
        self.assertEquals('stub_uuid', cmd.cp.called_unregister_uuid)
