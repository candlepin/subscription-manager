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
import datetime
from unittest import mock

from test.rhsmlib.base import InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.cp_provider import CPProvider
from subscription_manager.cache import AvailableEntitlementsCache

from rhsm import connection

from rhsmlib.services import exceptions
from rhsmlib.services.entitlement import EntitlementService


class TestEntitlementService(InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection").return_value

        self.mock_ent_dir = mock.Mock(spec=EntitlementDirectory, name="EntitlementDirectory").return_value
        self.mock_cache_avail_ent = mock.Mock(
            spec=AvailableEntitlementsCache, name="AvailableEntitlements"
        ).return_value
        self.mock_cache_avail_ent.get_not_obsolete_data = mock.Mock(return_value=[])
        self.mock_cache_avail_ent.timeout = mock.Mock(return_value=10.0)
        self.mock_provider = mock.Mock(spec=CPProvider, name="CPProvider")
        self.mock_provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.ENT_DIR:
            return self.mock_ent_dir
        elif args[0] == inj.AVAILABLE_ENTITLEMENT_CACHE:
            return self.mock_cache_avail_ent
        elif args[0] == inj.CP_PROVIDER:
            return self.mock_provider
        else:
            return None

    def _build_options(
        self,
        pool_subsets=None,
        matches=None,
        pool_only=None,
        match_installed=None,
        no_overlap=None,
        service_level=None,
        show_all=None,
        on_date=None,
    ):
        return {
            "pool_subsets": pool_subsets,
            "matches": matches,
            "pool_only": pool_only,
            "match_installed": match_installed,
            "no_overlap": no_overlap,
            "service_level": service_level,
            "show_all": show_all,
            "on_date": on_date,
        }

    def test_get_status_when_unregistered(self):
        # Prime the injected dependencies with those built in injection_definitions
        service = EntitlementService()

        self.mock_identity.is_valid.return_value = False
        expected_value = {
            "status": "Unknown",
            "status_id": "unknown",
            "reasons": {},
            "reason_ids": {},
            "valid": False,
        }
        self.assertEqual(expected_value, service.get_status())

    def test_only_accepts_correct_pool_subsets(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["foo"])
        with self.assertRaisesRegex(exceptions.ValidationError, r".*invalid listing type.*"):
            service.validate_options(options)

    def test_show_all_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["installed"], show_all=True)
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_on_date_requires_available(self):
        service = EntitlementService()
        on_date = datetime.date.today().strftime("%Y-%m-%d")
        options = self._build_options(pool_subsets=["installed", "consumed"], on_date=on_date)
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_service_level_requires_consumed_or_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["installed"], service_level="foo")
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_match_installed_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["installed", "consumed"], match_installed=True)
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_no_overlap_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["installed", "consumed"], no_overlap=True)
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_pool_only_requires_consumed_or_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=["installed"], pool_only=True)
        with self.assertRaisesRegex(exceptions.ValidationError, r".*only applicable with --available"):
            service.validate_options(options)
        options["pool_subsets"].append("available")
        service.validate_options(options)

    def test_available_requires_registration(self):
        service = EntitlementService()
        self.mock_identity.is_valid.return_value = False
        options = self._build_options(pool_subsets=["available"])
        with self.assertRaisesRegex(exceptions.ValidationError, r".*not registered.*"):
            service.validate_options(options)

    @mock.patch("rhsmlib.services.entitlement.managerlib")
    def test_filter_only_specified_service_level(self, mock_managerlib):
        service = EntitlementService()
        pools = [{"service_level": "Level1"}, {"service_level": "Level2"}, {"service_level": "Level3"}]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(service_level="Level2")

        self.assertEqual(1, len(filtered))
        self.assertEqual("Level2", filtered[0]["service_level"])

    @mock.patch("rhsmlib.services.entitlement.managerlib")
    def test_pagged_result(self, mock_managerlib):
        service = EntitlementService()
        pools = [
            {"id": "ff8080816ea20fb9016ea21283ab02e0"},
            {"id": "ff8080816ea20fb9016ea21283ab02e1"},
            {"id": "ff8080816ea20fb9016ea21283ab02e2"},
            {"id": "ff8080816ea20fb9016ea21283ab02e3"},
            {"id": "ff8080816ea20fb9016ea21283ab02e4"},
        ]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(page=1, items_per_page=3)

        self.assertEqual(2, len(filtered))
        self.assertEqual("ff8080816ea20fb9016ea21283ab02e3", filtered[0]["id"])
        self.assertEqual(1, filtered[0]["page"])
        self.assertEqual(3, filtered[0]["items_per_page"])

    @mock.patch("rhsmlib.services.entitlement.managerlib")
    def test_no_pagged_result(self, mock_managerlib):
        service = EntitlementService()
        pools = [
            {"id": "ff8080816ea20fb9016ea21283ab02e0"},
            {"id": "ff8080816ea20fb9016ea21283ab02e1"},
            {"id": "ff8080816ea20fb9016ea21283ab02e2"},
            {"id": "ff8080816ea20fb9016ea21283ab02e3"},
            {"id": "ff8080816ea20fb9016ea21283ab02e4"},
        ]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(page=0, items_per_page=0)

        self.assertEqual(5, len(filtered))
        self.assertEqual("ff8080816ea20fb9016ea21283ab02e0", filtered[0]["id"])
        self.assertNotIn("page", filtered[0])
        self.assertNotIn("items_per_page", filtered[0])

    @mock.patch("rhsmlib.services.entitlement.managerlib")
    def test_pagged_result_too_big_page_value(self, mock_managerlib):
        service = EntitlementService()
        pools = [
            {"id": "ff8080816ea20fb9016ea21283ab02e0"},
            {"id": "ff8080816ea20fb9016ea21283ab02e1"},
            {"id": "ff8080816ea20fb9016ea21283ab02e2"},
            {"id": "ff8080816ea20fb9016ea21283ab02e3"},
            {"id": "ff8080816ea20fb9016ea21283ab02e4"},
        ]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(page=10, items_per_page=3)

        self.assertEqual(0, len(filtered))

    @mock.patch("rhsmlib.services.entitlement.managerlib")
    def test_no_pool_with_specified_filter(self, mock_managerlib):
        service = EntitlementService()
        pools = [{"service_level": "Level1"}]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(service_level="NotFound")
        self.assertEqual(0, len(filtered))

    def test_parse_valid_date(self):
        """
        Test parsing valid date
        """
        on_date = datetime.date.today().strftime("%Y-%m-%d")
        ent_service = EntitlementService(self.mock_cp)
        expected_result = datetime.datetime.strptime(on_date, "%Y-%m-%d")
        parsed_date = ent_service.parse_date(on_date)
        self.assertEqual(expected_result, parsed_date)

    def test_parse_invalid_date(self):
        """
        Test parsing invalid date (invalid format)
        """
        on_date = "2000-20-20"
        ent_service = EntitlementService(self.mock_cp)
        self.assertRaises(ValueError, ent_service.parse_date, on_date)

    def test_parse_yesterday(self):
        """
        Test parsing invalid date (past dates are not allowed)
        """
        yesterday = datetime.date.today() - datetime.timedelta(1)
        on_date = yesterday.strftime("%Y-%m-%d")
        ent_service = EntitlementService(self.mock_cp)
        self.assertRaises(ValueError, ent_service.parse_date, on_date)
