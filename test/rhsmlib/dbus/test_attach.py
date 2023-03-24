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
from typing import Any, Dict

import dbus
import json
import mock

from rhsmlib.dbus.objects import AttachDBusObject

from test.rhsmlib.base import DBusServerStubProvider
from test.rhsmlib.services.test_attach import CONTENT_JSON


class TestAttachDBusObject(DBusServerStubProvider):
    dbus_class = AttachDBusObject
    dbus_class_kwargs: Dict[str, Any] = {}

    @classmethod
    def setUpClass(cls) -> None:
        is_simple_content_access_patch = mock.patch(
            "rhsmlib.dbus.objects.attach.is_simple_content_access",
            name="is_simple_content_access",
        )
        cls.patches["is_simple_content_access"] = is_simple_content_access_patch.start()
        cls.addClassCleanup(is_simple_content_access_patch.stop)

        is_registered_patch = mock.patch(
            "rhsmlib.dbus.base_object.BaseObject.is_registered",
            name="is_registered",
        )
        cls.patches["is_registered"] = is_registered_patch.start()
        cls.addClassCleanup(is_registered_patch.stop)

        update_patch = mock.patch(
            "subscription_manager.certlib.BaseActionInvoker.update",
            name="update",
        )
        cls.patches["update"] = update_patch.start()
        cls.addClassCleanup(update_patch.stop)

        super().setUpClass()

    def setUp(self) -> None:
        self.patches["is_simple_content_access"].return_value = False
        self.patches["is_registered"].return_value = True
        self.patches["update"].return_value = None

        AttachService_patch = mock.patch(
            "rhsmlib.dbus.objects.attach.AttachService",
            name="AttachService",
            autospec=True,
        )
        self.mock_attach = AttachService_patch.start().return_value
        self.addCleanup(AttachService_patch.stop)

        super().setUp()

    def test_PoolAttach(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, self.LOCALE)
        self.assertEqual(result, expected)

    def test_PoolAttach__proxy(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(
            self.obj,
            ["x", "y"],
            1,
            {
                "proxy_hostname": "proxy.company.com",
                "proxy_port": "3128",
                "proxy_user": "user",
                "proxy_password": "password",
            },
            self.LOCALE,
        )
        self.assertEqual(result, expected)

    def test_PoolAttach__de(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, "de")
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, "de_DE")
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE_utf8(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, "de_DE.utf-8")
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE_UTF8(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, "de_DE.UTF-8")
        self.assertEqual(expected, result)

    def test_PoolAttach__sca(self):
        self.patches["is_simple_content_access"].return_value = True
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        # TODO: Change to assertRaises when auto-attach is not supported in SCA mode
        # BZ 2049101, BZ 2049620

        expected = [json.dumps(CONTENT_JSON), json.dumps(CONTENT_JSON)]
        result = self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, "de_DE.UTF-8")
        self.assertEqual(expected, result)

    def test_PoolAttach__not_registered(self):
        self.patches["is_registered"].return_value = False
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        with self.assertRaisesRegex(dbus.DBusException, "requires the consumer to be registered"):
            self.obj.PoolAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, self.LOCALE)

    def test_AutoAttach(self):
        self.mock_attach.attach_auto.return_value = CONTENT_JSON

        expected = json.dumps(CONTENT_JSON)
        result = self.obj.AutoAttach.__wrapped__(self.obj, "service_level", {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_AutoAttach__sca(self):
        self.patches["is_simple_content_access"].return_value = True
        self.mock_attach.attach_auto.return_value = CONTENT_JSON

        # TODO: Change to assertRaises when auto-attach is not supported in SCA mode
        # BZ 2049101, BZ 2049620

        expected = json.dumps(CONTENT_JSON)
        result = self.obj.AutoAttach.__wrapped__(self.obj, "service_level", {}, self.LOCALE)
        self.assertEqual(expected, result)

    def test_AutoAttach__not_registered(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        self.patches["is_registered"].return_value = False

        with self.assertRaisesRegex(dbus.DBusException, "requires the consumer to be registered"):
            self.obj.AutoAttach.__wrapped__(self.obj, ["x", "y"], 1, {}, self.LOCALE)
