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
import dbus
import mock
import six

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager
from subscription_manager.cp_provider import CPProvider

from rhsm import connection

from rhsmlib.dbus.objects import AttachDBusObject
from rhsmlib.dbus import constants
from rhsmlib.services import attach


class TestAttachService(InjectionMockingTest):
    def setUp(self):
        super(TestAttachService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        self.mock_pm = mock.Mock(spec=PluginManager, name="PluginManager")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.PLUGIN_MANAGER:
            return self.mock_pm
        elif args[0] == inj.CP_PROVIDER:
            provider = mock.Mock(spec=CPProvider, name="CPProvider")
            provider.get_consumer_auth_cp.return_value = self.mock_cp
            return provider
        else:
            return None

    def test_pool_attacm(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"

        self.mock_cp.bindByEntitlementPool.return_value = [{'pool': {}}]

        result = attach.AttachService().attach_pool('x', 1)

        self.assertEqual(1, len(result))
        self.assertEqual({'pool': {}}, result[0])

        expected_bind_calls = [
            mock.call('id', 'x', 1),
        ]
        self.assertEqual(expected_bind_calls, self.mock_cp.bindByEntitlementPool.call_args_list)

        expected_plugin_calls = [
            mock.call('pre_subscribe', consumer_uuid='id', pool_id='x', quantity=1),
            mock.call('post_subscribe', consumer_uuid='id', entitlement_data=[{'pool': {}}]),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    def test_auto_attach(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"

        self.mock_cp.bind.return_value = [{'pool': {}}]

        result = attach.AttachService().attach_auto('service_level')
        self.assertEqual(1, len(result))
        self.assertEqual({'pool': {}}, result[0])

        expected_update_calls = [
            mock.call('id', service_level='service_level')
        ]
        self.assertEqual(expected_update_calls, self.mock_cp.updateConsumer.call_args_list)

        expected_bind_calls = [
            mock.call('id'),
        ]
        self.assertEqual(expected_bind_calls, self.mock_cp.bind.call_args_list)

        expected_plugin_calls = [
            mock.call('pre_auto_attach', consumer_uuid='id'),
            mock.call('post_auto_attach', consumer_uuid='id', entitlement_data=[{'pool': {}}])
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)


class TestAttachDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestAttachDBusObject, self).setUp()
        self.proxy = self.proxy_for(AttachDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.ATTACH_INTERFACE)

        attach_patcher = mock.patch('rhsmlib.dbus.objects.attach.AttachService', autospec=True)
        self.mock_attach = attach_patcher.start().return_value
        self.addCleanup(attach_patcher.stop)
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        else:
            return None

    def dbus_objects(self):
        return [AttachDBusObject]

    def test_pool_attach(self):
        def assertions(*args):
            result = args[0]
            self.assertEqual(2, len(result))
            self.assertEqual({}, result[0])

        self.mock_attach.attach_pool.return_value = [{'pool': {}}]

        dbus_method_args = [['x', 'y'], 1, {}]
        self.dbus_request(assertions, self.interface.PoolAttach, dbus_method_args)

    def test_must_be_registered_pool(self):
        self.mock_identity.is_valid.return_value = False
        pool_method_args = [['x', 'y'], 1, {}]
        with six.assertRaisesRegex(self, dbus.DBusException, r'requires the consumer to be registered.*'):
            self.dbus_request(None, self.interface.PoolAttach, pool_method_args)

    def test_must_be_registered_auto(self):
        self.mock_identity.is_valid.return_value = False
        auto_method_args = ['service_level', {}]
        with six.assertRaisesRegex(self, dbus.DBusException, r'requires the consumer to be registered.*'):
            self.dbus_request(None, self.interface.AutoAttach, auto_method_args)

    def test_auto_attach(self):
        def assertions(*args):
            result = args[0]
            self.assertEqual(1, len(result))
            self.assertEqual({}, result[0])

        self.mock_attach.attach_auto.return_value = [{'pool': {}}]

        dbus_method_args = ['service_level', {}]
        self.dbus_request(assertions, self.interface.AutoAttach, dbus_method_args)
