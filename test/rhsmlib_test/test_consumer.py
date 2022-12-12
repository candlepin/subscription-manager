from __future__ import print_function, division, absolute_import

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

import mock

from rhsmlib.services import consumer
from rhsmlib.dbus.objects.consumer import ConsumerDBusObject

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from test.rhsmlib_test.base import DBusServerStubProvider, InjectionMockingTest


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


class TestConsumerDbusObject(DBusServerStubProvider):
    dbus_class = ConsumerDBusObject
    dbus_class_kwargs = {}

    @classmethod
    def setUpClass(cls) -> None:
        get_consumer_uuid_patch = mock.patch(
            "rhsmlib.dbus.objects.consumer.Consumer.get_consumer_uuid",
            name="get_consumer_uuid",
        )
        cls.patches["get_consumer_uuid"] = get_consumer_uuid_patch.start()
        cls.addClassCleanup(get_consumer_uuid_patch)

        super().setUpClass()

    def test_GetUuid(self):
        self.patches["get_consumer_uuid"].return_value = "fake-uuid"

        expected = "fake-uuid"
        result = self.obj.GetUuid.__wrapped__(self.obj, self.LOCALE)
        self.assertEqual(expected, result)
