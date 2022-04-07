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
import json
import datetime

from test.rhsmlib.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.cp_provider import CPProvider

from rhsmlib.dbus.objects import ProductsDBusObject
from rhsmlib.dbus import constants

from test import subman_marker_dbus


START_DATE = datetime.datetime.now() - datetime.timedelta(days=100)
NOW_DATE = datetime.datetime.now()
END_DATE = datetime.datetime.now() + datetime.timedelta(days=265)


@subman_marker_dbus
class TestProductsDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestProductsDBusObject, self).setUp()
        self.proxy = self.proxy_for(ProductsDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.PRODUCTS_INTERFACE)

        products_patcher = mock.patch("rhsmlib.dbus.objects.products.InstalledProducts")
        self.mock_products = products_patcher.start().return_value
        self.addCleanup(products_patcher.stop)
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "id"

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CP_PROVIDER:
            provider = mock.Mock(spec=CPProvider, name="CPProvider")
            provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")
            return provider
        else:
            return None

    def dbus_objects(self):
        return [ProductsDBusObject]

    def test_list_installed_products_without_filter(self):
        expected_result = [
            (
                "Red Hat Enterprise Linux Server",
                "69",
                "7.4",
                "x86_64",
                "subscribed",
                [],
                START_DATE.strftime("%Y-%m-%d"),
                END_DATE.strftime("%Y-%m-%d"),
            ),
            (
                "Red Hat Enterprise Linux Server - Extended Update Support",
                "70",
                "7.2",
                "x86_64",
                "subscribed",
                [],
                START_DATE.strftime("%Y-%m-%d"),
                END_DATE.strftime("%Y-%m-%d"),
            ),
        ]

        def assertions(*args):
            result = args[0]
            self.assertEqual(result, json.dumps(expected_result))

        self.mock_products.list.return_value = expected_result

        dbus_method_args = ["", {}, ""]
        self.dbus_request(assertions, self.interface.ListInstalledProducts, dbus_method_args)
