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
import dbus

from rhsmlib.services import consumer
from rhsmlib.dbus import constants
from rhsmlib.dbus.objects.consumer import ConsumerDBusObject

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from test.rhsmlib_test.base import InjectionMockingTest, DBusObjectTest


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


class TestConsumerDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestConsumerDBusObject, self).setUp()
        self.proxy = self.proxy_for(ConsumerDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.CONSUMER_INTERFACE)

        consumer_patcher = mock.patch('rhsmlib.dbus.objects.consumer.Consumer', autospec=True)
        self.mock_consumer = consumer_patcher.start().return_value
        self.addCleanup(consumer_patcher.stop)

    def _create_mock_identity(self):
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "43b30b32-86cf-459e-9310-cb4182c23c4a"

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            if not hasattr(self, 'mock_identity'):
                self._create_mock_identity()
            return self.mock_identity
        else:
            return None

    def dbus_objects(self):
        return [ConsumerDBusObject]

    def test_get_consumer_uuid(self):
        """
        Test of getting consumer UUID
        """
        expected_result = "43b30b32-86cf-459e-9310-cb4182c23c4a"

        def assertions(*args):
            result = args[0]
            self.assertEqual(result, expected_result)

        self.mock_consumer.get_consumer_uuid.return_value = expected_result

        dbus_method_args = ['']
        self.dbus_request(assertions, self.interface.GetUuid, dbus_method_args)
