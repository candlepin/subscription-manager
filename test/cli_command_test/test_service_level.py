# -*- coding: utf-8 -*-

import os
import shutil
import tempfile

from ..test_managercli import TestCliProxyCommand
from subscription_manager import syspurposelib
from subscription_manager import managercli

from ..stubs import StubConsumerIdentity, StubUEP
from ..fixture import set_up_mock_sp_store

from mock import patch, Mock, call


class TestServiceLevelCommand(TestCliProxyCommand):
    command_class = managercli.ServiceLevelCommand

    def setUp(self):
        syspurpose_patch = patch('syspurpose.files.SyncedStore')
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        TestCliProxyCommand.setUp(self)
        self.cc.consumerIdentity = StubConsumerIdentity
        self.cc.cp = StubUEP()
        # Set up syspurpose mocking, do not test functionality of other source tree.
        from subscription_manager import syspurposelib

        self.syspurposelib = syspurposelib
        self.syspurposelib.USER_SYSPURPOSE = self.write_tempfile("{}").name

        syspurpose_patch = patch('subscription_manager.cli_command.abstract_syspurpose.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def tearDown(self):
        super(TestServiceLevelCommand, self).tearDown()
        syspurposelib.USER_SYSPURPOSE = "/etc/rhsm/syspurpose/syspurpose.json"

    def test_main_server_url(self):
        server_url = "https://subscription.rhsm.redhat.com/subscription"
        self.cc.main(["--serverurl", server_url])

    def test_insecure(self):
        self.cc.main(["--insecure"])

    def test_org_requires_list_error(self):
        try:
            self.cc.main(["--org", "one"])
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_set_allows_list_good(self):
        self.cc.is_registered = Mock(return_value=False)
        self.cc.main(["--set", "two", "--org", "test"])
        self.cc._validate_options()

    def test_org_requires_list_good(self):
        self.cc.main(["--org", "one", "--list"])

    def test_list_with_one_org_no_prompt(self):
        owner_list = self.cc.cp.getOwnerList
        self.cc.cp.getOwnerList = Mock(return_value='test_org')
        self.cc.main(["--list"])
        self.cc.cp.getOwnerList = owner_list

    def test_service_level_supported(self):
        self.cc.cp.setConsumer({'serviceLevel': 'Jarjar'})
        self.cc._set('JRJAR')

    @patch("subscription_manager.cli_command.service_level.SyncedStore")
    def test_service_level_creates_syspurpose_dir_and_file(self, mock_syspurpose):
        # create a mock /etc/rhsm/ directory, and set the value of a mock USER_SYSPURPOSE under that
        old_capabilities = self.cc.cp._capabilities
        self.cc.cp._capabilities = ['syspurpose']
        self.cc.store = self.mock_sp_store()
        self.cc.store.get_cached_contents = Mock(return_value={})

        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        mock_syspurpose.return_value = self.mock_sp_store()

        mock_etc_rhsm_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, mock_etc_rhsm_dir)
        mock_syspurpose_file = os.path.join(mock_etc_rhsm_dir, "syspurpose/syspurpose.json")
        syspurposelib.USER_SYSPURPOSE = mock_syspurpose_file

        self.cc.store = self.mock_sp_store()
        self.cc.options = Mock()
        self.cc.options.set = 'JRJAR'
        self.cc.set()

        self.cc.store.set.assert_has_calls([call("service_level_agreement", "JRJAR")])

        # make sure the sla has been persisted in syspurpose.json:
        contents = self.cc.store.get_local_contents()
        self.assertEqual(contents.get("service_level_agreement"), "JRJAR")
        self.cc.cp._capabilities = old_capabilities

    def test_old_service_level(self):
        self.cc.options = Mock()
        self.cc.cp.getConsumer = Mock(return_value={'serviceLevel': 'foo'})
        self.cc.options.set = 'JRJAR'
        self.cc.cp.updateConsumer = Mock()
        # 'syspurpose' is not in capabilities of server
        self.cc.set()
        self.cc.cp.updateConsumer.assert_has_calls(
            [call('fixture_identity_mock_uuid', service_level='JRJAR')]
        )

    def test_username_on_registered_system(self):
        """Argument --username cannot be used on registered system."""
        self.cc.is_registered = Mock(return_value=True)
        self.cc.options = Mock()
        self.cc.options.set = None
        self.cc.options.unset = None
        self.cc.options.to_add = None
        self.cc.options.to_remove = None
        self.cc.options.show = None
        self.cc.options.list = True
        self.cc.options.username = "admin"
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_password_on_registered_system(self):
        """Argument --password cannot be used on registered system."""
        self.cc.is_registered = Mock(return_value=True)
        self.cc.options = Mock()
        self.cc.options.set = None
        self.cc.options.unset = None
        self.cc.options.to_add = None
        self.cc.options.to_remove = None
        self.cc.options.show = None
        self.cc.options.list = True
        self.cc.options.password = "secret"
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_token_on_registered_system(self):
        """Argument --token cannot be used on registered system."""
        self.cc.is_registered = Mock(return_value=True)
        self.cc.options = Mock()
        self.cc.options.set = None
        self.cc.options.unset = None
        self.cc.options.to_add = None
        self.cc.options.to_remove = None
        self.cc.options.show = None
        self.cc.options.list = True
        self.cc.options.token = "TOKEN"
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_org_on_registered_system(self):
        """Argument --org cannot be used on registered system."""
        self.cc.is_registered = Mock(return_value=True)
        self.cc.options = Mock()
        self.cc.options.set = None
        self.cc.options.unset = None
        self.cc.options.to_add = None
        self.cc.options.to_remove = None
        self.cc.options.show = None
        self.cc.options.list = True
        self.cc.options.org = "organization"
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)
