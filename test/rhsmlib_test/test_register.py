from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2016 Red Hat, Inc.
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

import errno
import mock
import json
import dbus.connection
import socket
import six

import subscription_manager.injection as inj

from subscription_manager.cache import InstalledProductsManager
from subscription_manager.cp_provider import CPProvider
from subscription_manager.facts import Facts
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager

from ..fixture import set_up_mock_sp_store

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from rhsm import connection

from rhsmlib.dbus import constants
from rhsmlib.dbus.objects import RegisterDBusObject

from rhsmlib.services import register, exceptions

CONTENT_JSON = '''{"hypervisorId": null,
        "serviceLevel": "",
        "autoheal": true,
        "idCert": {
          "key": "FAKE_KEY",
          "cert": "FAKE_CERT",
          "serial" : {
            "id" : 5196045143213189102,
            "revoked" : false,
            "collected" : false,
            "expiration" : "2033-04-25T18:03:06+0000",
            "serial" : 5196045143213189102,
            "created" : "2017-04-25T18:03:06+0000",
            "updated" : "2017-04-25T18:03:06+0000"
          },
          "id" : "8a8d011e5ba64700015ba647fbd20b88",
          "created" : "2017-04-25T18:03:07+0000",
          "updated" : "2017-04-25T18:03:07+0000"
        },
        "owner": {"href": "/owners/admin", "displayName": "Admin Owner",
        "id": "ff808081550d997c01550d9adaf40003", "key": "admin"},
        "href": "/consumers/c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "facts": {}, "id": "ff808081550d997c015511b0406d1065",
        "uuid": "c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "guestIds": null, "capabilities": null,
        "environment": null, "installedProducts": null,
        "canActivate": false, "type": {"manifest": false,
        "id": "1000", "label": "system"}, "annotations": null,
        "username": "admin", "updated": "2016-06-02T15:16:51+0000",
        "lastCheckin": null, "entitlementCount": 0, "releaseVer":
        {"releaseVer": null}, "entitlementStatus": "valid", "name":
        "test.example.com", "created": "2016-06-02T15:16:51+0000",
        "contentTags": null, "dev": false}'''


class RegisterServiceTest(InjectionMockingTest):
    def setUp(self):
        super(RegisterServiceTest, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")

        # Mock a basic auth connection
        self.mock_cp.username = "username"
        self.mock_cp.password = "password"

        # Add a mock cp_provider
        self.mock_cp_provider = mock.Mock(spec=CPProvider, name="CPProvider")

        # For the tests in which it's used, the consumer_auth cp and basic_auth cp can be the same
        self.mock_cp_provider.get_consumer_auth_cp.return_value = self.mock_cp
        self.mock_cp_provider.get_basic_auth_cp.return_value = self.mock_cp

        self.mock_pm = mock.Mock(spec=PluginManager, name="PluginManager")
        self.mock_installed_products = mock.Mock(spec=InstalledProductsManager,
            name="InstalledProductsManager")
        self.mock_facts = mock.Mock(spec=Facts, name="Facts")
        self.mock_facts.get_facts.return_value = {}

        syspurpose_patch = mock.patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

        self.mock_syspurpose = mock.Mock()

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.PLUGIN_MANAGER:
            return self.mock_pm
        elif args[0] == inj.INSTALLED_PRODUCTS_MANAGER:
            return self.mock_installed_products
        elif args[0] == inj.FACTS:
            return self.mock_facts
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_cp_provider
        else:
            return None

    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally(self, mock_persist_consumer):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", environment="environment")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environment="environment",
            keys=None,
            installed_products=[],
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage="")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_with_activation_keys(self, mock_persist_consumer):
        self.mock_cp.username = None
        self.mock_cp.password = None
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []

        expected_consumer = json.loads(CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", activation_keys=[1])

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environment=None,
            keys=[1],
            installed_products=[],
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage=""
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_with_consumerid(self, mock_persist_consumer):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []

        expected_consumer = json.loads(CONTENT_JSON)
        self.mock_cp.getConsumer.return_value = json.loads(CONTENT_JSON)

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", consumerid="consumerid")

        self.mock_cp.getConsumer.assert_called_once_with("consumerid")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    def _build_options(self, activation_keys=None, environment=None, force=None, name=None, consumerid=None):
        return {
            'activation_keys': activation_keys,
            'environment': environment,
            'force': force,
            'name': name,
            'consumerid': consumerid
        }

    def test_fails_when_previously_registered(self):
        self.mock_identity.is_valid.return_value = True

        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*system is already registered.*'):
            register.RegisterService(self.mock_cp).validate_options(self._build_options())

    def test_allows_force(self):
        self.mock_identity.is_valid.return_value = True
        options = self._build_options(force=True)
        register.RegisterService(self.mock_cp).validate_options(options)

    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_reads_syspurpose(self, mock_persist_consumer):
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        self.mock_identity.is_valid.return_value = False
        self.mock_sp_store_contents["role"] = "test_role"
        self.mock_sp_store_contents["service_level_agreement"] = "test_sla"
        self.mock_sp_store_contents["addons"] = ["addon1"]
        self.mock_sp_store_contents["usage"] = "test_usage"

        expected_consumer = json.loads(CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name")

        self.mock_cp.registerConsumer.assert_called_once_with(
            addons=["addon1"],
            content_tags=[],
            environment=None,
            facts={},
            installed_products=[],
            keys=None,
            name="name",
            owner="org",
            role="test_role",
            service_level="test_sla",
            type="system",
            usage="test_usage")

    def test_does_not_require_basic_auth_with_activation_keys(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(activation_keys=[1])
        register.RegisterService(self.mock_cp).validate_options(options)

    def test_does_not_allow_basic_auth_with_activation_keys(self):
        self.mock_identity.is_valid.return_value = False
        options = self._build_options(activation_keys=[1])
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*do not require user credentials.*'):
            register.RegisterService(self.mock_cp).validate_options(options)

    def test_does_not_allow_environment_with_activation_keys(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(activation_keys=[1], environment='environment')
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*do not allow environments.*'):
            register.RegisterService(self.mock_cp).validate_options(options)

    def test_does_not_allow_environment_with_consumerid(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(activation_keys=[1], consumerid='consumerid')
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*previously registered.*'):
            register.RegisterService(self.mock_cp).validate_options(options)

    def test_requires_basic_auth_for_normal_registration(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(consumerid='consumerid')
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*Missing username.*'):
            register.RegisterService(self.mock_cp).validate_options(options)


class DomainSocketRegisterDBusObjectTest(DBusObjectTest, InjectionMockingTest):
    def dbus_objects(self):
        return [RegisterDBusObject]

    def setUp(self):
        super(DomainSocketRegisterDBusObjectTest, self).setUp()

        self.proxy = self.proxy_for(RegisterDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.REGISTER_INTERFACE)

        self.mock_identity.is_valid.return_value = True

        self.mock_cp_provider = mock.Mock(spec=CPProvider, name="CPProvider")

        register_patcher = mock.patch('rhsmlib.dbus.objects.register.RegisterService', autospec=True)
        self.mock_register = register_patcher.start().return_value
        self.addCleanup(register_patcher.stop)

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_cp_provider
        else:
            return None

    def test_open_domain_socket(self):
        dbus_method_args = ['']

        def assertions(*args):
            result = args[0]
            six.assertRegex(self, result, r'/var/run/dbus.*')

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

    def test_same_socket_on_subsequent_opens(self):
        dbus_method_args = ['']

        def assertions(*args):
            # Assign the result as an attribute to this function.
            # See http://stackoverflow.com/a/27910553/6124862
            assertions.result = args[0]
            six.assertRegex(self, assertions.result, r'/var/run/dbus.*')

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

        # Reset the handler_complete_event so we'll block for the second
        # dbus_request
        self.handler_complete_event.clear()

        def assertions2(*args):
            result2 = args[0]
            self.assertEqual(assertions.result, result2)

        self.dbus_request(assertions2, self.interface.Start, dbus_method_args)

    def test_cannot_close_what_is_not_opened(self):
        dbus_method_args = ['']
        with self.assertRaises(dbus.exceptions.DBusException):
            self.dbus_request(None, self.interface.Stop, dbus_method_args)

    def test_closes_domain_socket(self):
        dbus_method_args = ['']

        def get_address(*args):
            address = args[0]
            _prefix, _equal, address = address.partition('=')
            get_address.address, _equal, _suffix = address.partition(',')

        self.dbus_request(get_address, self.interface.Start, dbus_method_args)
        self.handler_complete_event.clear()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            # The socket returned for connection is an abstract socket so we have
            # to begin the name with a NUL byte to get into that namespace.  See
            # http://blog.eduardofleury.com/archives/2007/09/13
            sock.connect('\0' + get_address.address)
        finally:
            sock.close()

        self.dbus_request(None, self.interface.Stop, dbus_method_args)
        self.handler_complete_event.wait()

        with self.assertRaises(socket.error) as serr:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect('\0' + get_address.address)
            finally:
                sock.close()
            self.assertEqual(serr.errno, errno.ECONNREFUSED)

    def _build_interface(self):
        dbus_method_args = ['']

        def get_address(*args):
            get_address.address = args[0]

        self.dbus_request(get_address, self.interface.Start, dbus_method_args)
        self.handler_complete_event.clear()
        socket_conn = dbus.connection.Connection(get_address.address)
        socket_proxy = socket_conn.get_object(constants.BUS_NAME, constants.PRIVATE_REGISTER_DBUS_PATH)
        return dbus.Interface(socket_proxy, constants.PRIVATE_REGISTER_INTERFACE)

    def test_can_register_over_domain_socket(self):
        expected_consumer = json.loads(CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ['admin', 'admin', 'admin', {}, {}, '']
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_register_over_domain_socket_with_activation_keys(self):
        expected_consumer = json.loads(CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = [
            'admin',
            ['key1', 'key2'],
            {},
            {
                'host': 'localhost',
                'port': '8443',
                'handler': '/candlepin'
            },
            ''
        ]

        self.dbus_request(assertions, self._build_interface().RegisterWithActivationKeys, dbus_method_args)
