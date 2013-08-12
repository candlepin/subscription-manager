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

from mock import Mock, patch
from datetime import timedelta, datetime

from stubs import StubEntitlementCertificate, StubProduct, StubEntitlementDirectory, \
            StubConsumerIdentity

from fixture import SubManFixture

from subscription_manager.certdirectory import Writer
from subscription_manager import certlib


class TestingUpdateAction(certlib.UpdateAction):

    def __init__(self, mock_uep, mock_entdir):
        certlib.UpdateAction.__init__(self, uep=mock_uep, entdir=mock_entdir)

    def _get_consumer_id(self):
        return StubConsumerIdentity("ConsumerKey", "ConsumerCert")


class UpdateActionTests(SubManFixture):

    @patch("subscription_manager.certlib.EntitlementCertBundleInstaller.build_cert")
    @patch.object(Writer, "write")
    def test_expired_are_not_ignored_when_installing_certs(self, write_mock, build_cert_mock):
        valid_ent = StubEntitlementCertificate(StubProduct("PValid"))
        expired_ent = StubEntitlementCertificate(StubProduct("PExpired"),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=10))

        cp_certificates = [valid_ent, expired_ent]
        # get certificates actually returns cert bundles
        cp_bundles = [{'key': Mock(), 'cert': x} for x in cp_certificates]

        # so we dont try to build actual x509 objects from stub certs
        def mock_build_cert(bundle):
            return (bundle['key'], bundle['cert'])

        build_cert_mock.side_effect = mock_build_cert

        mock_uep = Mock()
        mock_uep.getCertificates.return_value = cp_bundles  # Passed into build_cert(bundle)

        update_action = TestingUpdateAction(mock_uep,
                                            StubEntitlementDirectory([]))
        report = certlib.UpdateReport()
        report.expected.append(valid_ent.serial)
        report.expected.append(expired_ent.serial)

        update_action.install([valid_ent.serial, expired_ent.serial], report)
        self.assertEqual(0, len(update_action.exceptions), "No exceptions should have been thrown")
        self.assertTrue(valid_ent in report.added)
        self.assertTrue(valid_ent.serial in report.expected)
        self.assertTrue(expired_ent.serial in report.expected)

    def test_delete(self):
        ent = StubEntitlementCertificate(StubProduct("Prod"))
        ent.delete = Mock(side_effect=OSError("Cert has already been deleted"))
        mock_uep = Mock()
        mock_uep.getCertificates = Mock(return_value=[])
        mock_uep.getCertificateSerials = Mock(return_value=[])
        update_action = TestingUpdateAction(mock_uep, StubEntitlementDirectory([ent]))
        try:
            updates, exceptions = update_action.perform()
        except OSError:
            self.fail("operation failed when certificate wasn't deleted")
        self.assertEquals(0, updates)
        self.assertEquals([], exceptions)
