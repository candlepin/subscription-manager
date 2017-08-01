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
import json
import mock
import six

from test.rhsmlib_test.base import DBusObjectTest, InjectionMockingTest

from subscription_manager import injection as inj
from subscription_manager.identity import Identity
from subscription_manager.plugins import PluginManager
from subscription_manager.cp_provider import CPProvider
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.reasons import Reasons
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.facts import Facts

from rhsm import connection

from rhsmlib.dbus.objects import EntitlementDBusObject
from rhsmlib.dbus import constants
from rhsmlib.services import entitlement
from subscription_manager.cache import PoolTypeCache, ProfileManager
from rhsmlib.services.entitlement.pool_stash import PoolStash

class TestEntitlementService(InjectionMockingTest):
    def setUp(self):
        super(TestEntitlementService, self).setUp()
        self.mock_identity = mock.Mock(spec=Identity, name="Identity")

        self.mock_cp_provider = mock.Mock(spec=CPProvider,name="CPProvider")
        self.mock_cp = mock.Mock(spec=connection.UEPConnection, name="UEPConnection")

        self.mock_pm = mock.Mock(spec=PluginManager, name="PluginManager")

        self.mock_cert_sorter = mock.Mock(spec=CertSorter, name="CertSorter")
        self.mock_cert_sorter.reasons =  mock.Mock(spec=Reasons, name="Reasons")
        self.mock_cert_sorter.reasons.get_name_message_map.return_value = {}
        self.mock_cert_sorter.get_system_status.return_value="System Status"

        self.pooltype_cache = mock.Mock(spec=PoolTypeCache, name="PoolTypeCache")
        self.pooltype_cache.get.return_value="some subscription type"
        self.ent_dir = mock.Mock(spec=EntitlementDirectory, name="EntitlementDirectory")
        self.facts = mock.Mock(spec=Facts, name="Facts")
        self.profile_manager = mock.Mock(spec=ProfileManager, name="ProfileManager")
        self.pool_stash = mock.Mock(spec=PoolStash, name="PoolStash")

    def injection_definitions(self, *args, **kwargs):
        result = {
            inj.IDENTITY: self.mock_identity,
            inj.PLUGIN_MANAGER: self.mock_pm,
            inj.CERT_SORTER: self.mock_cert_sorter,
            inj.CP_PROVIDER: self.mock_cp_provider,
            inj.POOLTYPE_CACHE: self.pooltype_cache,
            inj.ENT_DIR: self.ent_dir,
            inj.FACTS: self.facts,
            inj.PROFILE_MANAGER: self.profile_manager,
            inj.POOL_STASH: self.pool_stash,
        }.get(args[0]) # None when a key does not exist
        #print("injection_definition:", args, " result: ", result)
        return result

    def test_get_status(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "some-uuid"
        result = entitlement.EntitlementService().get_status()
        self.assertEqual(
            {'status': 0,
             'reasons': {},
             'overall_status': "System Status"},
            result)

    def test_get_status_for_invalid_system(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "some-uuid"
        reasons = json.load(open("test/rhsmlib_test/data/reasons.json"))
        self.mock_cert_sorter.reasons.get_name_message_map.return_value = reasons
        self.mock_cert_sorter.is_valid.return_value=False
        result = entitlement.EntitlementService().get_status()
        self.assertEqual(
            {'status': 1,
             'reasons': reasons,
             'overall_status': "System Status"},
            result)

    def test_get_pools_available(self):
        self.mock_identity.is_valid.return_value = True
        self.mock_identity.uuid = "some-uuid"
        self.pool_stash.get_filtered_pools_list.return_value=\
            json.load(open("test/rhsmlib_test/data/filtered-pools.json"))
        result=entitlement.EntitlementService().get_pools()
        self.assertEqual(json.load(open("test/rhsmlib_test/data/entitlement-get-pools-available.json")),
                         result)
