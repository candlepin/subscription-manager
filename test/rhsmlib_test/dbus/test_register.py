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

import subscription_manager.injection as inj

from subscription_manager.cp_provider import CPProvider

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from rhsm import connection

from rhsmlib.dbus import constants
from rhsmlib.dbus.objects import RegisterDBusObject

from test import subman_marker_dbus

CONSUMER_CONTENT_JSON = """{"hypervisorId": null,
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
        "owner": {
          "href": "/owners/admin",
          "displayName": "Admin Owner",
          "id": "ff808081550d997c01550d9adaf40003",
          "key": "admin",
          "contentAccessMode": "entitlement"
        },
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
        "contentTags": null, "dev": false}"""

# Following consumer do not contain information about content access mode
OLD_CONSUMER_CONTENT_JSON = """{"hypervisorId": null,
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
        "owner": {
          "href": "/owners/admin",
          "displayName": "Admin Owner",
          "id": "ff808081550d997c01550d9adaf40003",
          "key": "admin"
        },
        "href": "/consumers/c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "facts": {}, "id": "ff808081550d997c015511b0406d1065",
        "uuid": "c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "guestIds": null, "capabilities": null,
        "environments": null, "installedProducts": null,
        "canActivate": false, "type": {"manifest": false,
        "id": "1000", "label": "system"}, "annotations": null,
        "username": "admin", "updated": "2016-06-02T15:16:51+0000",
        "lastCheckin": null, "entitlementCount": 0, "releaseVer":
        {"releaseVer": null}, "entitlementStatus": "valid", "name":
        "test.example.com", "created": "2016-06-02T15:16:51+0000",
        "contentTags": null, "dev": false}"""

OWNERS_CONTENT_JSON = """[
    {
        "autobindDisabled": false,
        "autobindHypervisorDisabled": false,
        "contentAccessMode": "entitlement",
        "contentAccessModeList": "entitlement",
        "contentPrefix": null,
        "created": "2020-02-17T08:21:47+0000",
        "defaultServiceLevel": null,
        "displayName": "Donald Duck",
        "href": "/owners/donaldduck",
        "id": "ff80808170523d030170523d34890003",
        "key": "donaldduck",
        "lastRefreshed": null,
        "logLevel": null,
        "parentOwner": null,
        "updated": "2020-02-17T08:21:47+0000",
        "upstreamConsumer": null
    },
    {
        "autobindDisabled": false,
        "autobindHypervisorDisabled": false,
        "contentAccessMode": "entitlement",
        "contentAccessModeList": "entitlement",
        "contentPrefix": null,
        "created": "2020-02-17T08:21:47+0000",
        "defaultServiceLevel": null,
        "displayName": "Admin Owner",
        "href": "/owners/admin",
        "id": "ff80808170523d030170523d347c0002",
        "key": "admin",
        "lastRefreshed": null,
        "logLevel": null,
        "parentOwner": null,
        "updated": "2020-02-17T08:21:47+0000",
        "upstreamConsumer": null
    },
    {
        "autobindDisabled": false,
        "autobindHypervisorDisabled": false,
        "contentAccessMode": "entitlement",
        "contentAccessModeList": "entitlement,org_environment",
        "contentPrefix": null,
        "created": "2020-02-17T08:21:47+0000",
        "defaultServiceLevel": null,
        "displayName": "Snow White",
        "href": "/owners/snowwhite",
        "id": "ff80808170523d030170523d348a0004",
        "key": "snowwhite",
        "lastRefreshed": null,
        "logLevel": null,
        "parentOwner": null,
        "updated": "2020-02-17T08:21:47+0000",
        "upstreamConsumer": null
    }
]
"""


@subman_marker_dbus
class DomainSocketRegisterDBusObjectTest(DBusObjectTest, InjectionMockingTest):
    def dbus_objects(self):
        return [RegisterDBusObject]

    def setUp(self):
        super(DomainSocketRegisterDBusObjectTest, self).setUp()

        self.proxy = self.proxy_for(RegisterDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.REGISTER_INTERFACE)

        self.mock_identity.is_valid.return_value = True

        self.mock_cp_provider = mock.Mock(spec=CPProvider, name="CPProvider")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")

        # Mock a basic auth connection
        self.mock_cp.username = "username"
        self.mock_cp.password = "password"

        self.mock_cp.getOwnerList = mock.Mock()
        self.mock_cp.getOwnerList.return_value = json.loads(OWNERS_CONTENT_JSON)

        # For the tests in which it's used, the consumer_auth cp and basic_auth cp can be the same
        self.mock_cp_provider.get_consumer_auth_cp.return_value = self.mock_cp
        self.mock_cp_provider.get_basic_auth_cp.return_value = self.mock_cp

        register_patcher = mock.patch("rhsmlib.dbus.objects.register.RegisterService", autospec=True)
        self.mock_register = register_patcher.start().return_value
        self.addCleanup(register_patcher.stop)

        cert_invoker_patcher = mock.patch("rhsmlib.dbus.objects.register.EntCertActionInvoker", autospec=True)
        self.mock_cert_invoker = cert_invoker_patcher.start().return_value
        self.addCleanup(cert_invoker_patcher.stop)

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_cp_provider
        else:
            return None

    def test_open_domain_socket(self):
        dbus_method_args = [""]

        def assertions(*args):
            result = args[0]
            self.assertRegex(result, r"/run/dbus.*")

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

    def test_same_socket_on_subsequent_opens(self):
        dbus_method_args = [""]

        def assertions(*args):
            # Assign the result as an attribute to this function.
            # See http://stackoverflow.com/a/27910553/6124862
            assertions.result = args[0]
            self.assertRegex(assertions.result, r"/run/dbus.*")

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

        # Reset the handler_complete_event so we'll block for the second
        # dbus_request
        self.handler_complete_event.clear()

        def assertions2(*args):
            result2 = args[0]
            self.assertEqual(assertions.result, result2)

        self.dbus_request(assertions2, self.interface.Start, dbus_method_args)

    def test_cannot_close_what_is_not_opened(self):
        dbus_method_args = [""]
        with self.assertRaises(dbus.exceptions.DBusException):
            self.dbus_request(None, self.interface.Stop, dbus_method_args)

    def test_closes_domain_socket(self):
        dbus_method_args = [""]

        def get_address(*args):
            address = args[0]
            _prefix, _equal, address = address.partition("=")
            get_address.address, _equal, _suffix = address.partition(",")

        self.dbus_request(get_address, self.interface.Start, dbus_method_args)
        self.handler_complete_event.clear()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            # The socket returned for connection is an abstract socket so we have
            # to begin the name with a NUL byte to get into that namespace.  See
            # http://blog.eduardofleury.com/archives/2007/09/13
            sock.connect("\0" + get_address.address)
        finally:
            sock.close()

        self.dbus_request(None, self.interface.Stop, dbus_method_args)
        self.handler_complete_event.wait()

        with self.assertRaises(socket.error) as serr:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect("\0" + get_address.address)
            finally:
                sock.close()
            self.assertEqual(serr.errno, errno.ECONNREFUSED)

    def _build_interface(self):
        dbus_method_args = [""]

        def get_address(*args):
            get_address.address = args[0]

        self.dbus_request(get_address, self.interface.Start, dbus_method_args)
        self.handler_complete_event.clear()
        socket_conn = dbus.connection.Connection(get_address.address)
        socket_proxy = socket_conn.get_object(constants.BUS_NAME, constants.PRIVATE_REGISTER_DBUS_PATH)
        return dbus.Interface(socket_proxy, constants.PRIVATE_REGISTER_INTERFACE)

    def test_can_register_over_domain_socket(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ["admin", "admin", "admin", {}, {}, ""]
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_get_orgs_over_domain_socket(self):
        expected_owners = json.loads(OWNERS_CONTENT_JSON)
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_owners)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ["admin", "admin", {}, ""]
        self.dbus_request(assertions, self._build_interface().GetOrgs, dbus_method_args)

    def test_can_register_over_domain_socket_with_activation_keys(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = [
            "admin",
            ["key1", "key2"],
            {},
            {"host": "localhost", "port": "8443", "handler": "/candlepin"},
            "",
        ]

        self.dbus_request(assertions, self._build_interface().RegisterWithActivationKeys, dbus_method_args)
