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

from unittest import mock

from rhsmlib.services import consumer

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from test.rhsmlib.base import InjectionMockingTest


class TestConsumerService(InjectionMockingTest):
    def setUp(self):
        super(TestConsumerService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "43b30b32-86cf-459e-9310-cb4182c23c4a"

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        else:
            return None

    def test_get_consumer_uuid(self):
        """
        Test of getting UUID
        """
        test_concumer = consumer.Consumer()
        uuid = test_concumer.get_consumer_uuid()
        self.assertEqual(uuid, "43b30b32-86cf-459e-9310-cb4182c23c4a")

    def test_get_consumer_uuid_unregistered_system(self):
        """
        When system is not registered, then get_consumer_uuid should
        return empty string.
        :return:
        """
        self.mock_identity.uuid = None
        test_concumer = consumer.Consumer()
        uuid = test_concumer.get_consumer_uuid()
        self.assertEqual(uuid, "")
