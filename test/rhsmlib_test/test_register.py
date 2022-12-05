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
import tempfile
from typing import Optional

import subscription_manager.injection as inj

from subscription_manager.cache import InstalledProductsManager, ContentAccessModeCache
from subscription_manager.cp_provider import CPProvider
from subscription_manager.facts import Facts
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager

from ..fixture import set_up_mock_sp_store

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from rhsm import connection

from rhsmlib.dbus import constants
from rhsmlib.dbus.server import DomainSocketServer
from rhsmlib.dbus.objects import RegisterDBusObject

from rhsmlib.services import register, exceptions

from test import subman_marker_dbus

CONSUMER_CONTENT_JSON = '''{"hypervisorId": "foo",
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
        "contentTags": null, "dev": false}'''

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

ENABLED_CONTENT = """[ {
  "created" : "2022-06-30T13:24:33+0000",
  "updated" : "2022-06-30T13:24:33+0000",
  "id" : "16def3d98d6549f8a3649f723a76991c",
  "consumer" : {
    "id" : "4028face81aa047e0181b4c8e1170bdc",
    "uuid" : "8503a41a-6ce2-480c-bc38-b67d6aa6dd20",
    "name" : "thinkpad-t580",
    "href" : "/consumers/8503a41a-6ce2-480c-bc38-b67d6aa6dd20"
  },
  "pool" : {
    "created" : "2022-06-28T11:14:35+0000",
    "updated" : "2022-06-30T13:24:33+0000",
    "id" : "4028face81aa047e0181aa052f740360",
    "type" : "NORMAL",
    "owner" : {
      "id" : "4028face81aa047e0181aa0490e30002",
      "key" : "admin",
      "displayName" : "Admin Owner",
      "href" : "/owners/admin",
      "contentAccessMode" : "entitlement"
    },
    "activeSubscription" : true,
    "sourceEntitlement" : null,
    "quantity" : 5,
    "startDate" : "2022-06-23T13:14:26+0000",
    "endDate" : "2023-06-23T13:14:26+0000",
    "attributes" : [ ],
    "restrictedToUsername" : null,
    "contractNumber" : "0",
    "accountNumber" : "6547096716",
    "orderNumber" : "order-23226139",
    "consumed" : 1,
    "exported" : 0,
    "branding" : [ ],
    "calculatedAttributes" : {
      "compliance_type" : "Standard"
    },
    "upstreamPoolId" : "upstream-05736148",
    "upstreamEntitlementId" : null,
    "upstreamConsumerId" : null,
    "productName" : "SP Server Standard (U: Development, R: SP Server)",
    "productId" : "sp-server-dev",
    "productAttributes" : [ {
      "name" : "management_enabled",
      "value" : "1"
    }, {
      "name" : "usage",
      "value" : "Development"
    }, {
      "name" : "roles",
      "value" : "SP Server"
    }, {
      "name" : "variant",
      "value" : "ALL"
    }, {
      "name" : "sockets",
      "value" : "128"
    }, {
      "name" : "support_level",
      "value" : "Standard"
    }, {
      "name" : "support_type",
      "value" : "L1-L3"
    }, {
      "name" : "arch",
      "value" : "ALL"
    }, {
      "name" : "type",
      "value" : "MKT"
    }, {
      "name" : "version",
      "value" : "1.0"
    } ],
    "stackId" : null,
    "stacked" : false,
    "sourceStackId" : null,
    "developmentPool" : false,
    "href" : "/pools/4028face81aa047e0181aa052f740360",
    "derivedProductAttributes" : [ ],
    "derivedProductId" : null,
    "derivedProductName" : null,
    "providedProducts" : [ {
      "productId" : "99000",
      "productName" : "SP Server Bits"
    } ],
    "derivedProvidedProducts" : [ ],
    "subscriptionSubKey" : "master",
    "subscriptionId" : "srcsub-45255972",
    "locked" : false
  },
  "quantity" : 1,
  "certificates" : [ {
    "created" : "2022-06-30T13:24:33+0000",
    "updated" : "2022-06-30T13:24:33+0000",
    "id" : "4028face81aa047e0181b4c8e4b90be1",
    "key" : "-----BEGIN PRIVATE KEY-----REDACTED-----END PRIVATE KEY-----",
    "cert" : "-----BEGIN CERTIFICATE-----REDACTED-----END RSA SIGNATURE-----",
    "serial" : {
      "created" : "2022-06-30T13:24:33+0000",
      "updated" : "2022-06-30T13:24:33+0000",
      "id" : 3712610178651551557,
      "serial" : 3712610178651551557,
      "expiration" : "2023-06-23T13:14:26+0000",
      "revoked" : false
    }
  } ],
  "startDate" : "2022-06-23T13:14:26+0000",
  "endDate" : "2023-06-23T13:14:26+0000",
  "href" : null
} ]
"""

# Following consumer do not contain information about content access mode
OLD_CONSUMER_CONTENT_JSON = '''{"hypervisorId": null,
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
        "contentTags": null, "dev": false}'''

OWNERS_CONTENT_JSON = '''[
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
'''


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

        # Add a mock for content access mode cache
        self.mock_content_access_mode_cache = mock.Mock(
            spec=ContentAccessModeCache,
            name="ContentAccessModeCache"
        )
        self.mock_content_access_mode_cache.read_data = mock.Mock(return_value='entitlement')

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
        elif args[0] == inj.CONTENT_ACCESS_MODE_CACHE:
            return self.mock_content_access_mode_cache
        else:
            return None

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", environments="environment")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments="environment",
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage="")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally_old_candlepin(self, mock_persist_consumer, mock_write_cache):
        """
        Test for the case, when candlepin server returns consumer without information about
        content access mode.
        """
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(OLD_CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        consumer = register_service.register("org", name="name", environments="environments")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments="environments",
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage="")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)
        assert 'owner' in consumer
        assert 'contentAccessMode' in consumer['owner']
        assert 'entitlement' == consumer['owner']['contentAccessMode']

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally_no_owner(self, mock_persist_consumer, mock_write_cache):
        """
        Test for the case, when candlepin server returns consumer without owner
        """
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(OLD_CONSUMER_CONTENT_JSON)
        del expected_consumer['owner']
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        consumer = register_service.register("org", name="name", environments="environments")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments="environments",
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage="")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)
        assert 'owner' not in consumer

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally_with_no_org_specified(self, mock_persist_consumer, mock_write_cache):
        """
        This test is intended for the case, when no organization is specified, but user is member
        only of one organization and thus it can be automatically selected
        """
        self.mock_cp.getOwnerList = mock.Mock()
        self.mock_cp.getOwnerList.return_value = [
            {
                "created": "2020-08-18T07:57:47+0000",
                "updated": "2020-08-18T07:57:47+0000",
                "id": "ff808081740092cd01740092fe540002",
                "key": "snowwhite",
                "displayName": "Snow White",
                "parentOwner": None,
                "contentPrefix": None,
                "defaultServiceLevel": None,
                "upstreamConsumer": None,
                "logLevel": None,
                "autobindDisabled": False,
                "autobindHypervisorDisabled": False,
                "contentAccessMode": "entitlement",
                "contentAccessModeList": "entitlement,org_environment",
                "lastRefreshed": None,
                "href": "/owners/snowwhite"
            }
        ]
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)

        def _get_owner_cb(orgs):
            pass

        def _no_owner_cb(username):
            pass

        org = register_service.determine_owner_key(
            username=self.mock_cp.username,
            get_owner_cb=_get_owner_cb,
            no_owner_cb=_no_owner_cb
        )

        self.assertIsNotNone(org)

        register_service.register(org, name="name", environments="environment")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="snowwhite",
            environments="environment",
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage="")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_with_activation_keys(self, mock_persist_consumer, mock_write_cache):
        self.mock_cp.username = None
        self.mock_cp.password = None
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []

        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", activation_keys=[1])

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments=None,
            keys=[1],
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            type="system",
            role="",
            addons=[],
            service_level="",
            usage=""
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_with_consumerid(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []

        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.getConsumer.return_value = json.loads(CONSUMER_CONTENT_JSON)

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", consumerid="consumerid")

        self.mock_cp.getConsumer.assert_called_once_with("consumerid")
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call('pre_register_consumer', name='name', facts={}),
            mock.call('post_register_consumer', consumer=expected_consumer, facts={})
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    def _build_options(self, activation_keys=None, environments=None, force=None, name=None, consumerid=None):
        return {
            'activation_keys': activation_keys,
            'environments': environments,
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

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_reads_syspurpose(self, mock_persist_consumer, mock_write_cache):
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        self.mock_identity.is_valid.return_value = False
        self.mock_sp_store_contents["role"] = "test_role"
        self.mock_sp_store_contents["service_level_agreement"] = "test_sla"
        self.mock_sp_store_contents["addons"] = ["addon1"]
        self.mock_sp_store_contents["usage"] = "test_usage"

        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name")

        self.mock_cp.registerConsumer.assert_called_once_with(
            addons=["addon1"],
            content_tags=[],
            environments=None,
            facts={},
            installed_products=[],
            jwt_token=None,
            keys=None,
            name="name",
            owner="org",
            role="test_role",
            service_level="test_sla",
            type="system",
            usage="test_usage")
        mock_write_cache.assert_called_once()

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
        options = self._build_options(activation_keys=[1], environments='environment')
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


@subman_marker_dbus
class DomainSocketRegisterDBusObjectTest(DBusObjectTest, InjectionMockingTest):
    socket_dir: Optional[tempfile.TemporaryDirectory] = None

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

        register_patcher = mock.patch('rhsmlib.dbus.objects.register.RegisterService', autospec=True)
        self.mock_register = register_patcher.start().return_value
        self.addCleanup(register_patcher.stop)

        unregister_patcher = mock.patch('rhsmlib.dbus.objects.unregister.UnregisterService.unregister')
        self.mock_unregister = unregister_patcher.start().return_value
        self.addCleanup(unregister_patcher.stop)

        cert_invoker_patcher = mock.patch('rhsmlib.dbus.objects.register.EntCertActionInvoker', autospec=True)
        self.mock_cert_invoker = cert_invoker_patcher.start().return_value
        self.addCleanup(cert_invoker_patcher.stop)

        attach_patcher = mock.patch("rhsmlib.dbus.objects.register.AttachService")
        self.mock_attach_invoker = attach_patcher.start()
        self.addCleanup(attach_patcher.stop)

        ent_cert_service_patcher = mock.patch("rhsmlib.dbus.objects.register.EntitlementService")
        self.mock_ent_cert_service_invoker = ent_cert_service_patcher.start()
        self.addCleanup(ent_cert_service_patcher.stop)

        self.socket_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.socket_dir.cleanup)
        socket_path_patch = mock.patch.object(DomainSocketServer, "_server_socket_path", self.socket_dir.name)
        socket_path_patch.start()
        # `tmpdir` behaves differently from `dir` on old versions of dbus
        # (earlier than 1.12.24 and 1.14.4).
        # In newer versions we are not getting abstract socket anymore.
        socket_iface_patch = mock.patch.object(DomainSocketServer, "_server_socket_iface", "unix:dir=")
        socket_iface_patch.start()

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
            six.assertRegex(self, result, self.socket_dir.name + "/dbus.*")

        self.dbus_request(assertions, self.interface.Start, dbus_method_args)

    def test_same_socket_on_subsequent_opens(self):
        dbus_method_args = ['']

        def assertions(*args):
            # Assign the result as an attribute to this function.
            # See http://stackoverflow.com/a/27910553/6124862
            assertions.result = args[0]
            six.assertRegex(self, assertions.result, self.socket_dir.name + "/dbus.*")

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
            sock.connect(get_address.address)
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
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ['admin', 'admin', 'admin', {}, {}, '']
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_cannot_register_over_domain_socket_when_already_registered(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ['admin', 'admin', 'admin', {}, {}, '']
        with self.assertRaisesRegexp(dbus.exceptions.DBusException, r'.* system is already registered.'):
            self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_register_over_domain_socket_with_force_option(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = ['admin', 'admin', 'admin', {'force': True}, {}, '']
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_register_over_domain_socket_no_enabled_content(self):
        """
        Test calling Register method with argument "enable_content", when
        access mode is entitlement and no content is enabled (e.g. due to
        no installed product certs.)
        """

        def assertions(*args):
            expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
            # Test that enabled content (with empty list) was injected to consumer object
            expected_consumer["enabledContent"] = []
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = json.loads(CONSUMER_CONTENT_JSON)

        # Return empty list of consumed entitlement certificates (e.g. no installed product certs)
        mock_attach_service_instance = mock.Mock(name="Mock of AttachService instance")
        mock_attach_service_instance.attach_auto = mock.Mock(name="Mock of AttachService.attach_auto()")
        # Empty list of consumed ent. certs.
        mock_attach_service_instance.attach_auto.return_value = []
        self.mock_attach_invoker.return_value = mock_attach_service_instance

        dbus_method_args = ["admin", "admin", "admin", {"enable_content": "1"}, {}, ""]
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_register_over_domain_socket_enable_content(self):
        """
        Test calling Register method with argument "enable_content", when
        access mode is entitlement and some content is enabled during auto-attach
        """
        enabled_content = json.loads(ENABLED_CONTENT)

        def assertions(*args):
            consumer = json.loads(args[0])
            expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
            # Test that enabled content was injected to consumer object
            expected_consumer["enabledContent"] = enabled_content
            self.assertEqual(consumer, expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = json.loads(CONSUMER_CONTENT_JSON)

        # Return list of consumed entitlement certificates
        mock_attach_service_instance = mock.Mock(name="Mock of AttachService instance")
        mock_attach_service_instance.attach_auto = mock.Mock(name="Mock of AttachService.attach_auto()")
        mock_attach_service_instance.attach_auto.return_value = enabled_content
        self.mock_attach_invoker.return_value = mock_attach_service_instance

        dbus_method_args = ["admin", "admin", "admin", {"enable_content": "1"}, {}, ""]
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_register_over_domain_socket_enable_content_sca(self):
        """
        Test calling Register method with argument "enable_content", when
        SCA mode is used
        """

        def assertions(*args):
            # Be sure we are persisting the consumer cert and nothing is injected
            # to consumer object, when SCA mode is used
            expected_consumer = json.loads(CONSUMER_CONTENT_JSON_SCA)
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        self.mock_register.register.return_value = json.loads(CONSUMER_CONTENT_JSON_SCA)

        dbus_method_args = ["admin", "admin", "admin", {"enable_content": "1"}, {}, ""]
        self.dbus_request(assertions, self._build_interface().Register, dbus_method_args)

    def test_can_get_orgs_over_domain_socket(self):
        def assertions(*args):
            # Be sure the returned json contains list of orgs
            expected_owners = json.loads(OWNERS_CONTENT_JSON)
            self.assertEqual(json.loads(args[0]), expected_owners)

        self.mock_identity.is_valid.return_value = False
        self.mock_identity.uuid = "INVALIDCONSUMERUUID"

        dbus_method_args = ["admin", "admin", {}, ""]
        self.dbus_request(assertions, self._build_interface().GetOrgs, dbus_method_args)

    def test_can_register_over_domain_socket_with_activation_keys(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

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

    def test_cannot_register_over_domain_socket_with_activation_keys_when_already_registered(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = True
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

        with self.assertRaisesRegexp(dbus.exceptions.DBusException, r'.* system is already registered.'):
            self.dbus_request(assertions, self._build_interface().RegisterWithActivationKeys, dbus_method_args)

    def test_can_register_over_domain_socket_with_activation_keys_and_force_option(self):
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)

        def assertions(*args):
            # Be sure we are persisting the consumer cert
            self.assertEqual(json.loads(args[0]), expected_consumer)

        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = 'INVALIDCONSUMERUUID'

        self.mock_register.register.return_value = expected_consumer

        dbus_method_args = [
            'admin',
            ['key1', 'key2'],
            {'force': True},
            {
                'host': 'localhost',
                'port': '8443',
                'handler': '/candlepin'
            },
            ''
        ]

        self.dbus_request(assertions, self._build_interface().RegisterWithActivationKeys, dbus_method_args)
