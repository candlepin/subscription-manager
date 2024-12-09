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

from unittest import mock
import json

import subscription_manager.injection as inj

from subscription_manager.cache import InstalledProductsManager
from subscription_manager.cp_provider import CPProvider
from subscription_manager.facts import Facts
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager

from test.fixture import set_up_mock_sp_store

from test.rhsmlib.base import InjectionMockingTest

from rhsm import connection

from rhsmlib.services import register, exceptions

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
          "contentAccessMode": "org_environment"
        },
        "href": "/consumers/c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "facts": {}, "id": "ff808081550d997c015511b0406d1065",
        "uuid": "c1b8648c-6f0a-4aa5-b34e-b9e62c0e4364",
        "guestIds": null, "capabilities": null,
        "environment": {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-1",
          "name" : "env-name-1",
          "type" : "content-template",
          "description" : "Testing environment #1",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        },
        "installedProducts": null,
        "canActivate": false, "type": {"manifest": false,
        "id": "1000", "label": "system"}, "annotations": null,
        "username": "admin", "updated": "2016-06-02T15:16:51+0000",
        "lastCheckin": null, "entitlementCount": 0, "releaseVer":
        {"releaseVer": null}, "entitlementStatus": "valid", "name":
        "test.example.com", "created": "2016-06-02T15:16:51+0000",
        "contentTags": null,
        "dev": false,
        "environments": [ {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-1",
          "name" : "env-name-1",
          "type" : "content-template",
          "description" : "Testing environment #1",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        },
        {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-2",
          "name" : "env-name-2",
          "type" : "content-template",
          "description" : "Testing environment #2",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        } ] }"""

CONSUMER_CONTENT_JSON_WRONG_ENT_TYPE = """{"hypervisorId": null,
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
        "environment": {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-1",
          "name" : "env-name-1",
          "type" : "content-template",
          "description" : "Testing environment #1",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        },
        "installedProducts": null,
        "canActivate": false, "type": {"manifest": false,
        "id": "1000", "label": "system"}, "annotations": null,
        "username": "admin", "updated": "2016-06-02T15:16:51+0000",
        "lastCheckin": null, "entitlementCount": 0, "releaseVer":
        {"releaseVer": null}, "entitlementStatus": "valid", "name":
        "test.example.com", "created": "2016-06-02T15:16:51+0000",
        "contentTags": null,
        "dev": false,
        "environments": [ {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-1",
          "name" : "env-name-1",
          "type" : "content-template",
          "description" : "Testing environment #1",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        },
        {
          "created" : "2024-12-09T09:25:17+0000",
          "updated" : "2024-12-09T09:25:17+0000",
          "id" : "env-id-2",
          "name" : "env-name-2",
          "type" : "wrong_type_foo",
          "description" : "Testing environment #2",
          "contentPrefix" : null,
          "owner" : {
            "id" : "ff808081550d997c01550d9adaf40003",
            "key" : "admin",
            "displayName" : "Admin Owner",
            "href" : "/owners/admin",
            "contentAccessMode" : "org_environment"
          },
          "environmentContent" : [ ]
        } ] }"""

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

        # For the tests in which it's used, the consumer_auth cp and basic_auth cp can be the same
        self.mock_cp_provider.get_consumer_auth_cp.return_value = self.mock_cp
        self.mock_cp_provider.get_basic_auth_cp.return_value = self.mock_cp

        self.mock_pm = mock.Mock(spec=PluginManager, name="PluginManager")
        self.mock_installed_products = mock.Mock(
            spec=InstalledProductsManager, name="InstalledProductsManager"
        )
        self.mock_facts = mock.Mock(spec=Facts, name="Facts")
        self.mock_facts.get_facts.return_value = {}

        syspurpose_patch = mock.patch("subscription_manager.syspurposelib.SyncedStore")
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
        register_service.register("org", name="name", environments=["environment"])

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments=["environment"],
            environment_names=None,
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_multiple_environment_ids(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", environments=["env-id-1", "env-id-2"])

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments=["env-id-1", "env-id-2"],
            environment_names=None,
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_multiple_environment_names(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register("org", name="name", environment_names=["env-name-1", "env-name-2"])

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments=None,
            environment_names=["env-name-1", "env-name-2"],
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_environment_name_type(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        register_service.register(
            "org",
            name="name",
            environment_names=["env-name-1", "env-name-2"],
            environment_type="content-template",
        )

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="org",
            environments=None,
            environment_names=["env-name-1", "env-name-2"],
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_environment_name_wrong_type(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON_WRONG_ENT_TYPE)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)

        with self.assertRaises(Exception):
            register_service.register(
                "org",
                name="name",
                environment_names=["env-name-1", "env-name-2"],
                environment_type="content-template",
            )

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_not_allow_environment_ids_and_names(self, mock_persist_consumer, mock_write_cache):
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(CONSUMER_CONTENT_JSON)
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        with self.assertRaisesRegex(
            exceptions.ValidationError, r".*Environment IDs and environment names are mutually exclusive.*"
        ):
            register_service.register(
                "org",
                name="name",
                environments=["env-id-1", "env-id-2"],
                environment_names=["env-name-1", "env-name-2"],
            )

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.clean_all_data", return_value=None)
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally_old_candlepin(self, mock_persist_consumer, mock_clean, mock_write_cache):
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
        with self.assertRaises(exceptions.ServiceError) as exc_info:
            register_service.register("org", name="name", environments=["environment"])
            self.assertEqual(
                str(exc_info.exception),
                "Registration is only possible when the organization is in Simple Content Access Mode.",
            )

    @mock.patch("rhsmlib.services.register.syspurposelib.write_syspurpose_cache", return_value=True)
    @mock.patch("rhsmlib.services.register.managerlib.clean_all_data")
    @mock.patch("rhsmlib.services.register.managerlib.persist_consumer_cert")
    def test_register_normally_no_owner(self, mock_persist_consumer, mock_clean, mock_write_cache):
        """
        Test for the case, when candlepin server returns consumer without owner
        """
        self.mock_identity.is_valid.return_value = False
        self.mock_installed_products.format_for_server.return_value = []
        self.mock_installed_products.tags = []
        expected_consumer = json.loads(OLD_CONSUMER_CONTENT_JSON)
        del expected_consumer["owner"]
        self.mock_cp.registerConsumer.return_value = expected_consumer

        register_service = register.RegisterService(self.mock_cp)
        with self.assertRaises(exceptions.ServiceError) as exc_info:
            register_service.register("org", name="name", environments=["environment"])
            self.assertEqual(
                str(exc_info.exception),
                "Registration is only possible when the organization is in Simple Content Access Mode.",
            )

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
                "href": "/owners/snowwhite",
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
            username=self.mock_cp.username, get_owner_cb=_get_owner_cb, no_owner_cb=_no_owner_cb
        )

        self.assertIsNotNone(org)

        register_service.register(org, name="name")

        self.mock_cp.registerConsumer.assert_called_once_with(
            name="name",
            facts={},
            owner="snowwhite",
            environments=None,
            environment_names=None,
            keys=None,
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
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
            environment_names=None,
            keys=[1],
            installed_products=[],
            jwt_token=None,
            content_tags=[],
            consumer_type="system",
            role="",
            addons=[],
            service_level="",
            usage="",
        )
        self.mock_installed_products.write_cache.assert_called()

        mock_persist_consumer.assert_called_once_with(expected_consumer)
        mock_write_cache.assert_called_once()
        expected_plugin_calls = [
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
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
            mock.call("pre_register_consumer", name="name", facts={}),
            mock.call("post_register_consumer", consumer=expected_consumer, facts={}),
        ]
        self.assertEqual(expected_plugin_calls, self.mock_pm.run.call_args_list)

    def _build_options(self, activation_keys=None, environments=None, force=None, name=None, consumerid=None):
        return {
            "activation_keys": activation_keys,
            "environments": environments,
            "force": force,
            "name": name,
            "consumerid": consumerid,
        }

    def test_fails_when_previously_registered(self):
        self.mock_identity.is_valid.return_value = True

        with self.assertRaisesRegex(exceptions.ValidationError, r".*system is already registered.*"):
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
            environment_names=None,
            facts={},
            installed_products=[],
            jwt_token=None,
            keys=None,
            name="name",
            owner="org",
            role="test_role",
            service_level="test_sla",
            consumer_type="system",
            usage="test_usage",
        )
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
        with self.assertRaisesRegex(exceptions.ValidationError, r".*do not require user credentials.*"):
            register.RegisterService(self.mock_cp).validate_options(options)

    def test_does_not_allow_environment_with_consumerid(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(activation_keys=[1], consumerid="consumerid")
        with self.assertRaisesRegex(exceptions.ValidationError, r".*previously registered.*"):
            register.RegisterService(self.mock_cp).validate_options(options)

    def test_requires_basic_auth_for_normal_registration(self):
        self.mock_cp.username = None
        self.mock_cp.password = None

        self.mock_identity.is_valid.return_value = False
        options = self._build_options(consumerid="consumerid")
        with self.assertRaisesRegex(exceptions.ValidationError, r".*Missing username.*"):
            register.RegisterService(self.mock_cp).validate_options(options)
