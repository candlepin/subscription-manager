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

from test.rhsmlib_test.base import InjectionMockingTest, DBusObjectTest

from subscription_manager import injection as inj
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.cp_provider import CPProvider

from rhsm import connection

from rhsmlib.dbus import constants
from rhsmlib.dbus.objects import EntitlementDBusObject

from test import subman_marker_dbus


@subman_marker_dbus
class TestEntitlementDBusObject(DBusObjectTest, InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementDBusObject, self).setUp()
        self.proxy = self.proxy_for(EntitlementDBusObject.default_dbus_path)
        self.interface = dbus.Interface(self.proxy, constants.ENTITLEMENT_INTERFACE)

        entitlement_patcher = mock.patch("rhsmlib.dbus.objects.entitlement.EntitlementService", autospec=True)
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
        expected_status = {"status": "Unknown", "reasons": {}, "valid": False}
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
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(
            return_value=removed_unremoved_serials
        )
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
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(
            return_value=removed_unremoved_serials
        )
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
        self.mock_entitlement.remove_entitlements_by_serials = mock.Mock(
            return_value=removed_unremoved_serials
        )
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
        removed_unremoved_pools_serials = (["4028fa7a5dea087d015dea0b025003f6"], [], ["6219625278114868779"])
        self.mock_entitlement.remove_entilements_by_pool_ids = mock.Mock(
            return_value=removed_unremoved_pools_serials
        )

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
