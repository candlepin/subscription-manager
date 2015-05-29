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

from stubs import StubUEP
import rhsm.connection as connection
from subscription_manager.cache import CacheManager
from subscription_manager import managercli
from fixture import SubManFixture
from mock import patch


class CliUnRegistrationTests(SubManFixture):

    @patch('subscription_manager.managerlib.clean_all_data')
    def test_unregister_removes_consumer_cert(self, clean_data_mock):
        connection.UEPConnection = StubUEP

        mock_injected_identity = self._inject_mock_valid_consumer()

        # When
        cmd = managercli.UnRegisterCommand()

        CacheManager.delete_cache = classmethod(lambda cls: None)

        cmd.main(['unregister'])
        self.assertEquals(mock_injected_identity.uuid, cmd.cp.called_unregister_uuid)
