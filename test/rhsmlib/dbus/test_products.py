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
import mock
import json
import datetime

from rhsmlib.dbus.objects import ProductsDBusObject

from test.rhsmlib.base import DBusServerStubProvider


START_DATE = datetime.datetime.now() - datetime.timedelta(days=100)
NOW_DATE = datetime.datetime.now()
END_DATE = datetime.datetime.now() + datetime.timedelta(days=265)


class TestProductsDBusObject(DBusServerStubProvider):
    dbus_class = ProductsDBusObject
    dbus_class_kwargs = {}

    @classmethod
    def setUpClass(cls) -> None:
        list_patch = mock.patch(
            "rhsmlib.dbus.objects.products.InstalledProducts.list",
            name="list",
        )
        cls.patches["list"] = list_patch.start()
        cls.addClassCleanup(list_patch.stop)

        super().setUpClass()

    def test_ListInstalledProducts__no_filter(self):
        expected = [
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

        self.patches["list"].return_value = expected

        result = self.obj.ListInstalledProducts.__wrapped__(self.obj, "", {}, self.LOCALE)
        self.assertEqual(json.dumps(expected), result)
