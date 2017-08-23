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

    def injection_definitions(self, *args, **kwargs):
        if args[0] == inj.IDENTITY:
            return self.mock_identity
        elif args[0] == inj.CERT_SORTER:
            # This sleight of hand is needed because we want to check the arguments given
            # when the cert sorter is instantiated.
            instance = self.mock_sorter_class(*args[1:])
            self.mock_sorter_class.return_value = instance
            return instance
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


class TestEntitlementDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementDBusObject, self).setUp()
        self.proxy = self.proxy_for(EntitlementDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.ENTITLEMENT_INTERFACE)

        entitlement_patcher = mock.patch('rhsmlib.dbus.objects.entitlement.EntitlementService', autospec=True)
        self.mock_entitlement = entitlement_patcher.start().return_value
        self.addCleanup(entitlement_patcher.stop)

    def injection_definitions(self, *args, **kwargs):
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
        self.dbus_request(assertions, self.interface.GetStatus, [""])
