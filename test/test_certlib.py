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
from mock import Mock, patch
from datetime import timedelta, datetime

from stubs import StubEntitlementCertificate, StubProduct, StubEntitlementDirectory, \
            StubConsumerIdentity

from subscription_manager.certlib import UpdateAction, UpdateReport
from subscription_manager.certdirectory import Writer


class TestingUpdateAction(UpdateAction):

    def __init__(self, mock_uep, mock_entdir):
        UpdateAction.__init__(self, uep=mock_uep, entdir=mock_entdir)

    def build(self, cert):
        '''
          Override so that we can specify stubs as certificates.
        '''
        return (Mock(), cert)

    def _getConsumerId(self):
        return StubConsumerIdentity("ConsumerKey", "ConsumerCert")


class UpdateActionTests(unittest.TestCase):

    def setUp(self):
        pass

    @patch.object(Writer, "write")
    def test_expired_are_ignored_when_installing_certs(self, write_mock):
        valid_ent = StubEntitlementCertificate(StubProduct("PValid"))
        expired_ent = StubEntitlementCertificate(StubProduct("PExpired"),
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now() - timedelta(days=10))

        cp_certificates = [valid_ent, expired_ent]

        mock_uep = Mock()
        mock_uep.getCertificates.return_value = cp_certificates  # Passed into build(cert)

        update_action = TestingUpdateAction(mock_uep,
                                            StubEntitlementDirectory([]))
        report = UpdateReport()
        report.expected.append(valid_ent.serial)
        report.expected.append(expired_ent.serial)

        exceptions = update_action.install([valid_ent.serial, expired_ent.serial], report)
        self.assertEqual(0, len(exceptions), "No exceptions should have been thrown")
        self.assertTrue(valid_ent in report.added)
        self.assertTrue(valid_ent.serial in report.expected)
        self.assertFalse(expired_ent.serial in report.expected)
