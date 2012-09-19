
# Copyright (c) 2010 Red Hat, Inc.
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
import simplejson as json
from datetime import datetime, timedelta

import mock
import stubs

from subscription_manager import certmgr
from subscription_manager import certlib
from subscription_manager import repolib
from subscription_manager import facts
from subscription_manager import hwprobe

from rhsm.profile import  RPMProfile
from rhsm.connection import GoneException


CONSUMER_DATA = {'releaseVer': {'id': 1, 'releaseVer': '123123'},
                 'serviceLevel': "Pro Turbo HD Plus Ultra",
                 'owner': {'key': 'admin'},
                 'autoheal': 1,
                 'idCert': {'serial': {'serial': 3787455826750723380}}}


def mock_pkg_profile(packages):
    dict_list = []
    for pkg in packages:
        dict_list.append(pkg.to_dict())

    mock_file = mock.Mock()
    mock_file.read = mock.Mock(return_value=json.dumps(dict_list))

    mock_profile = RPMProfile(from_file=mock_file)
    return mock_profile


class ExceptionalException(Exception):
    pass


class TestCertmgr(unittest.TestCase):

    # on python 2.6+ we could set class decorators, but that doesn't
    # work on python2.4, so this...
    # http://www.voidspace.org.uk/python/mock/patch.html#patch-methods-start-and-stop
    def setUp(self):
        # we have to have a reference to the patchers
        self.patcher2 = mock.patch.object(certlib.UpdateAction, '_getConsumerId')
        self.certlib_updateaction_getconsumerid = self.patcher2.start()

        self.patcher3 = mock.patch.object(repolib.UpdateAction, 'perform')
        self.repolib_updateaction_perform = self.patcher3.start()

        self.patcher4 = mock.patch('subscription_manager.factlib.ConsumerIdentity')
        self.factlib_consumeridentity = self.patcher4.start()

        self.patcher5 = mock.patch('subscription_manager.certlib.ConsumerIdentity')
        self.certlib_consumeridentity = self.patcher5.start()

        self.patcher6 = mock.patch('subscription_manager.managerlib.persist_consumer_cert')
        self.managerlib_persist_consumer_cert = self.patcher6.start()

        self.patcher7 = mock.patch.object(facts.Facts, '_get_validity_facts')
        self.facts_getvalidityfacts = self.patcher7.start()
        self.facts_getvalidityfacts.return_value = []

        self.patcher8 = mock.patch.object(facts.Facts, 'get_last_update')
        self.facts_getlastupdate = self.patcher8.start()
        self.facts_getlastupdate.return_value = None

        self.facts_load_hw_patcher = mock.patch.object(facts.Facts, '_load_hw_facts')
        self.facts_load_hw_mock = self.facts_load_hw_patcher.start()
        self.facts_load_hw_mock.return_value = {}

        self.facts_load_custom_patcher = mock.patch.object(facts.Facts, '_load_custom_facts')
        self.facts_load_custom_mock = self.facts_load_custom_patcher.start()
        self.facts_load_custom_mock.return_value = {}

        # we end up import EntitlementDirectory differently lots...
        self.patcher9 = mock.patch('subscription_manager.certlib.EntitlementDirectory')
        self.certlib_entdir = self.patcher9.start()

        # mock out all hardware fetching... we may need to fake socket counts
        self.hwprobe_getall_patcher = mock.patch.object(hwprobe.Hardware, 'getAll')
        self.hwprobe_getall_mock = self.hwprobe_getall_patcher.start()
        self.hwprobe_getall_mock.return_value = {}

        self.patchcer_certdir_entdir = \
            mock.patch('subscription_manager.certdirectory.EntitlementDirectory')
        self.certdir_entdir = self.patchcer_certdir_entdir.start()

        self.patcher_repolib_entdir = \
            mock.patch("subscription_manager.repolib.EntitlementDirectory")
        self.repolib_entdir = self.patcher_repolib_entdir.start()

        self.patcher_certlib_writer = mock.patch("subscription_manager.certlib.Writer")
        self.certlib_writer = self.patcher_certlib_writer.start()

        self.patcher_certlib_action_syslogreport = mock.patch.object(certlib.UpdateAction, 'syslogResults')
        self.update_action_syslog_mock = self.patcher_certlib_action_syslogreport.start()

        # some stub certs
        stub_product = stubs.StubProduct('stub_product')
        self.stub_ent1 = stubs.StubEntitlementCertificate(stub_product)
        self.stub_ent2 = stubs.StubEntitlementCertificate(stub_product)
        self.stub_ent_expires_tomorrow = \
            stubs.StubEntitlementCertificate(stub_product,
                                             end_date=datetime.now() + timedelta(days=1))

        self.stub_ent_expires_tomorrow_entdir = \
            stubs.StubEntitlementDirectory([self.stub_ent_expires_tomorrow])

        self.local_ent_certs = [self.stub_ent1, self.stub_ent2]
        self.stub_entitled_proddir = \
            stubs.StubProductDirectory([stubs.StubProductCertificate(stub_product)])

        # local entitlement dir
        self.stub_entdir = stubs.StubEntitlementDirectory(self.local_ent_certs)
        self.certdir_entdir.return_value = self.stub_entdir
        self.certlib_entdir.return_value = self.stub_entdir
        self.repolib_entdir.return_value = self.stub_entdir

        self.mock_uep = mock.Mock()
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[{'serial': self.stub_ent1.serial},
                                                                      {'serial': self.stub_ent2.serial}])
        self.mock_uep.getConsumer = mock.Mock(return_value=CONSUMER_DATA)

        self.stub_unentitled_prod = stubs.StubProduct('not_entitled_stub_product')
        self.stub_unentitled_prod_cert = stubs.StubProductCertificate(self.stub_unentitled_prod)
        self.stub_unentitled_proddir = stubs.StubProductDirectory([self.stub_unentitled_prod_cert])

        self.certdir_entdir = self.patchcer_certdir_entdir.start()
        self.certlib_updateaction_getconsumerid.return_value = "234234"

        self.repolib_updateaction_perform.return_value = 0

        self.factlib_consumeridentity.read.return_value = stubs.StubConsumerIdentity("sdfsdf", "sdfsdf")
        self.certlib_consumeridentity.read.return_value = stubs.StubConsumerIdentity("sdfsdf", "sdfsdf")

    def tearDown(self):
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()
        self.patcher5.stop()
        self.patcher6.stop()
        self.patcher7.stop()
        self.patcher8.stop()
        self.patcher9.stop()

        self.facts_load_hw_patcher.stop()
        self.facts_load_custom_patcher.stop()

        self.patchcer_certdir_entdir.stop()
        self.patcher_repolib_entdir.stop()
        self.patcher_certlib_writer.stop()

        self.hwprobe_getall_patcher.stop()
        self.patcher_certlib_action_syslogreport.stop()

    def test_init(self):
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

    @mock.patch('subscription_manager.certlib.log')
    def test_healing_no_heal(self, mock_log):
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep,
                                  product_dir=self.stub_entitled_proddir)
        mgr.update(autoheal=True)
        mock_log.info.assert_called_with('Auto-heal check complete.')

    def test_healing_needs_heal(self):
        # need a stub product dir with prods with no entitlements,
        # don't have to mock here since we can actually pass in a product
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep,
                                  product_dir=self.stub_unentitled_proddir)
        mgr.update(autoheal=True)
        self.assertTrue(self.mock_uep.bind.called)

    @mock.patch.object(certlib.Action, 'build')
    def test_healing_needs_heal_tomorrow(self, cert_build_mock):
        cert_build_mock.return_value = (mock.Mock(), self.stub_ent_expires_tomorrow)

        self._stub_certificate_calls([self.stub_ent_expires_tomorrow])
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep,
                                  product_dir=self.stub_entitled_proddir)
        mgr.update(autoheal=True)
        # see if we tried to update certs
        self.assertTrue(self.mock_uep.bind.called)

    @mock.patch('subscription_manager.certlib.log')
    def test_healing_trigger_exception(self, mock_log):
        # this setup causes an exception in certSorter, which HealingLib
        # needs to be able to handle
        # StubProductDirectory is incorrectly created with a single product cert here,
        # where it wants a list, causing a TypeError
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep,
                                  product_dir=stubs.StubProductDirectory(self.stub_unentitled_prod))
        mgr.update(autoheal=True)
        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], TypeError):
                return
        self.fail("Did not see TypeError in the logged exceptions")

    # see bz #852706
    @mock.patch.object(certlib.CertLib, 'update')
    def test_gone_exception(self, mock_update):
        mock_update.side_effect = GoneException(410, "bye bye", " 234234")
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        self.assertRaises(GoneException, mgr.update)

    # see bz #852706, except this time for idcertlib
    @mock.patch.object(certlib.IdentityCertLib, 'update')
    def test_idcertlib_gone_exception(self, mock_update):
        mock_update.side_effect = GoneException(410, "bye bye", " 234234")
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        self.assertRaises(GoneException, mgr.update)

        # just verify the certlib update worked
        report = self.update_action_syslog_mock.call_args[0][0]
        self.assertTrue(self.stub_ent1.serial in report.valid)

    @mock.patch.object(certlib.CertLib, 'update')
    @mock.patch('subscription_manager.certmgr.log')
    def test_certlib_update_exception(self, mock_log, mock_update):
        mock_update.side_effect = ExceptionalException()
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")

    @mock.patch.object(certlib.IdentityCertLib, 'update')
    @mock.patch('subscription_manager.certmgr.log')
    def test_idcertlib_update_exception(self, mock_log, mock_update):
        mock_update.side_effect = ExceptionalException()
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")

    def _stub_certificate_calls(self, stub_ents=[]):
        stub_entdir = stubs.StubEntitlementDirectory(stub_ents)

        self.certdir_entdir.return_value = stub_entdir
        self.certlib_entdir.return_value = stub_entdir
        self.repolib_entdir.return_value = stub_entdir

        # don't need to build real pem's, we mock out the writer anyway
        # so this just create a list of mock keys and stub ent certs
        stub_certificate_list = []
        for stub_cert in self.local_ent_certs:
            stub_certificate_list.append((mock.Mock(), stub_cert))

        # return a list of stub ent certs, could be new stubs, but
        # we already have created that
        self.mock_uep.getCertificates.return_value = stub_certificate_list

    # we need to simulate the client missing some ent certs
    @mock.patch.object(certlib.Action, 'build')
    def test_missing(self, cert_build_mock):
        # mock no certs client side
        self._stub_certificate_calls()

        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        report = self.update_action_syslog_mock.call_args[0][0]
        self.assertTrue(self.stub_ent1 in report.added)

    def test_rogue(self):
        # to mock "rogue" certs we need some local, that are not known to the
        # server so getCertificateSerials to return nothing
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        report = self.update_action_syslog_mock.call_args[0][0]

        # our local ent certs should be showing up as rogue
        self.assertTrue(self.local_ent_certs[0] in report.rogue)
        self.assertTrue(self.local_ent_certs[1] in report.rogue)

    @mock.patch.object(certlib.Action, 'build')
    def test_expired(self, cert_build_mock):
        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)

        # this makes the stub_entdir report all ents as being expired
        # so we fetch new ones
        self.stub_entdir.expired = True

        # we don't want to find replacements, so this forces a delete
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        # the expired certs should be delete/rogue and expired
        report = self.update_action_syslog_mock.call_args[0][0]
        self.assertTrue(self.stub_ent1 in report.rogue)
        self.assertTrue(self.stub_ent1 in report.expired)

    @mock.patch.object(certlib.Action, 'build')
    def test_expired_with_syslog_report(self, cert_build_mock):
        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)

        # unpatch the syslog capturing so we cover the real one
        self.patcher_certlib_action_syslogreport.stop()

        # this makes the stub_entdir report all ents as being expired
        # so we fetch new ones
        self.stub_entdir.expired = True

        # we don't want to find replacements, so this forces a delete
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        # repatch syslogReport
        self.patcher_certlib_action_syslogreport = mock.patch.object(certlib.UpdateAction, 'syslogResults')
        self.update_action_syslog_mock = self.patcher_certlib_action_syslogreport.start()

    @mock.patch.object(certlib.Action, 'build')
    def test_expired_show_update_report(self, cert_build_mock):
        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)

        # this makes the stub_entdir report all ents as being expired
        # so we fetch new ones
        self.stub_entdir.expired = True

        # we don't want to find replacements, so this forces a delete
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        mgr.update()

        # the expired certs should be delete/rogue and expired
        report = self.update_action_syslog_mock.call_args[0][0]

        # some of this is more certlib testing, but while we have
        # everything mocked up...

        # UpdateReport.write
        line_array = []
        report.write(line_array, 'this is a title', self.local_ent_certs)
        self.assertTrue(len(line_array) > 0)

        report_str = '%s' % report
        self.assertTrue(len(report_str) > 0)

        self.assertTrue(self.stub_ent1 in report.rogue)
        self.assertTrue(self.stub_ent1 in report.expired)

    @mock.patch.object(certlib.Action, 'build')
    @mock.patch('subscription_manager.certlib.log')
    def test_exception_on_cert_write(self, mock_log, mock_cert_build):
        # this is basically the same as test_missing, expect we throw
        # an exception attempting to write the certs out
        self._stub_certificate_calls()

        mock_cert_build.side_effect = ExceptionalException()
        mgr = certmgr.CertManager(lock=stubs.MockActionLock(), uep=self.mock_uep)
        # we should fail on the certlib.update, but keep going...
        # and handle it well.
        mgr.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")
