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

import rhsm.connection
import subscription_manager.injection as inj
import subscription_manager.cp_provider

from subscription_manager.identity import Identity
from subscription_manager.facts import Facts
from subscription_manager.plugins import PluginManager

from test import stubs
from test.fixture import SubManFixture
from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from rhsmlib.dbus import dbus_utils, constants
from rhsmlib.dbus.objects import DomainSocketRegisterDBusObject, RegisterDBusObject

CONTENT_JSON = '''{"hypervisorId": null,
        "serviceLevel": "",
        "autoheal": true,
        "idCert": "FAKE_KEY",
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

SUCCESSFUL_REGISTRATION = {
    "headers": {
        'content-type': 'application/json',
        'date': 'Thu, 02 Jun 2016 15:16:51 GMT',
        'server': 'Apache-Coyote/1.1',
        'transfer-encoding': 'chunked',
        'x-candlepin-request-uuid': '01566658-137b-478c-84c0-38540daa8602',
        'x-version': '2.0.13-1'
    },
    "content": CONTENT_JSON,
    "status": "200"
}


class DomainSocketRegisterDBusObjectUnitTest(SubManFixture):
    def setUp(self):
        self.dbus_connection = mock.Mock(spec=dbus.connection.Connection)
        self.stub_cp_provider = stubs.StubCPProvider()
        inj.provide(inj.CP_PROVIDER, self.stub_cp_provider)

        super(DomainSocketRegisterDBusObjectUnitTest, self).setUp()

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_register(self, patched_uep, mock_persist_consumer):
        self._inject_mock_invalid_consumer()

        expected_consumer = json.loads(CONTENT_JSON, object_hook=dbus_utils._decode_dict)
        del expected_consumer['idCert']

        patched_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)
        self.stub_cp_provider.basic_auth_cp = patched_uep.return_value
        register_service = DomainSocketRegisterDBusObject(conn=self.dbus_connection)

        output = register_service.Register('admin', 'admin', 'admin', {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        })

        # Be sure we are persisting the consumer cert
        mock_persist_consumer.assert_called_once_with(expected_consumer)
        # Be sure we get the right output
        self.assertEqual(output, SUCCESSFUL_REGISTRATION)

    @mock.patch("rhsm.connection.UEPConnection")
    def test_get_uep_from_options(self, patched_uep):
        inj.provide(inj.CP_PROVIDER, subscription_manager.cp_provider.CPProvider)
        options = {
            'username': 'test',
            'password': 'test_password',
            'host': 'localhost',
            'port': 8443,
            'handler': '/candlepin'
        }

        self._inject_mock_invalid_consumer()

        register_service = DomainSocketRegisterDBusObject(conn=self.dbus_connection)
        register_service.build_uep(options)

        from rhsmlib.dbus.base_object import conf as register_conf

        conf = register_conf['server']
        patched_uep.assert_called_once_with(
            username=options['username'],
            password=options['password'],
            host=options['host'],
            ssl_port=options['port'],
            handler=options['handler'],
            proxy_hostname=conf['proxy_hostname'],
            proxy_port=conf.get_int('proxy_port'),
            proxy_user=conf['proxy_user'],
            proxy_password=conf['proxy_password'],
            no_proxy=conf['no_proxy'],
            correlation_id=mock.ANY,
            restlib_class=rhsm.connection.BaseRestLib
        )

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_register_with_activation_keys(self, patched_uep, mock_persist_consumer):
        self._inject_mock_invalid_consumer()

        expected_consumer = json.loads(CONTENT_JSON, object_hook=dbus_utils._decode_dict)
        del expected_consumer['idCert']
        patched_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)
        # Note it's no_auth_cp since activation key registration uses no authentication
        self.stub_cp_provider.no_auth_cp = patched_uep.return_value
        register_service = DomainSocketRegisterDBusObject(self.dbus_connection)

        output = register_service.RegisterWithActivationKeys('admin', ['default_key'], {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        })

        # Be sure we are persisting the consumer cert
        mock_persist_consumer.assert_called_once_with(expected_consumer)
        # Be sure we get the right output
        self.assertEqual(output, SUCCESSFUL_REGISTRATION)


class DomainSocketRegisterDBusObjectFunctionalTest(DBusObjectTest, InjectionMockingTest):
    def dbus_objects(self):
        return [RegisterDBusObject]

    def setUp(self):
        self.stub_cp_provider = stubs.StubCPProvider()

        facts_host_patcher = mock.patch('rhsmlib.dbus.facts.FactsClient', auto_spec=True)
        self.addCleanup(facts_host_patcher.stop)
        self.mock_facts_host = facts_host_patcher.start()
        self.mock_facts_host.return_value.GetFacts.return_value = {}

        super(DomainSocketRegisterDBusObjectFunctionalTest, self).setUp()
        self.proxy = self.proxy_for(RegisterDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.REGISTER_INTERFACE)

        self.mock_identity = mock.Mock(spec=Identity, name="Identity")
        self.mock_identity.is_valid.return_value = True

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.PROD_DIR:
            return stubs.StubProductDirectory()
        elif args[0] == inj.INSTALLED_PRODUCTS_MANAGER:
            return stubs.StubInstalledProductsManager()
        elif args[0] == inj.CP_PROVIDER:
            return self.stub_cp_provider
        elif args[0] == inj.PLUGIN_MANAGER:
            return mock.Mock(spec=PluginManager, name="PluginManager")
        elif args[0] == inj.FACTS:
            return Facts()
        else:
            return None

    def test_open_domain_socket(self):
        dbus_method_args = []

        def assertions(*args):
            result = args[0]
            six.assertRegex(self, result, r'/var/run/dbus.*')

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

    def test_same_socket_on_subsequent_opens(self):
        dbus_method_args = []

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
        with self.assertRaises(dbus.exceptions.DBusException):
            self.dbus_request(None, self.interface.Stop, [])

    def test_closes_domain_socket(self):
        def get_address(*args):
            address = args[0]
            _prefix, _equal, address = address.partition('=')
            get_address.address, _equal, _suffix = address.partition(',')

        self.dbus_request(get_address, self.interface.Start, [])
        self.handler_complete_event.clear()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            # The socket returned for connection is an abstract socket so we have
            # to begin the name with a NUL byte to get into that namespace.  See
            # http://blog.eduardofleury.com/archives/2007/09/13
            sock.connect('\0' + get_address.address)
        finally:
            sock.close()

        self.dbus_request(None, self.interface.Stop, [])
        self.handler_complete_event.wait()

        with self.assertRaises(socket.error) as serr:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect('\0' + get_address.address)
            finally:
                sock.close()
            self.assertEqual(serr.errno, errno.ECONNREFUSED)

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_can_register_over_domain_socket(self, patched_uep, mock_persist_consumer):
        def get_address(*args):
            get_address.address = args[0]

        self.dbus_request(get_address, self.interface.Start, [])
        self.handler_complete_event.clear()

        socket_conn = dbus.connection.Connection(get_address.address)
        socket_proxy = socket_conn.get_object(constants.BUS_NAME, constants.PRIVATE_REGISTER_DBUS_PATH)
        socket_interface = dbus.Interface(socket_proxy, constants.PRIVATE_REGISTER_INTERFACE)

        expected_consumer = json.loads(CONTENT_JSON, object_hook=dbus_utils._decode_dict)
        del expected_consumer['idCert']

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            mock_persist_consumer.assert_called_once_with(expected_consumer)
            self.assertEqual(args[0], SUCCESSFUL_REGISTRATION)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        patched_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)
        # We patch the real UEP class in the tests in this class because we don't want a StubUEP
        self.stub_cp_provider.basic_auth_cp = patched_uep.return_value

        register_opts = ['admin', 'admin', 'admin', {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        }]

        self.dbus_request(assertions, socket_interface.Register, register_opts)
