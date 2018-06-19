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
import mock
import json
import datetime

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.validity import ValidProductDateRangeCalculator
from subscription_manager.cp_provider import CPProvider

from test import stubs

from rhsm import connection

from rhsmlib.dbus.objects import ProductsDBusObject
from rhsmlib.dbus import constants
from rhsmlib.services import products


START_DATE = datetime.datetime.now() - datetime.timedelta(days=100)
NOW_DATE = datetime.datetime.now()
END_DATE = datetime.datetime.now() + datetime.timedelta(days=265)


NO_CONTENT_JSON = [{
    "id": "4028fa7a5da1fbc2015da203aba209b7",
    "uuid": "57b7dbff-9489-43ac-991a-b848324b423a",
    "name": "localhost.localdomain",
    "username": "admin",
    "entitlementStatus": "valid",
    "serviceLevel": "",
    "releaseVer": {
        "releaseVer": None
    },
    "idCert": {
        "key": "FAKE RSA PRIVATE KEY",
        "cert": "FAKE CERTIFICATE",
        "serial": {
            "id": 8134386700568860251,
            "revoked": False,
            "collected": False,
            "expiration": END_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "serial": 8134386700568860251,
            "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
        },
        "id": "4028fa7a5da1fbc2015da203ad8c09b9",
        "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
    },
    "type": {
        "id": "1000",
        "label": "system",
        "manifest": False
    },
    "owner": {
        "id": "4028fa7a5da1fbc2015da1fdb5380004",
        "key": "admin",
        "displayName": "Admin Owner",
        "href": "/owners/admin"
    },
    "environment": None,
    "entitlementCount": 0,
    "facts": {},
    "lastCheckin": NOW_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
    "installedProducts": [],
    "canActivate": False,
    "capabilities": [],
    "hypervisorId": None,
    "contentTags": [],
    "autoheal": True,
    "contentAccessMode": None,
    "recipientOwnerKey": None,
    "annotations": None,
    "href": "/consumers/57b7dbff-9489-43ac-991a-b848324b423a",
    "dev": False,
    "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
    "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
}]

CONTENT_JSON = [{
    "id": "4028fa7a5da1fbc2015da203aba209b7",
    "uuid": "57b7dbff-9489-43ac-991a-b848324b423a",
    "name": "localhost.localdomain",
    "username": "admin",
    "entitlementStatus": "valid",
    "serviceLevel": "",
    "releaseVer": {
        "releaseVer": None
    },
    "idCert": {
        "key": "FAKE RSA PRIVATE KEY",
        "cert": "FAKE CERTIFICATE",
        "serial": {
            "id": 8134386700568860251,
            "revoked": False,
            "collected": False,
            "expiration": END_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "serial": 8134386700568860251,
            "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
        },
        "id": "4028fa7a5da1fbc2015da203ad8c09b9",
        "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
    },
    "type": {
        "id": "1000",
        "label": "system",
        "manifest": False
    },
    "owner": {
        "id": "4028fa7a5da1fbc2015da1fdb5380004",
        "key": "admin",
        "displayName": "Admin Owner",
        "href": "/owners/admin"
    },
    "environment": None,
    "entitlementCount": 0,
    "facts": {},
    "lastCheckin": "2017-08-02T08:16:39+0000",
    "installedProducts": [
        {
            "id": "8a99f9895d8b4f96015d9db99e9971fb",
            "productId": "69",
            "productName": "Red Hat Enterprise Linux Server",
            "version": "7.4",
            "arch": "x86_64",
            "status": "green",
            "startDate": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "endDate": END_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
        },
        {
            "id": "8a99f9895d8b4f96015d9db99e9971fc",
            "productId": "70",
            "productName": "Red Hat Enterprise Linux Server - Extended Update Support",
            "version": "7.2",
            "arch": "x86_64",
            "status": "green",
            "startDate": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "endDate": END_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
        }
    ],
    "canActivate": False,
    "capabilities": [],
    "hypervisorId": None,
    "contentTags": [],
    "autoheal": True,
    "contentAccessMode": None,
    "recipientOwnerKey": None,
    "annotations": None,
    "href": "/consumers/57b7dbff-9489-43ac-991a-b848324b423a",
    "dev": False,
    "created": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000"),
    "updated": START_DATE.strftime("%Y-%m-%dT%H:%M:%S+0000")
}]


class TestProductService(InjectionMockingTest):
    def setUp(self):
        super(TestProductService, self).setUp()
        self.mock_cert_sorter = mock.Mock(spec=CertSorter, name="CertSorter")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")
        self.mock_calculator = mock.Mock(spec=ValidProductDateRangeCalculator, name="ValidProductDateRangeCalculator")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.CERT_SORTER:
            return self.mock_cert_sorter
        elif args[0] == inj.PRODUCT_DATE_RANGE_CALCULATOR:
            return self.mock_calculator
        else:
            return None

    def _create_rhel74_cert(self):
        return self._create_cert("69", "Red Hat Enterprise Linux Server",
                                 "7.4", "rhel-7,rhel-7-server")

    def _create_rhel72_ues_cert(self):
        return self._create_cert("70", "Red Hat Enterprise Linux Server - Extended Update Support",
                                 "7.2", "rhel-7-eus-server,rhel-7-server")

    @staticmethod
    def _create_cert(product_id, name, version, provided_tags):
        cert = stubs.StubProductCertificate(
            product=stubs.StubProduct(
                product_id=product_id,
                name=name,
                version=version,
                provided_tags=provided_tags
            ),
            start_date=START_DATE,
            end_date=END_DATE
        )
        cert.delete = mock.Mock()
        cert.write = mock.Mock()
        return cert

    def test_list_no_installed_products(self):
        self.mock_cp.getConsumer.return_value = NO_CONTENT_JSON
        self.mock_cert_sorter.installed_products = []

        result = products.InstalledProducts(self.mock_cp).list()
        self.assertEqual([], result)

    def test_list_installed_products_without_filter(self):
        self.mock_cp.getConsumer.return_value = CONTENT_JSON
        self.mock_cert_sorter.reasons = mock.Mock()
        self.mock_cert_sorter.reasons.get_product_reasons = mock.Mock(return_value=[])
        self.mock_cert_sorter.get_status = mock.Mock(return_value="subscribed")
        # Mock methods in calculator
        self.mock_calculator.calculate = mock.Mock()

        self.mock_calculator.calculate.return_value.begin = mock.Mock()
        self.mock_calculator.calculate.return_value.begin.return_value.astimezone = mock.Mock()
        self.mock_calculator.calculate.return_value.begin.return_value.astimezone.return_value.strftime = mock.Mock(
            return_value='{d.day}.{d.month}.{d.year}'.format(d=START_DATE)
        )
        self.mock_calculator.calculate.return_value.end = mock.Mock()
        self.mock_calculator.calculate.return_value.end.return_value.astimezone = mock.Mock()
        self.mock_calculator.calculate.return_value.end.return_value.astimezone.return_value.strftime = mock.Mock(
            return_value='{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
        )

        expected_result = [
            (
                u'Red Hat Enterprise Linux Server',
                '69',
                u'7.4',
                u'x86_64',
                'subscribed',
                [],
                '{d.day}.{d.month}.{d.year}'.format(d=START_DATE),
                '{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
            ),
            (
                u'Red Hat Enterprise Linux Server - Extended Update Support',
                '70',
                u'7.2',
                u'x86_64',
                'subscribed',
                [],
                '{d.day}.{d.month}.{d.year}'.format(d=START_DATE),
                '{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
            ),
        ]

        self.mock_cert_sorter.installed_products = {
            '69': self._create_rhel74_cert(),
            '70': self._create_rhel72_ues_cert()
        }

        result = products.InstalledProducts(self.mock_cp).list()

        self.assertEqual(expected_result, result)

    def test_list_installed_products_with_filter(self):
        self.mock_cp.getConsumer.return_value = CONTENT_JSON
        self.mock_cert_sorter.reasons = mock.Mock()
        self.mock_cert_sorter.reasons.get_product_reasons = mock.Mock(return_value=[])
        self.mock_cert_sorter.get_status = mock.Mock(return_value="subscribed")
        # Mock methods in calculator
        self.mock_calculator.calculate = mock.Mock()

        self.mock_calculator.calculate.return_value.begin = mock.Mock()
        self.mock_calculator.calculate.return_value.begin.return_value.astimezone = mock.Mock()
        self.mock_calculator.calculate.return_value.begin.return_value.astimezone.return_value.strftime = mock.Mock(
            return_value='{d.day}.{d.month}.{d.year}'.format(d=START_DATE)
        )
        self.mock_calculator.calculate.return_value.end = mock.Mock()
        self.mock_calculator.calculate.return_value.end.return_value.astimezone = mock.Mock()
        self.mock_calculator.calculate.return_value.end.return_value.astimezone.return_value.strftime = mock.Mock(
            return_value='{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
        )

        expected_result = [
            (
                u'Red Hat Enterprise Linux Server - Extended Update Support',
                '70',
                u'7.2',
                u'x86_64',
                'subscribed',
                [],
                '{d.day}.{d.month}.{d.year}'.format(d=START_DATE),
                '{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
            ),
        ]

        self.mock_cert_sorter.installed_products = {
            '69': self._create_rhel74_cert(),
            '70': self._create_rhel72_ues_cert()
        }

        result = products.InstalledProducts(self.mock_cp).list("*Extended*")

        self.assertEqual(expected_result, result)


class TestProductsDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestProductsDBusObject, self).setUp()
        self.proxy = self.proxy_for(ProductsDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.PRODUCTS_INTERFACE)

        products_patcher = mock.patch('rhsmlib.dbus.objects.products.InstalledProducts')
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
                u'Red Hat Enterprise Linux Server',
                '69',
                u'7.4',
                u'x86_64',
                'subscribed',
                [],
                '{d.day}.{d.month}.{d.year}'.format(d=START_DATE),
                '{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
            ),
            (
                u'Red Hat Enterprise Linux Server - Extended Update Support',
                '70',
                u'7.2',
                u'x86_64',
                'subscribed',
                [],
                '{d.day}.{d.month}.{d.year}'.format(d=START_DATE),
                '{d.day}.{d.month}.{d.year}'.format(d=END_DATE)
            ),
        ]

        def assertions(*args):
            result = args[0]
            self.assertEqual(result, json.dumps(expected_result))

        self.mock_products.list.return_value = expected_result

        dbus_method_args = ['', {}, '']
        self.dbus_request(assertions, self.interface.ListInstalledProducts, dbus_method_args)
