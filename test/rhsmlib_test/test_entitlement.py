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
import datetime
import dbus
import mock
import json

from test.rhsmlib_test.base import InjectionMockingTest, DBusObjectTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.reasons import Reasons
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.cp_provider import CPProvider

from rhsm import connection

from rhsmlib.dbus import constants
from rhsmlib.dbus.objects import EntitlementDBusObject

from rhsmlib.services import exceptions
from rhsmlib.services.entitlement import EntitlementService


class TestEntitlementService(InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity").return_value
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection").return_value
        self.mock_sorter_class = mock.Mock(spec=CertSorter, name="CertSorter")
        self.mock_ent_dir = mock.Mock(spec=EntitlementDirectory, name="EntitlementDirectory").return_value

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CERT_SORTER:
            # This sleight of hand is needed because we want to check the arguments given
            # when the cert sorter is instantiated.
            instance = self.mock_sorter_class(*args[1:])
            self.mock_sorter_class.return_value = instance
            return instance
        elif args[0] == inj.ENT_DIR:
            return self.mock_ent_dir
        else:
            return None

    def test_get_status(self):
        # Prime the injected dependencies built in injection_definitions
        service = EntitlementService()

        self.mock_identity.is_valid.return_value = True

        mock_reasons = mock.Mock(spec=Reasons, name="Reasons").return_value
        mock_reasons.get_name_message_map.return_value = {"RHEL": ["Not supported by a valid subscription"]}

        mock_sorter = self.mock_sorter_class.return_value
        mock_sorter.get_system_status.return_value = "Invalid"
        mock_sorter.reasons = mock_reasons
        mock_sorter.is_valid.return_value = False

        expected_value = {
            'status': 'Invalid',
            'reasons': {
                'RHEL': ['Not supported by a valid subscription']
            },
            'valid': False
        }

        self.assertEqual(expected_value, service.get_status())

    def test_get_status_on_date(self):
        # Prime the injected dependencies with those built in injection_definitions
        service = EntitlementService()

        # Verify the cert_sorter was constructed for a specific date
        mock_sorter = self.mock_sorter_class.return_value

        self.mock_identity.is_valid.return_value = True

        mock_reasons = mock.Mock(spec=Reasons, name="Reasons").return_value
        mock_reasons.get_name_message_map.return_value = {"RHEL": ["Not supported by a valid subscription"]}

        mock_sorter.get_system_status.return_value = "Invalid"
        mock_sorter.reasons = mock_reasons
        mock_sorter.is_valid.return_value = False

        expected_value = {
            'status': 'Invalid',
            'reasons': {
                'RHEL': ['Not supported by a valid subscription']
            },
            'valid': False
        }

        self.assertEqual(expected_value, service.get_status("some_date"))
        self.mock_sorter_class.assert_called_once_with("some_date")

    def _build_options(self, pool_subsets=None, matches=None, pool_only=None, match_installed=None,
            no_overlap=None, service_level=None, show_all=None, on_date=None):
        return {
            'pool_subsets': pool_subsets,
            'matches': matches,
            'pool_only': pool_only,
            'match_installed': match_installed,
            'no_overlap': no_overlap,
            'service_level': service_level,
            'show_all': show_all,
            'on_date': on_date,
        }

    def test_get_status_when_unregistered(self):
        # Prime the injected dependencies with those built in injection_definitions
        service = EntitlementService()

        self.mock_identity.is_valid.return_value = False
        expected_value = {'status': 'Unknown', 'reasons': {}, 'valid': False}
        self.assertEqual(expected_value, service.get_status())

    def test_only_accepts_correct_pool_subsets(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['foo'])
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*invalid listing type.*'):
            service.validate_options(options)

    def test_show_all_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['installed'], show_all=True)
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_on_date_requires_available(self):
        service = EntitlementService()
        on_date = datetime.date.today().strftime('%Y-%m-%d')
        options = self._build_options(pool_subsets=['installed', 'consumed'], on_date=on_date)
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_service_level_requires_consumed_or_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['installed'], service_level='foo')
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_match_installed_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['installed', 'consumed'], match_installed=True)
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_no_overlap_requires_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['installed', 'consumed'], no_overlap=True)
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_pool_only_requires_consumed_or_available(self):
        service = EntitlementService()
        options = self._build_options(pool_subsets=['installed'], pool_only=True)
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*only applicable with --available'):
            service.validate_options(options)
        options['pool_subsets'].append('available')
        service.validate_options(options)

    def test_available_requires_registration(self):
        service = EntitlementService()
        self.mock_identity.is_valid.return_value = False
        options = self._build_options(pool_subsets=['available'])
        with self.assertRaisesRegexp(exceptions.ValidationError, r'.*not registered.*'):
            service.validate_options(options)

    @mock.patch('rhsmlib.services.entitlement.managerlib')
    def test_filter_only_specified_service_level(self, mock_managerlib):
        service = EntitlementService()
        pools = [{'service_level': 'Level1'},
                 {'service_level': 'Level2'},
                 {'service_level': 'Level3'}]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(service_level="Level2")

        self.assertEqual(1, len(filtered))
        self.assertEqual("Level2", filtered[0]['service_level'])

    @mock.patch('rhsmlib.services.entitlement.managerlib')
    def test_no_pool_with_specified_filter(self, mock_managerlib):
        service = EntitlementService()
        pools = [{'service_level': 'Level1'}]
        mock_managerlib.get_available_entitlements.return_value = pools

        filtered = service.get_available_pools(service_level="NotFound")
        self.assertEqual(0, len(filtered))

    def test_remove_all_pools(self):
        """
        Test of removing all pools
        """
        ent_service = EntitlementService(self.mock_cp)
        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()
        ent_service.cp.unbindAll = mock.Mock(return_value='[]')

        response = ent_service.remove_all_entitlements()
        self.assertEqual(response, '[]')

    def test_remove_all_pools_by_id(self):
        """
        Test of removing all pools by IDs of pool
        """
        ent_service = EntitlementService(self.mock_cp)
        ent_service.cp.unbindByPoolId = mock.Mock()
        ent_service.entitlement_dir.list_serials_for_pool_ids = mock.Mock(return_value={
            '4028fa7a5dea087d015dea0b025003f6': ['6219625278114868779'],
            '4028fa7a5dea087d015dea0adf560152': ['3573249574655121394']
        })
        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_pools, unremoved_pools, removed_serials = ent_service.remove_entilements_by_pool_ids(
            ['4028fa7a5dea087d015dea0b025003f6',
             '4028fa7a5dea087d015dea0adf560152']
        )

        expected_removed_serials = [
            '6219625278114868779',
            '3573249574655121394'
        ]
        expected_removed_pools = [
            '4028fa7a5dea087d015dea0b025003f6',
            '4028fa7a5dea087d015dea0adf560152'
        ]

        self.assertEqual(expected_removed_serials, removed_serials)
        self.assertEqual(expected_removed_pools, removed_pools)
        self.assertEqual([], unremoved_pools)

    def test_remove_dupli_pools_by_id(self):
        """
        Test of removing pools specified with duplicities
        (one pool id is set twice)
        """
        ent_service = EntitlementService(self.mock_cp)
        ent_service.cp.unbindByPoolId = mock.Mock()
        ent_service.entitlement_dir.list_serials_for_pool_ids = mock.Mock(return_value={
            '4028fa7a5dea087d015dea0b025003f6': ['6219625278114868779'],
            '4028fa7a5dea087d015dea0adf560152': ['3573249574655121394']
        })
        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_pools, unremoved_pools, removed_serials = ent_service.remove_entilements_by_pool_ids(
            ['4028fa7a5dea087d015dea0b025003f6',
             '4028fa7a5dea087d015dea0b025003f6',
             '4028fa7a5dea087d015dea0adf560152']
        )

        expected_removed_serials = [
            '6219625278114868779',
            '3573249574655121394'
        ]
        expected_removed_pools = [
            '4028fa7a5dea087d015dea0b025003f6',
            '4028fa7a5dea087d015dea0adf560152'
        ]

        self.assertEqual(expected_removed_serials, removed_serials)
        self.assertEqual(expected_removed_pools, removed_pools)
        self.assertEqual([], unremoved_pools)

    def test_remove_some_pools_by_id(self):
        """
        Test of removing only some pools, because one pool ID is not valid
        """
        ent_service = EntitlementService(self.mock_cp)

        def stub_unbind(uuid, pool_id):
            if pool_id == 'does_not_exist_d015dea0adf560152':
                raise connection.RestlibException(400, 'Error')

        ent_service.cp.unbindByPoolId = mock.Mock(side_effect=stub_unbind)
        ent_service.entitlement_dir.list_serials_for_pool_ids = mock.Mock(return_value={
            '4028fa7a5dea087d015dea0b025003f6': ['6219625278114868779'],
            '4028fa7a5dea087d015dea0adf560152': ['3573249574655121394']
        })
        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_pools, unremoved_pools, removed_serials = ent_service.remove_entilements_by_pool_ids(
            ['4028fa7a5dea087d015dea0b025003f6', 'does_not_exist_d015dea0adf560152']
        )

        expected_removed_serials = ['6219625278114868779']
        expected_removed_pools = ['4028fa7a5dea087d015dea0b025003f6']
        expected_unremoved_pools = ['does_not_exist_d015dea0adf560152']

        self.assertEqual(expected_removed_serials, removed_serials)
        self.assertEqual(expected_removed_pools, removed_pools)
        self.assertEqual(expected_unremoved_pools, unremoved_pools)

    def test_remove_all_pools_by_serial(self):
        """
        Test of removing all pools by serial numbers
        """
        ent_service = EntitlementService(self.mock_cp)
        ent_service.cp.unbindBySerial = mock.Mock()

        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_serial, unremoved_serials = ent_service.remove_entitlements_by_serials(
            ['6219625278114868779', '3573249574655121394']
        )

        expected_removed_serials = ['6219625278114868779', '3573249574655121394']

        self.assertEqual(expected_removed_serials, removed_serial)
        self.assertEqual([], unremoved_serials)

    def test_remove_dupli_pools_by_serial(self):
        """
        Test of removing pools specified with duplicities
        (one serial number is set twice)
        """
        ent_service = EntitlementService(self.mock_cp)
        ent_service.cp.unbindBySerial = mock.Mock()

        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_serial, unremoved_serials = ent_service.remove_entitlements_by_serials(
            ['6219625278114868779',
             '6219625278114868779',
             '3573249574655121394']
        )

        expected_removed_serials = ['6219625278114868779', '3573249574655121394']

        self.assertEqual(expected_removed_serials, removed_serial)
        self.assertEqual([], unremoved_serials)

    def test_remove_some_pools_by_serial(self):
        """
        Test of removing some of pools by serial numbers, because one serial
        number is not valid.
        """
        ent_service = EntitlementService(self.mock_cp)

        def stub_unbind(uuid, serial):
            if serial == 'does_not_exist_1394':
                raise connection.RestlibException(400, 'Error')

        ent_service.cp.unbindBySerial = mock.Mock(side_effect=stub_unbind)

        ent_service.entcertlib = mock.Mock().return_value
        ent_service.entcertlib.update = mock.Mock()

        removed_serial, unremoved_serials = ent_service.remove_entitlements_by_serials(
            ['6219625278114868779',
             'does_not_exist_1394']
        )

        expected_removed_serials = ['6219625278114868779']
        expected_unremoved_serials = ['does_not_exist_1394']

        self.assertEqual(expected_removed_serials, removed_serial)
        self.assertEqual(expected_unremoved_serials, unremoved_serials)

    def test_parse_valid_date(self):
        """
        Test parsing valid date
        """
        on_date = datetime.date.today().strftime('%Y-%m-%d')
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
        on_date = yesterday.strftime('%Y-%m-%d')
        ent_service = EntitlementService(self.mock_cp)
        self.assertRaises(ValueError, ent_service.parse_date, on_date)


class TestEntitlementDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementDBusObject, self).setUp()
        self.proxy = self.proxy_for(EntitlementDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.ENTITLEMENT_INTERFACE)

        entitlement_patcher = mock.patch('rhsmlib.dbus.objects.entitlement.EntitlementService', autospec=True)
        self.mock_entitlement = entitlement_patcher.start().return_value
        self.addCleanup(entitlement_patcher.stop)
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection").return_value
        self.mock_sorter_class = mock.Mock(spec=CertSorter, name="CertSorter")
        self.mock_ent_dir = mock.Mock(spec=EntitlementDirectory, name="EntitlementDirectory").return_value

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CERT_SORTER:
            # This sleight of hand is needed because we want to check the arguments given
            # when the cert sorter is instantiated.
            instance = self.mock_sorter_class(*args[1:])
            self.mock_sorter_class.return_value = instance
            return instance
        elif args[0] == inj.ENT_DIR:
            return self.mock_ent_dir
        elif args[0] == inj.CP_PROVIDER:
            provider = mock.Mock(spec=CPProvider, name="CPProvider")
            provider.get_consumer_auth_cp.return_value = mock.Mock(name="MockCP")
            return provider
        else:
            return None

    def dbus_objects(self):
        return [EntitlementDBusObject]

    def test_get_status(self):
        expected_status = {'status': 'Unknown', 'reasons': {}, 'valid': False}
        expected_return = json.dumps(expected_status)

        def assertions(*args):
            result = args[0]
            self.assertEqual(expected_return, result)

        self.mock_entitlement.get_status.return_value = expected_status
        dbus_method_args = ["", ""]
        self.dbus_request(assertions, self.interface.GetStatus, dbus_method_args)

    def test_remove_entitlement_by_serial(self):
        """
        Test of D-Bus object for removing entitlements by serial number.
        """
        removed_unremoved_serials = (["6219625278114868779"], [])
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(return_value=removed_unremoved_serials)
        expected_return = json.dumps(removed_unremoved_serials[0])

        def assertation(*args):
            result = args[0]
            self.assertEqual(expected_return, result)

        dbus_method_args = [["6219625278114868779"], {}, ""]
        self.dbus_request(assertation, self.interface.RemoveEntitlementsBySerials, dbus_method_args)

    def test_remove_more_entitlement_by_serials(self):
        """
        Test of D-Bus object for removing entitlements by more than one serial number.
        """
        removed_unremoved_serials = (["6219625278114868779", "3573249574655121394"], [])
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(return_value=removed_unremoved_serials)
        expected_return = json.dumps(removed_unremoved_serials[0])

        def assertation(*args):
            result = args[0]
            self.assertEqual(expected_return, result)

        dbus_method_args = [["6219625278114868779", "3573249574655121394"], {}, ""]
        self.dbus_request(assertation, self.interface.RemoveEntitlementsBySerials, dbus_method_args)

    def test_remove_entitlement_by_serial_with_wrong_serial(self):
        """
        Test of D-Bus object for removing entitlements by serial numbers.
        List of serial numbers containts also not valid number.
        """
        removed_unremoved_serials = (["6219625278114868779"], ["3573249574655121394"])
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(return_value=removed_unremoved_serials)
        expected_return = json.dumps(removed_unremoved_serials[0])

        def assertation(*args):
            result = args[0]
            self.assertEqual(expected_return, result)

        dbus_method_args = [["6219625278114868779", "3573249574655121394"], {}, ""]
        self.dbus_request(assertation, self.interface.RemoveEntitlementsBySerials, dbus_method_args)

    def test_remove_entitlement_by_pool_id(self):
        """
        Test of D-Bus object for removing entitlements by pool IDs
        """
        removed_unremoved_pools_serials = (['4028fa7a5dea087d015dea0b025003f6'], [], ['6219625278114868779'])
        self.mock_entitlement.remove_entilements_by_pool_ids = mock.Mock(return_value=removed_unremoved_pools_serials)

        expected_result = json.dumps(removed_unremoved_pools_serials[2])

        def assertation(*args):
            result = args[0]
            self.assertEqual(expected_result, result)

        dbus_method_args = [["4028fa7a5dea087d015dea0b025003f6"], {}, ""]
        self.dbus_request(assertation, self.interface.RemoveEntitlementsByPoolIds, dbus_method_args)

    def test_remove_all_entitlements(self):
        """
        Test of D-Bus object for removing all entitlements
        """
        deleted_records = {"deletedRecords": 1}
        self.mock_entitlement.remove_all_entitlements = mock.Mock(return_value=deleted_records)
        expected_result = json.dumps(deleted_records)

        def assertation(*args):
            result = args[0]
            self.assertEqual(expected_result, result)

        dbus_method_args = [{}, ""]
        self.dbus_request(assertation, self.interface.RemoveAllEntitlements, dbus_method_args)
