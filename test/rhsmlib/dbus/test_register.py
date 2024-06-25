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
import contextlib
import dbus
import json
import socket
import tempfile
from typing import Optional

from rhsm import connection
import rhsmlib.dbus.exceptions
from rhsmlib.dbus.objects.register import DomainSocketRegisterDBusImplementation, RegisterDBusImplementation
from rhsmlib.dbus.server import DomainSocketServer

from unittest import mock
from test.rhsmlib.base import SubManDBusFixture


CONSUMER_CONTENT_JSON_SCA = """{"hypervisorId": null,
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
          "contentAccessMode": "org_environment"
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


class RegisterDBusObjectTest(SubManDBusFixture):
    socket_dir: Optional[tempfile.TemporaryDirectory] = None

    def setUp(self) -> None:
        super().setUp()
        self.impl = RegisterDBusImplementation()

        self.socket_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.socket_dir.cleanup)

        socket_path_patch = mock.patch.object(DomainSocketServer, "_server_socket_path", self.socket_dir.name)
        socket_path_patch.start()
        # `tmpdir` behaves differently from `dir` on old versions of dbus
        # (earlier than 1.12.24 and 1.14.4).
        # In newer versions we are not getting abstract socket anymore.
        socket_iface_patch = mock.patch.object(DomainSocketServer, "_server_socket_iface", "unix:dir=")
        socket_iface_patch.start()

        get_cmd_line_patch = mock.patch(
            "rhsmlib.client_info.DBusSender.get_cmd_line",
            autospec=True,
        )
        get_cmd_line_mock = get_cmd_line_patch.start()
        get_cmd_line_mock.return_value = "unit-test sender"

        pid_of_sender_patch = mock.patch(
            "rhsmlib.dbus.server.pid_of_sender",
            autospec=True,
        )
        pid_of_sender_mock = pid_of_sender_patch.start()
        pid_of_sender_mock.return_value = 123456

        are_others_running_path = mock.patch(
            "rhsmlib.dbus.server.DomainSocketServer.are_other_senders_still_running",
            autospec=True,
        )
        are_others_running_mock = are_others_running_path.start()
        are_others_running_mock.return_value = False

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    def tearDown(self) -> None:
        """Make sure the domain server is stopped once the test ends."""
        with contextlib.suppress(rhsmlib.dbus.exceptions.Failed):
            self.impl.stop("sender")

        super().tearDown()

    def test_Start(self):
        substring = self.socket_dir.name + "/dbus.*"
        result = self.impl.start("sender")
        self.assertRegex(result, substring)

    def test_Start__two_starts(self):
        """Test that opening the server twice returns the same address"""
        result_1 = self.impl.start("sender")
        result_2 = self.impl.start("sender")
        self.assertEqual(result_1, result_2)

    def test_Start__can_connect(self):
        result = self.impl.start("sender")
        prefix, _, data = result.partition("=")
        address, _, guid = data.partition(",")

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(address)
        finally:
            sock.close()

    def test_Stop(self):
        self.impl.start("sender")
        self.impl.stop("sender")

    def test_Stop__not_running(self):
        with self.assertRaises(rhsmlib.dbus.exceptions.Failed):
            self.impl.stop("sender")


class DomainSocketRegisterDBusObjectTest(SubManDBusFixture):
    def setUp(self) -> None:
        super().setUp()
        self.impl = DomainSocketRegisterDBusImplementation()

        register_patch = mock.patch(
            "rhsmlib.dbus.objects.register.RegisterService.register",
            name="register",
        )
        self.patches["register"] = register_patch.start()
        self.addCleanup(register_patch.stop)

        unregister_patch = mock.patch(
            "rhsmlib.services.unregister.UnregisterService.unregister", name="unregister"
        )
        self.patches["unregister"] = unregister_patch.start()
        self.addCleanup(unregister_patch.stop)

        is_registered_patch = mock.patch(
            "rhsmlib.dbus.base_object.BaseImplementation.is_registered",
            name="is_registered",
        )
        self.patches["is_registered"] = is_registered_patch.start()
        self.addCleanup(is_registered_patch.stop)

        update_patch = mock.patch(
            "rhsmlib.dbus.objects.register.EntCertActionInvoker.update",
            name="update",
        )
        self.patches["update"] = update_patch.start()
        self.addCleanup(update_patch.stop)

        build_uep_patch = mock.patch(
            "rhsmlib.dbus.base_object.BaseImplementation.build_uep",
            name="build_uep",
        )
        self.patches["build_uep"] = build_uep_patch.start()
        self.addCleanup(build_uep_patch.stop)
        self.patches["update"].return_value = None

    def test_Register(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["register"].return_value = expected
        self.patches["is_registered"].return_value = False

        result = self.impl.register_with_credentials(
            "org", {"username": "username", "password": "password"}, {}
        )
        self.assertEqual(expected, result)

    def test_Register__with_force_option(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["register"].return_value = expected
        self.patches["unregister"].return_value = None
        self.patches["is_registered"].return_value = True

        result = self.impl.register_with_credentials(
            "org", {"username": "username", "password": "password", "force": True}, {}
        )
        self.assertEqual(expected, result)

    def test_Register__already_registered(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["register"].return_value = expected
        self.patches["unregister"].return_value = None
        self.patches["is_registered"].return_value = True

        with self.assertRaisesRegex(dbus.DBusException, "This system is already registered."):
            self.impl.register_with_credentials("org", {"username": "username", "password": "password"}, {})

    def test_Register__enable_content(self):
        """Test including 'enable_content' in entitlement mode with no content."""
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["register"].return_value = expected
        self.patches["is_registered"].return_value = False

        result = self.impl.register_with_credentials(
            "org", {"username": "username", "password": "password", "enable_content": "1"}, {"force": True}
        )
        self.assertEqual(expected, result)

    def test_Register__enable_content__sca(self):
        """Test including 'enable_content' in SCA mode."""
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["register"].return_value = expected
        self.patches["is_registered"].return_value = False

        result = self.impl.register_with_credentials(
            "org", {"username": "username", "password": "password", "enable_content": "1"}, {}
        )
        self.assertEqual(expected, result)

    def test_GetOrgs(self):
        self.patches["is_registered"].return_value = False
        mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        mock_cp.username = "username"
        mock_cp.password = "password"
        mock_cp.getOwnerList = mock.Mock()
        mock_cp.getOwnerList.return_value = json.loads(OWNERS_CONTENT_JSON)
        self.patches["build_uep"].return_value = mock_cp

        expected = json.loads(OWNERS_CONTENT_JSON)
        result = self.impl.get_organizations({"username": "username", "password": "password"})
        self.assertEqual(expected, result)

    def test_RegisterWithActivationKeys(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["is_registered"].return_value = False
        self.patches["register"].return_value = expected

        result = self.impl.register_with_activation_keys(
            "username",
            {"keys": ["key1", "key2"]},
            {"host": "localhost", "port": "8443", "handler": "/candlepin"},
        )
        self.assertEqual(expected, result)

    def test_RegisterWithActivationKeys__already_registered(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["is_registered"].return_value = True
        self.patches["register"].return_value = expected

        with self.assertRaisesRegex(dbus.DBusException, "This system is already registered."):
            self.impl.register_with_activation_keys(
                "username",
                {"keys": ["key1", "key2"]},
                {"host": "localhost", "port": "8443", "handler": "/candlepin"},
            )

    def test_RegisterWithActivationKeys__with_force_option(self):
        expected = json.loads(CONSUMER_CONTENT_JSON_SCA)
        self.patches["is_registered"].return_value = True
        self.patches["unregister"].return_value = None
        self.patches["register"].return_value = expected

        result = self.impl.register_with_activation_keys(
            "username",
            {"keys": ["key1", "key2"], "force": True},
            {"host": "localhost", "port": "8443", "handler": "/candlepin"},
        )
        self.assertEqual(expected, result)
