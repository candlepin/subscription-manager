#
# Copyright (c) 2012 Red Hat, Inc.
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

import mock


import stubs

from fixture import SubManFixture
from subscription_manager import ga
from subscription_manager.injection import require, provide, IDENTITY

from subscription_manager.gui import preferences

CONSUMER_DATA = {'autoheal': True,
                 'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'}}


def getConsumerData(self):
    return CONSUMER_DATA


def get_releases():
    return ["123123", "1", "2", "4", "blippy"]


class TestPreferencesDialog(SubManFixture):
    _getConsumerData = None

    def setUp(self):
        super(TestPreferencesDialog, self).setUp()
        # FIXME: this is c&p and could be in a fixture sub class
        #        that  does the same things StubConsumer does now
        self.id_mock = mock.Mock()
        self.id_mock.name = "John Q Consumer"
        self.id_mock.uuid = "not_actually_a_uuid"
        self.id_mock.exists_and_valid = mock.Mock(return_value=True)
        provide(IDENTITY, self.id_mock)

    @mock.patch.object(stubs.StubUEP, 'updateConsumer')
    def testAutohealChanged(self, MockUep):
        self._getPrefDialog()
        self.preferences_dialog.show()
        identity = require(IDENTITY)
        event = ga.Gdk.Event(ga.Gdk.EventType.BUTTON_PRESS)

        self.preferences_dialog.autoheal_event.emit("button-press-event", event)
        MockUep.assert_called_with(identity.uuid, autoheal=False)

        self.preferences_dialog.autoheal_event.emit("button-press-event", event)
        MockUep.assert_called_with(identity.uuid, autoheal=True)

        self.preferences_dialog.autoheal_checkbox.set_active(0)
        MockUep.assert_called_with(identity.uuid, autoheal=False)

        self.preferences_dialog.autoheal_checkbox.set_active(1)
        MockUep.assert_called_with(identity.uuid, autoheal=True)

    def _getPrefDialog(self):
        stub_backend = stubs.StubBackend()
        stub_backend.cp_provider.consumer_auth_cp.setConsumer(CONSUMER_DATA)

        stub_backend.product_dir = stubs.StubCertificateDirectory([stubs.StubProductCertificate(stubs.StubProduct("rhel-6"))])
        stub_backend.entitlement_dir = stubs.StubEntitlementDirectory([stubs.StubEntitlementCertificate(stubs.StubProduct("rhel-6"))])

        self.preferences_dialog = preferences.PreferencesDialog(backend=stub_backend,
                                                                parent=None)
        self.preferences_dialog.release_backend.facts = stubs.StubFacts()
        self.preferences_dialog.release_backend.get_releases = get_releases
        self.preferences_dialog.async_updater = stubs.StubAsyncUpdater(self.preferences_dialog)

    def testShowPreferencesDialog(self):
        self._getPrefDialog()
        self.preferences_dialog.show()

    def testShowPreferencesDialogNoSLA(self):
        def getConsumerNoSla(self):
            return {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                    'owner': {'key': 'admin'}}
        self._getConsumerData = getConsumerNoSla
        self._getPrefDialog()
        self.preferences_dialog.show()

    def testShowPreferencesDialogNoRelease(self):
        def getConsumerNoRelease(self):
            return {'serviceLevel': "Pro Turbo HD Plus Ultra",
                    'owner': {'key': 'admin'}}
        self._getConsumerData = getConsumerNoRelease
        self._getPrefDialog()
        self.preferences_dialog.show()

    def testShowPreferencesDialogNoConsumer(self):
        id_mock = mock.Mock()
        id_mock.name = "John Q Consumer"
        id_mock.uuid = None
        id_mock.exists_and_valid = mock.Mock(return_value=True)
        provide(IDENTITY, id_mock)

        self._getPrefDialog()
        self.preferences_dialog.show()

    @mock.patch.object(stubs.StubUEP, 'updateConsumer')
    def testSlaChanged(self, MockUep):
        self._getPrefDialog()

        self.preferences_dialog.show()
        self.preferences_dialog.sla_combobox.set_active(1)
        # FIXME:
        # slightly odd, we inject self.id_mock as the identity, but
        # something in mock doesn't like to equate that to the injected
        # one, so we just get a ref to the injected one and verify
        identity = require(IDENTITY)
        MockUep.assert_called_with(identity.uuid, service_level="Pro")

    def testSlaUnset(self):
        self._getPrefDialog()
        self.preferences_dialog.show()
        self.preferences_dialog.sla_combobox.set_active(0)
        tree_iter = self.preferences_dialog.sla_combobox.get_active_iter()
        display_text = self.preferences_dialog.sla_model.get_value(tree_iter, 0)
        self.assertEquals("Not Set", display_text)

    @mock.patch.object(stubs.StubUEP, 'updateConsumer')
    def testReleaseChanged(self, MockUep):
        self._getPrefDialog()

        self.preferences_dialog.release_backend.get_releases = get_releases
        self.preferences_dialog.show()
        self.preferences_dialog.release_combobox.set_active(5)
        identity = require(IDENTITY)
        MockUep.assert_called_with(identity.uuid, release="blippy")

    def testReleaseUnset(self):
        self._getPrefDialog()

        self.preferences_dialog.release_backend.get_releases = get_releases
        self.preferences_dialog.show()
        self.preferences_dialog.release_combobox.set_active(0)
        tree_iter = self.preferences_dialog.release_combobox.get_active_iter()
        display_text = self.preferences_dialog.release_model.get_value(tree_iter, 0)
        self.assertEquals("Not Set", display_text)
