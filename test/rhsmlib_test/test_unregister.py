from __future__ import print_function, division, absolute_import

#
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

import dbus
import mock
import six

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.cp_provider import CPProvider

from rhsmlib.dbus.objects import UnregisterDBusObject
from rhsmlib.dbus import constants
from rhsmlib.services import unregister

from rhsm import connection


class TestUnregisterService(InjectionMockingTest):
    def setUp(self):
        super(TestUnregisterService, self).setUp()
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_identity.uuid = mock.Mock(return_value='7a002098-c167-41f2-91b3-d0c71e808142')
        self.mock_provider = mock.Mock(spec=CPProvider, name="CPProvider")
        self.mock_provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_provider
        else:
            return None

    @mock.patch('os.path.exists')
    @mock.patch('subscription_manager.managerlib.clean_all_data')
    def test_unregister(self, clean_all_data, mock_path_exists):
        """
        Testing normal unregistration process
        """
        mock_path_exists.return_value = False  # this short-circuits --no-insights path mask check
        result = unregister.UnregisterService(self.mock_cp).unregister()
        self.assertIsNone(result)

    @mock.patch('subprocess.call')
    @mock.patch('os.path.islink')
    @mock.patch('os.readlink')
    @mock.patch('os.path.exists')
    @mock.patch('subscription_manager.managerlib.clean_all_data')
    def test_unregister_insights_register_unmask(self, clean_all_data, mock_path_exists, mock_readlink, mock_islink,
                                                 mock_subprocess_call):
        """
        Testing normal unregistration process
        """
        mock_path_exists.return_value = True
        mock_readlink.return_value = '/dev/null'
        mock_islink.return_value = True

        mock_open = mock.mock_open()
        with mock.patch('rhsmlib.services.unregister.open', mock_open, create=True):
            result = unregister.UnregisterService(self.mock_cp).unregister()
        self.assertIsNone(result)
        mock_subprocess_call.assert_called_once_with(
            ['/usr/bin/systemctl', 'unmask', 'insights-register.path'],
            stdout=mock_open(), stderr=mock_open()
        )


class TestUnregisterDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestUnregisterDBusObject, self).setUp()
        self.proxy = self.proxy_for(UnregisterDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.UNREGISTER_INTERFACE)

        unregister_patcher = mock.patch('rhsmlib.dbus.objects.unregister.UnregisterService')
        self.unregister = unregister_patcher.start().return_value
        self.addCleanup(unregister_patcher.stop)

        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "7a002098-c167-41f2-91b3-d0c71e808142"

        self.mock_provider = mock.Mock(spec=CPProvider, name="CPProvider")
        self.mock_provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_provider
        else:
            return None

    def dbus_objects(self):
        return [UnregisterDBusObject]

    def test_must_be_registered_unregister(self):
        self.mock_identity.is_valid.return_value = False
        unregister_method_args = [{}, '']
        with six.assertRaisesRegex(self, dbus.DBusException, r'requires the consumer to be registered.*'):
            self.dbus_request(None, self.interface.Unregister, unregister_method_args)
