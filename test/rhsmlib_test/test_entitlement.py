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
import json
import mock
import six

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager
from subscription_manager.cp_provider import CPProvider
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.reasons import Reasons

from rhsm import connection

from rhsmlib.dbus.objects import EntitlementDBusObject
from rhsmlib.dbus import constants
from rhsmlib.services import entitlement

class TestEntitlementService(InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")
        self.mock_cp_provider = mock.Mock(spec=CPProvider,name="CPProvider")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        self.mock_pm = mock.Mock(spec=PluginManager, name="PluginManager")
        self.mock_cert_sorter = mock.Mock(spec=CertSorter, name="CertSorter")
        self.mock_cert_sorter.reasons =  mock.Mock(spec=Reasons, name="Reasons")
        self.mock_cert_sorter.reasons.get_name_message_map.return_value = {}
        self.mock_cert_sorter.get_system_status.return_value="System Status"

    def injection_definitions(self, *args, **kwargs):
        return {
            inj.IDENTITY: self.mock_identity,
            inj.PLUGIN_MANAGER: self.mock_pm,
            inj.CERT_SORTER: self.mock_cert_sorter,
            inj.CP_PROVIDER: self.mock_cp_provider,
        }.get(args[0]) # None when a key does not exist

    def test_get_status(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"
        result = entitlement.EntitlementService().get_status()
        self.assertEqual(
            {'status': 0,
             'reasons': {},
             'overall_status': "System Status"},
            result)

    def test_get_status_for_invalid_system(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"
        reasons = json.load(open("test/rhsmlib_test/data/reasons.json"))
        self.mock_cert_sorter.reasons.get_name_message_map.return_value = reasons
        self.mock_cert_sorter.is_valid.return_value=False
        result = entitlement.EntitlementService().get_status()
        self.assertEqual(
            {'status': 1,
             'reasons': reasons,
             'overall_status': "System Status"},
            result)

class TestEntitlementDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        open("output.txt","wt").write("setUp for TestEntitlementDBusObject\n")
        super(TestEntitlementDBusObject, self).setUp()
        open("output.txt","at").write("after super setUp\n")
        self.proxy = self.proxy_for(EntitlementDBusObject.default_dbus_path)
        open("output.txt","at").write("after proxy_for\n")
        self.interface = dbus.Interface(self.proxy, EntitlementDBusObject.interface_name)
        entitlement_patcher = mock.patch('rhsmlib.dbus.objects.entitlement.EntitlementService', autospec=True)
        self.mock_entitlement = entitlement_patcher.start().return_value
        open("output.txt","at").write("before addCleanup\n")
        self.addCleanup(entitlement_patcher.stop)
        open("output.txt","at").write("after addCleanup\n")
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"
        open("output.txt","at").write("we are here\n")

    def injection_definitions(self, *args, **kwargs):
        cp_provider =  mock.Mock(spec=CPProvider, name="CPProvider")
        cp_provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")
        print("injection_definitions:",*args)
        return {
            inj.IDENTITY:  self.mock_identity,
            inj.CP_PROVIDER: cp_provider
        }.get(args[0])

    def dbus_objects(self):
        return [EntitlementDBusObject]

    def test_get_status(self):
        def assertions(*args):
            expected_content = ""
            result = args[0]
            print ("assertions:",*args)
            self.assertEqual(result, expected_content)

        self.mock_entitlement.get_status.return_value = ""

        dbus_method_args = [['x', 'y'], 1, {}]
        self.dbus_request(assertions, self.interface.Entitlement, dbus_method_args)

#     def test_must_be_registered_pool(self):
#         self.mock_identity.is_valid.return_value = False
#         pool_method_args = [['x', 'y'], 1, {}]
#         with six.assertRaisesRegex(self, dbus.DBusException, r'requires the consumer to be registered.*'):
#             self.dbus_request(None, self.interface.PoolAttach, pool_method_args)

#     def test_must_be_registered_auto(self):
#         self.mock_identity.is_valid.return_value = False
#         auto_method_args = ['service_level', {}]
#         with six.assertRaisesRegex(self, dbus.DBusException, r'requires the consumer to be registered.*'):
#             self.dbus_request(None, self.interface.AutoAttach, auto_method_args)

#     def test_auto_attach(self):
#         def assertions(*args):
#             result = args[0]
#             self.assertEqual(result, json.dumps(CONTENT_JSON))

#         self.mock_attach.attach_auto.return_value = CONTENT_JSON

#         dbus_method_args = ['service_level', {}]
#         self.dbus_request(assertions, self.interface.AutoAttach, dbus_method_args)
