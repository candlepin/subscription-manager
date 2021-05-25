from __future__ import print_function, division, absolute_import

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

import rhsm.connection as connection

from .stubs import StubUEP
from .fixture import SubManFixture
from subscription_manager import managercli
from mock import patch, Mock


class CliUnRegistrationTests(SubManFixture):
    @patch('subscription_manager.managerlib.clean_all_data')
    def test_unregister_removes_consumer_cert(self, clean_data_mock):
        mock_injected_identity = self._inject_mock_valid_consumer()

        # When
        cmd = managercli.UnRegisterCommand()

        # CacheManager.delete_cache = classmethod(lambda cls: None)

        cmd.main([])
        self.assertEqual(mock_injected_identity.uuid, cmd.cp.called_unregister_uuid)

    @patch('subscription_manager.managerlib.clean_all_data')
    def test_unregister_removes_consumer_cert_with_gone_correct_id(self, clean_data_mock):
        with patch('rhsm.connection.UEPConnection', new_callable=StubUEP) as mock_uep:
            mock_uep.unregisterConsumer = Mock(side_effect=connection.GoneException("", "", 112233))
            self.stub_cp_provider.consumer_auth_cp = mock_uep
            self._inject_mock_valid_consumer(uuid=112233)

            cmd = managercli.UnRegisterCommand()
            cmd.main([])

            self.assertTrue(mock_uep.unregisterConsumer.called)
            clean_data_mock.assert_called_once_with(backup=False)
