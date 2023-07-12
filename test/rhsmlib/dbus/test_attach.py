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
from unittest import mock

from rhsmlib.dbus.objects.attach import AttachDBusImplementation
from subscription_manager.i18n import Locale

from test.rhsmlib.base import SubManDBusFixture
from test.rhsmlib.services.test_attach import CONTENT_JSON


class TestAttachDBusObject(SubManDBusFixture):
    def setUp(self) -> None:
        super().setUp()
        self.impl = AttachDBusImplementation()

        is_simple_content_access_patch = mock.patch(
            "rhsmlib.dbus.objects.attach.is_simple_content_access",
            name="is_simple_content_access",
        )
        self.patches["is_simple_content_access"] = is_simple_content_access_patch.start()
        self.addCleanup(is_simple_content_access_patch.stop)
        self.patches["is_simple_content_access"].return_value = False

        is_registered_patch = mock.patch(
            "rhsmlib.dbus.objects.attach.AttachDBusImplementation.is_registered",
            name="is_registered",
        )
        self.patches["is_registered"] = is_registered_patch.start()
        self.addCleanup(is_registered_patch.stop)
        self.patches["is_registered"].return_value = True

        update_patch = mock.patch(
            "subscription_manager.certlib.BaseActionInvoker.update",
            name="update",
        )
        self.patches["update"] = update_patch.start()
        self.addCleanup(update_patch.stop)
        self.patches["update"].return_value = None

        AttachService_patch = mock.patch(
            "rhsmlib.dbus.objects.attach.AttachService",
            name="AttachService",
            autospec=True,
        )
        self.mock_attach = AttachService_patch.start().return_value
        self.addCleanup(AttachService_patch.stop)

    def tearDown(self):
        Locale.set(self.LOCALE)

    def test_PoolAttach(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(result, expected)

    def test_PoolAttach__proxy(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(
            ["x", "y"],
            1,
            {
                "proxy_hostname": "proxy.company.com",
                "proxy_port": "3128",
                "proxy_user": "user",
                "proxy_password": "password",
            },
        )
        self.assertEqual(result, expected)

    def test_PoolAttach__de(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        Locale.set("de")

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        Locale.set("de_DE")

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE_utf8(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        Locale.set("de_DE.utf-8")

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(expected, result)

    def test_PoolAttach__de_DE_UTF8(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        Locale.set("de_DE.UTF-8")

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(expected, result)

    def test_PoolAttach__sca(self):
        self.patches["is_simple_content_access"].return_value = True
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        Locale.set("de_DE.UTF-8")

        # TODO: Change to assertRaises when auto-attach is not supported in SCA mode
        # BZ 2049101, BZ 2049620

        expected = [CONTENT_JSON, CONTENT_JSON]
        result = self.impl.pool_attach(["x", "y"], 1, {})
        self.assertEqual(expected, result)

    def test_PoolAttach__not_registered(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        self.patches["is_registered"].return_value = False

        with self.assertRaisesRegex(dbus.DBusException, "requires the consumer to be registered"):
            self.impl.pool_attach(["x", "y"], 1, {})

    def test_AutoAttach(self):
        self.mock_attach.attach_auto.return_value = CONTENT_JSON

        result = self.impl.auto_attach("service_level", {})
        self.assertEqual(CONTENT_JSON, result)

    def test_AutoAttach__sca(self):
        self.patches["is_simple_content_access"].return_value = True
        self.mock_attach.attach_auto.return_value = CONTENT_JSON

        # TODO: Change to assertRaises when auto-attach is not supported in SCA mode
        # BZ 2049101, BZ 2049620

        result = self.impl.auto_attach("service_level", {})
        self.assertEqual(CONTENT_JSON, result)

    def test_AutoAttach__not_registered(self):
        self.mock_attach.attach_pool.return_value = CONTENT_JSON
        self.patches["is_registered"].return_value = False

        with self.assertRaisesRegex(dbus.DBusException, "requires the consumer to be registered"):
            self.impl.auto_attach("service level", {})
