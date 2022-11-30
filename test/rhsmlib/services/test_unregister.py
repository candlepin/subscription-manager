# Copyright (c) 2017 Red Hat, Inc.
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

from unittest import mock

from test.rhsmlib.base import InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.cp_provider import CPProvider

from rhsmlib.services import unregister

from rhsm import connection


class TestUnregisterService(InjectionMockingTest):
    def setUp(self):
        super(TestUnregisterService, self).setUp()
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_identity.uuid = mock.Mock(return_value="7a002098-c167-41f2-91b3-d0c71e808142")
        self.mock_provider = mock.Mock(spec=CPProvider, name="CPProvider")
        self.mock_provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_provider
        else:
            return None

    @mock.patch("subscription_manager.managerlib.clean_all_data")
    def test_unregister(self, clean_all_data):
        """
        Testing normal unregistration process
        """
        result = unregister.UnregisterService(self.mock_cp).unregister()
        self.assertIsNone(result)
