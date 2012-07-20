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

import unittest

import stubs

from subscription_manager.gui import preferences


class StubConsumer:
    def __init__(self):
        self.uuid = "not_actually_a_uuid"

    def reload(self):
        pass

CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'}}


def getConsumerData(self):
    return CONSUMER_DATA


class StubConsumerNone:
    def __init__(self):
        self.uuid = None


def get_releases():
    return ["123123", "1", "2", "4", "blippy"]


class TestPreferencesDialog(unittest.TestCase):
    _getConsumerData = None
    _getConsumer = None

    def _getPrefDialog(self):
        stub_backend = stubs.StubBackend()
        stub_backend.uep.getConsumer = getConsumerData
        if self._getConsumerData:
            stub_backend.uep.getConsumer = self._getConsumerData

        self.consumer = StubConsumer()
        if self._getConsumer:
            self.consumer = self._getConsumer()

        stub_backend.product_dir = stubs.StubCertificateDirectory([stubs.StubProductCertificate(stubs.StubProduct("rhel-6"))])
        stub_backend.entitlement_dir = stubs.StubEntitlementDirectory([stubs.StubEntitlementCertificate(stubs.StubProduct("rhel-6"))])

        self.preferences_dialog = preferences.PreferencesDialog(backend=stub_backend,
                                                                consumer=self.consumer,
                                                                parent=None)
        self.preferences_dialog.release_backend.facts = stubs.StubFacts()
        self.preferences_dialog.release_backend.get_releases = get_releases

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
        def getConsumerNoConsumer():
            return StubConsumerNone()
        self._getConsumer = getConsumerNoConsumer
        self._getPrefDialog()
        self.preferences_dialog.show()

    def testSlaChanged(self):
        self._getPrefDialog()
        # monkey patch update consumer so we can see if it got triggered
        # and if so, that the right value got set, in this case, the
        # first service level "Pro"

        def updateConsumer(consumer, service_level=None, release=None):
            self.assertEquals(service_level, "Pro")

        self.preferences_dialog.show()
        self.preferences_dialog.backend.uep.updateConsumer = updateConsumer
        self.preferences_dialog.sla_combobox.set_active(1)

    def testReleaseChanged(self):
        self._getPrefDialog()

        def updateConsumer(consumer, service_level=None, release=None):
            # from monkeypatched getConsumer
            self.assertEquals(release, "123123")

        self.preferences_dialog.release_backend.get_releases = get_releases
        self.preferences_dialog.show()
        self.preferences_dialog.backend.uep.updateConsumer = updateConsumer
        self.preferences_dialog.release_combobox.set_active(1)
