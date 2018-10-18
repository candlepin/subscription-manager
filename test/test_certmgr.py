from __future__ import print_function, division, absolute_import

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

from datetime import datetime, timedelta

import mock
from . import stubs

from rhsm import ourjson as json
from subscription_manager import action_client
from subscription_manager import content_action_client
from subscription_manager import entcertlib
from subscription_manager import identitycertlib
from subscription_manager import repolib
from subscription_manager import injection
import subscription_manager.injection as inj

from rhsmlib.facts import hwprobe

from rhsm.profile import RPMProfile
from rhsm.connection import GoneException
from rhsm.certificate import GMT

from .fixture import SubManFixture, set_up_mock_sp_store


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


class ActionClientTestBase(SubManFixture):

    # on python 2.6+ we could set class decorators, but that doesn't
    # work on python2.4, so this...
    # http://www.voidspace.org.uk/python/mock/patch.html#patch-methods-start-and-stop
    def setUp(self):
        SubManFixture.setUp(self)
        # we have to have a reference to the patchers
        #self.patcher2 = mock.patch.object(entcertlib.EntCertUpdateAction, '_get_consumer_id')
        #self.entcertlib_updateaction_getconsumerid = self.patcher2.start()

        self.patcher3 = mock.patch.object(repolib.RepoUpdateActionCommand, 'perform')
        self.repolib_updateaction_perform = self.patcher3.start()

        self.patcher6 = mock.patch('subscription_manager.managerlib.persist_consumer_cert')
        self.managerlib_persist_consumer_cert = self.patcher6.start()

        # mock out all hardware fetching... we may need to fake socket counts
        self.hwprobe_getall_patcher = mock.patch.object(hwprobe.HardwareCollector, 'get_all')
        self.hwprobe_getall_mock = self.hwprobe_getall_patcher.start()
        self.hwprobe_getall_mock.return_value = {}

        self.patcher_entcertlib_writer = mock.patch("subscription_manager.entcertlib.Writer")
        self.entcertlib_writer = self.patcher_entcertlib_writer.start()

        self.patcher_entcertlib_action_syslogreport = mock.patch.object(entcertlib.EntCertUpdateAction, 'syslog_results')
        self.update_action_syslog_mock = self.patcher_entcertlib_action_syslogreport.start()

        # some stub certs
        stub_product = stubs.StubProduct('stub_product')
        self.stub_ent1 = stubs.StubEntitlementCertificate(stub_product)
        self.stub_ent2 = stubs.StubEntitlementCertificate(stub_product)
        self.stub_ent_expires_tomorrow = \
            stubs.StubEntitlementCertificate(stub_product,
                                             end_date=datetime.now() + timedelta(days=1))

        self.stub_ent_expires_tomorrow_ent_dir = \
            stubs.StubEntitlementDirectory([self.stub_ent_expires_tomorrow])

        self.local_ent_certs = [self.stub_ent1, self.stub_ent2]
        self.stub_entitled_proddir = \
            stubs.StubProductDirectory([stubs.StubProductCertificate(stub_product)])

        # local entitlement dir
        self.stub_ent_dir = stubs.StubEntitlementDirectory(self.local_ent_certs)
        inj.provide(inj.ENT_DIR, self.stub_ent_dir)

        self.mock_uep = mock.Mock()
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[{'serial': self.stub_ent1.serial},
                                                                        {'serial': self.stub_ent2.serial}])
        self.mock_uep.getConsumer = mock.Mock(return_value=CONSUMER_DATA)
        self.set_consumer_auth_cp(self.mock_uep)

        stub_release = {'releaseVer': '6.4'}
        self.mock_uep.getRelease = mock.Mock(return_value=stub_release)

        # we need to mock the consumers uuid with the mocked GoneExceptions
        # uuid
        self._inject_mock_valid_consumer(uuid="234234")

        self.repolib_updateaction_perform.return_value = 0

        # Setup a mock cert sorter to initiate the behaviour we want to test.
        # Must use a non-callable mock for our features dep injection
        # framework.
        self.mock_cert_sorter = mock.NonCallableMock()

        # TODO: need to provide return for "getRelease" for repolib stuff

        injection.provide(injection.CERT_SORTER, self.mock_cert_sorter)

        syspurpose_patch = mock.patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def tearDown(self):
        self.patcher3.stop()
        self.patcher6.stop()

        self.patcher_entcertlib_writer.stop()

        self.hwprobe_getall_patcher.stop()
        self.patcher_entcertlib_action_syslogreport.stop()


class TestContentActionClient(ActionClientTestBase):
    def test_init(self):
        actionclient = content_action_client.ContentActionClient()
        actionclient.update()


class TestActionClient(ActionClientTestBase):

    def test_init(self):
        actionclient = action_client.ActionClient()
        actionclient.update()

    # see bz #852706
    @mock.patch.object(entcertlib.EntCertActionInvoker, 'update')
    def test_gone_exception(self, mock_update):
        mock_update.side_effect = GoneException(410, "bye bye", " 234234")
        actionclient = action_client.ActionClient()
        self.assertRaises(GoneException, actionclient.update)

    # see bz #852706, except this time for idcertlib
    @mock.patch.object(identitycertlib.IdentityCertActionInvoker, 'update')
    def test_idcertlib_gone_exception(self, mock_update):
        mock_update.side_effect = GoneException(410, "bye bye", " 234234")
        actionclient = action_client.ActionClient()
        self.assertRaises(GoneException, actionclient.update)

        # just verify the certlib update worked
        report = actionclient.entcertlib.report
        self.assertTrue(self.stub_ent1.serial in report.valid)

    @mock.patch.object(entcertlib.EntCertActionInvoker, 'update')
    @mock.patch('subscription_manager.base_action_client.log')
    def test_entcertlib_update_exception(self, mock_log, mock_update):
        mock_update.side_effect = ExceptionalException()
        actionclient = action_client.ActionClient()
        actionclient.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")

    @mock.patch.object(identitycertlib.IdentityCertActionInvoker, 'update')
    @mock.patch('subscription_manager.base_action_client.log')
    def test_idcertlib_update_exception(self, mock_log, mock_update):
        mock_update.side_effect = ExceptionalException()
        actionclient = action_client.ActionClient()
        actionclient.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")

    def _stub_certificate_calls(self, stub_ents=None):
        stub_ents = stub_ents or []
        stub_ent_dir = stubs.StubEntitlementDirectory(stub_ents)

        inj.provide(inj.ENT_DIR, stub_ent_dir)

        # don't need to build real pem's, we mock out the writer anyway
        # so this just create a list of mock keys and stub ent certs
        stub_certificate_list = []
        for stub_cert in self.local_ent_certs:
            stub_certificate_list.append((mock.Mock(), stub_cert))

        # return a list of stub ent certs, could be new stubs, but
        # we already have created that
        self.mock_uep.getCertificates.return_value = stub_certificate_list

    # we need to simulate the client missing some ent certs
    @mock.patch.object(entcertlib.EntitlementCertBundleInstaller, 'build_cert')
    def test_missing(self, cert_build_mock):
        # mock no certs client side
        self._stub_certificate_calls()

        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)
        actionclient = action_client.ActionClient()
        actionclient.update()

        report = actionclient.entcertlib.report
        self.assertTrue(self.stub_ent1 in report.added)

    def test_rogue(self):
        # to mock "rogue" certs we need some local, that are not known to the
        # server so getCertificateSerials to return nothing
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        self.set_consumer_auth_cp(self.mock_uep)
        actionclient = action_client.ActionClient()
        actionclient.update()

        report = actionclient.entcertlib.report
        # our local ent certs should be showing up as rogue
        self.assertTrue(self.local_ent_certs[0] in report.rogue)
        self.assertTrue(self.local_ent_certs[1] in report.rogue)

    @mock.patch.object(entcertlib.EntitlementCertBundleInstaller, 'build_cert')
    def test_expired(self, cert_build_mock):
        cert_build_mock.return_value = (mock.Mock(), self.stub_ent1)

        # this makes the stub_ent_dir report all ents as being expired
        # so we fetch new ones
        self.stub_ent_dir.list_expired = mock.Mock(
                return_value=self.stub_ent_dir.list())

        # we don't want to find replacements, so this forces a delete
        self.mock_uep.getCertificateSerials = mock.Mock(return_value=[])
        self.set_consumer_auth_cp(self.mock_uep)

        actionclient = action_client.ActionClient()
        actionclient.update()

        report = actionclient.entcertlib.report
        # the expired certs should be delete/rogue and expired
        #report = self.update_action_syslog_mock.call_args[0][0]
        self.assertTrue(self.stub_ent1 in report.rogue)

    @mock.patch.object(entcertlib.EntitlementCertBundleInstaller, 'build_cert')
    @mock.patch('subscription_manager.entcertlib.log')
    def test_exception_on_cert_write(self, mock_log, mock_cert_build):
        # this is basically the same as test_missing, expect we throw
        # an exception attempting to write the certs out
        self._stub_certificate_calls()

        mock_cert_build.side_effect = ExceptionalException()
        actionclient = action_client.ActionClient()
        # we should fail on the certlib.update, but keep going...
        # and handle it well.
        actionclient.update()

        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], ExceptionalException):
                return
        self.fail("Did not ExceptionException in the logged exceptions")


class TestHealingActionClient(TestActionClient):
    def test_healing_no_heal(self):
        self.mock_cert_sorter.is_valid = mock.Mock(return_value=True)
        self.mock_cert_sorter.compliant_until = datetime.now() + \
                timedelta(days=15)
        actionclient = action_client.HealingActionClient()
        actionclient.update(autoheal=True)
        self.assertFalse(self.mock_uep.bind.called)

    def test_healing_needs_heal(self):
        # need a stub product dir with prods with no entitlements,
        # don't have to mock here since we can actually pass in a product
        self.mock_cert_sorter.is_valid = mock.Mock(return_value=False)
        actionclient = action_client.HealingActionClient()
        actionclient.update(autoheal=True)
        self.assertTrue(self.mock_uep.bind.called)

    @mock.patch.object(entcertlib.EntitlementCertBundleInstaller, 'build_cert')
    def test_healing_needs_heal_tomorrow(self, cert_build_mock):
        # Valid today, but not valid 24h from now:
        self.mock_cert_sorter.is_valid = mock.Mock(return_value=True)
        self.mock_cert_sorter.compliant_until = datetime.now(GMT()) + \
                timedelta(hours=6)
        cert_build_mock.return_value = (mock.Mock(),
                self.stub_ent_expires_tomorrow)

        self._stub_certificate_calls([self.stub_ent_expires_tomorrow])
        actionclient = action_client.HealingActionClient()
        actionclient.update(autoheal=True)
        # see if we tried to update certs
        self.assertTrue(self.mock_uep.bind.called)

    # TODO: use Mock(wraps=) instead of hiding all logging
    @mock.patch('subscription_manager.healinglib.log')
    def test_healing_trigger_exception(self, mock_log):
        # Forcing is_valid to throw the type error we used to expect from
        # cert sorter using the product dir. Just making sure an unexpected
        # exception is logged and not bubbling up.
        self.mock_cert_sorter.is_valid = mock.Mock(side_effect=TypeError())
        actionclient = action_client.HealingActionClient()
        actionclient.update(autoheal=True)
        for call in mock_log.method_calls:
            if call[0] == 'exception' and isinstance(call[1][0], TypeError):
                return
        self.fail("Did not see TypeError in the logged exceptions")
