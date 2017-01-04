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

import rhsm.connection
import subscription_manager.injection as inj

from test import stubs
from test.fixture import SubManFixture
from test.rhsmlib_test.base import DBusObjectTest

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
        super(DomainSocketRegisterDBusObjectUnitTest, self).setUp()

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_register(self, stub_uep, mock_persist_consumer):
        self._inject_mock_invalid_consumer()

        expected_consumer = json.loads(CONTENT_JSON, object_hook=dbus_utils._decode_dict)
        del expected_consumer['idCert']

        stub_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)
        register_service = DomainSocketRegisterDBusObject(conn=self.dbus_connection)

        output = register_service.Register('admin', 'admin', 'admin', {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        })

        # Be sure we are persisting the consumer cert
        mock_persist_consumer.assert_called_once_with(expected_consumer)
        # Be sure we get the right output
        self.assertEquals(output, SUCCESSFUL_REGISTRATION)

    @mock.patch("rhsm.connection.UEPConnection")
    def test_get_uep_from_options(self, stub_uep):
        stub_uep.return_value = mock.Mock(spec=rhsm.connection.UEPConnection)
        options = {
            'username': 'test',
            'password': 'test_password',
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin',
            'insecure': True
        }

        self._inject_mock_invalid_consumer()

        register_service = DomainSocketRegisterDBusObject(conn=self.dbus_connection)
        register_service.build_uep(options)

        stub_uep.assert_called_once_with(
            username=options.get('username', None),
            password=options.get('password', None),
            host=options.get('host', None),
            ssl_port=rhsm.connection.safe_int(options.get('port', None)),
            handler=options.get('handler', None),
            insecure=options.get('insecure', None),
            proxy_hostname=options.get('proxy_hostname', None),
            proxy_port=options.get('proxy_port', None),
            proxy_user=options.get('proxy_user', None),
            proxy_password=options.get('proxy_password', None),
            restlib_class=rhsm.connection.BaseRestLib
        )

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_register_with_activation_keys(self, stub_uep, mock_persist_consumer):
        self._inject_mock_invalid_consumer()

        expected_consumer = json.loads(CONTENT_JSON,
            object_hook=dbus_utils._decode_dict)
        del expected_consumer['idCert']
        stub_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)
        register_service = DomainSocketRegisterDBusObject(self.dbus_connection)

        output = register_service.RegisterWithActivationKeys('admin', ['default_key'], {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        })

        # Be sure we are persisting the consumer cert
        mock_persist_consumer.assert_called_once_with(expected_consumer)
        # Be sure we get the right output
        self.assertEquals(output, SUCCESSFUL_REGISTRATION)


class DomainSocketRegisterDBusObjectFunctionalTest(DBusObjectTest):
    def dbus_objects(self):
        return [RegisterDBusObject]

    def setUp(self):
        inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, stubs.StubInstalledProductsManager())
        facts_host_patcher = mock.patch('rhsmlib.dbus.facts.FactsClient', auto_spec=True)
        self.addCleanup(facts_host_patcher.stop)
        self.mock_facts_host = facts_host_patcher.start()
        self.mock_facts_host.return_value.GetFacts.return_value = {}

        super(DomainSocketRegisterDBusObjectFunctionalTest, self).setUp()
        self.proxy = self.proxy_for(RegisterDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.REGISTER_INTERFACE)

    def test_open_domain_socket(self):
        dbus_method_args = []

        def assertions(*args):
            result = args[0]
            self.assertRegexpMatches(result, r'/var/run/dbus.*')

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

    def test_same_socket_on_subsequent_opens(self):
        dbus_method_args = []

        def assertions(*args):
            # Assign the result as an attribute to this function.
            # See http://stackoverflow.com/a/27910553/6124862
            assertions.result = args[0]
            self.assertRegexpMatches(assertions.result, r'/var/run/dbus.*')

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

    def _inject_mock_invalid_consumer(self, uuid=None):
        invalid_identity = mock.NonCallableMock(name='InvalidIdentityMock')
        invalid_identity.is_valid = mock.Mock(return_value=False)
        invalid_identity.uuid = uuid or "INVALIDCONSUMERUUID"
        invalid_identity.cert_dir_path = "/not/a/real/path/to/pki/consumer/"
        inj.provide(inj.IDENTITY, invalid_identity)
        return invalid_identity

    @mock.patch("subscription_manager.managerlib.persist_consumer_cert")
    @mock.patch("rhsm.connection.UEPConnection")
    def test_can_register_over_domain_socket(self, stub_uep, mock_persist_consumer):
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
            self.assertEquals(args[0], SUCCESSFUL_REGISTRATION)

        self._inject_mock_invalid_consumer()
        stub_uep.return_value.registerConsumer = mock.Mock(return_value=SUCCESSFUL_REGISTRATION)

        register_opts = ['admin', 'admin', 'admin', {
            'host': 'localhost',
            'port': '8443',
            'handler': '/candlepin'
        }]

        self.dbus_request(assertions, socket_interface.Register, register_opts)
