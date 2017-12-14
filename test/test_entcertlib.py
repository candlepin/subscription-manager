# -*- coding: utf-8 -*-#

from __future__ import print_function, division, absolute_import

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
import six

from .stubs import StubEntitlementCertificate, StubProduct, StubEntitlementDirectory

from . import fixture

from subscription_manager.certdirectory import Writer
from subscription_manager import entcertlib
from subscription_manager import injection as inj


class TestDisconnected(fixture.SubManFixture):
    def test_repr(self):
        # no err_msg, so empty repr
        discon = entcertlib.Disconnected()
        err_msg = "%s" % discon
        self.assertEqual("", err_msg)


class TestingUpdateAction(entcertlib.EntCertUpdateAction):

    def __init__(self):
        entcertlib.EntCertUpdateAction.__init__(self)


class TestEntCertUpdateReport(fixture.SubManFixture):
    def test(self):
        r = entcertlib.EntCertUpdateReport()
        r.expected = u'12312'
        r.valid = [u'2342∰']
        r.added.append(self._stub_cert())
        r.rogue.append(self._stub_cert())

        # an UnicodeError will fail the tests
        report_str = six.text_type(r)
        '%s' % report_str

        with fixture.locale_context('de_DE.utf8'):
            report_str = six.text_type(r)
            '%s' % r

    def _stub_cert(self):
        stub_ent_cert = StubEntitlementCertificate(StubProduct(u"ஒரு அற்புதமான இயங்கு"))
        stub_ent_cert.order.name = u'一些秩序'
        return stub_ent_cert


class UpdateActionTests(fixture.SubManFixture):

    @patch("subscription_manager.entcertlib.EntitlementCertBundleInstaller.build_cert")
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
        mock_uep.getCertificateSerials.return_value = [x.serial for x in cp_certificates]
        mock_uep.getCertificates.return_value = cp_bundles  # Passed into build_cert(bundle)
        self.set_consumer_auth_cp(mock_uep)

        stub_ent_dir = StubEntitlementDirectory([])
        inj.provide(inj.ENT_DIR, stub_ent_dir)
        update_action = TestingUpdateAction()
        # we skip getting the expected serials, where this is normally
        # populated
        update_action.report.expected.append(valid_ent.serial)
        update_action.report.expected.append(expired_ent.serial)

        update_action.install([valid_ent.serial, expired_ent.serial])
        update_report = update_action.report

        self.assertEqual(0, len(update_report.exceptions()), "No exceptions should have been thrown")
        self.assertTrue(valid_ent in update_report.added)
        self.assertTrue(valid_ent.serial in update_report.expected)
        self.assertTrue(expired_ent.serial in update_report.expected)

    def test_delete(self):
        ent = StubEntitlementCertificate(StubProduct("Prod"))
        ent.delete = Mock(side_effect=OSError("Cert has already been deleted"))
        mock_uep = Mock()
        mock_uep.getCertificates = Mock(return_value=[])
        mock_uep.getCertificateSerials = Mock(return_value=[])

        self.set_consumer_auth_cp(mock_uep)
        stub_ent_dir = StubEntitlementDirectory([ent])
        inj.provide(inj.ENT_DIR, stub_ent_dir)

        # use the injected mock uep
        update_action = TestingUpdateAction()

        try:
            update_report = update_action.perform()
        except OSError:
            self.fail("operation failed when certificate wasn't deleted")
        self.assertEqual(0, update_report.updates())

        exceptions = update_action.report.exceptions()
        self.assertEqual([], exceptions)
