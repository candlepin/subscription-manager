import os

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.cli_command.abstract_syspurpose import AbstractSyspurposeCommand

from ..stubs import StubUEP
from ..fixture import Capture

from mock import patch, Mock, MagicMock


class TestSyspurposeCommand(TestCliProxyCommand):
    command_class = managercli.RoleCommand

    def setUp(self):
        synced_store_patch = patch('subscription_manager.cli_command.abstract_syspurpose.SyncedStore')
        self.synced_store_mock = synced_store_patch.start()
        self.addCleanup(self.synced_store_mock)
        syspurpose_patch = patch('syspurpose.files.SyncedStore')
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        super(TestSyspurposeCommand, self).setUp(False)
        self.cc = self.command_class()
        self.cc.cp = StubUEP()
        self.cc.cp.registered_consumer_info['role'] = None
        self.cc.cp._capabilities = ["syspurpose"]

    def test_show_option(self):
        self.cc.main(["--show"])


class TestRoleCommand(TestCliProxyCommand):
    command_class = managercli.RoleCommand

    def setUp(self):
        synced_store_patch = patch('subscription_manager.cli_command.abstract_syspurpose.SyncedStore')
        self.synced_store_mock = synced_store_patch.start()
        self.addCleanup(self.synced_store_mock)
        syspurpose_patch = patch('syspurpose.files.SyncedStore')
        sp_patch = syspurpose_patch.start()
        self.addCleanup(sp_patch.stop)
        super(TestRoleCommand, self).setUp(False)
        self.cc = self.command_class()
        self.cc.cp = StubUEP()
        self.cc.cp.registered_consumer_info['role'] = None
        self.cc.cp._capabilities = ["syspurpose"]

    def test_list_username_password_org(self):
        self.cc.is_registered = Mock(return_value=False)
        self.cc.main(["--username", "admin", "--password", "secret", "--org", "one", "--list"])

    def test_list_username_password(self):
        self.cc.is_registered = Mock(return_value=False)
        self.cc.main(["--username", "admin", "--password", "secret", "--list"])

    def test_list_only_username(self):
        self.cc.options = Mock()
        self.cc.is_registered = Mock(return_value=False)
        self.cc.options.set = False
        self.cc.options.unset = False
        self.cc.options.to_add = False
        self.cc.options.to_remove = False
        self.cc.options.list = True
        self.cc.options.token = None
        self.cc.options.username = "admin"
        self.cc.options.password = None
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_list_username_and_token(self):
        self.cc.options = Mock()
        self.cc.is_registered = Mock(return_value=False)
        self.cc.options.set = False
        self.cc.options.unset = False
        self.cc.options.to_add = False
        self.cc.options.to_remove = False
        self.cc.options.list = True
        self.cc.options.token = "TOKEN"
        self.cc.options.username = "admin"
        self.cc.options.password = "secret"
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

    def test_wrong_options_syspurpose_role(self):
        """It is possible to use --set or --unset options. It's not possible to use both of them together."""
        self.cc.options = Mock()
        self.cc.options.set = "Foo"
        self.cc.options.unset = True
        self.cc.options.to_add = False
        self.cc.options.to_remove = False
        try:
            self.cc._validate_options()
        except SystemExit as e:
            self.assertEqual(e.code, os.EX_USAGE)

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

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    def test_main_no_args(self, mock_syspurpose):
        # It is necessary to mock SyspurposeStore for test function of parent class
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.local_contents = {'role': 'Foo'}

        with patch.object(AbstractSyspurposeCommand, 'check_syspurpose_support', Mock(return_value=None)):
            super(TestRoleCommand, self).test_main_no_args()

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    def test_main_empty_args(self, mock_syspurpose):
        # It is necessary to mock SyspurposeStore for test function of parent class
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.local_contents = {'role': 'Foo'}

        with patch.object(AbstractSyspurposeCommand, 'check_syspurpose_support', Mock(return_value=None)):
            super(TestRoleCommand, self).test_main_empty_args()

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    @patch("subscription_manager.syspurposelib.SyspurposeSyncActionCommand")
    def test_display_valid_syspurpose_role(self, mock_syspurpose_sync, mock_syspurpose):
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {'role': 'Foo'}

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = None
        self.cc.options.unset = False

        mock_syspurpose_sync.return_value = Mock()
        instance_mock_syspurpose_sync = mock_syspurpose_sync.return_value

        mock_sync_result = Mock()
        mock_sync_result.result = {"role": "Foo"}
        instance_mock_syspurpose_sync.perform = Mock(return_value=({}, mock_sync_result))

        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Current Role: Foo", cap.out)

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    def test_display_none_syspurpose_role(self, mock_syspurpose):
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {'role': None}

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = None
        self.cc.options.unset = False
        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Role not set", cap.out)

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    def test_display_nonexisting_syspurpose_role(self, mock_syspurpose):
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {}

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = None
        self.cc.options.unset = False

        with Capture() as cap:
            self.cc._do_command()
        self.assertIn("Role not set.", cap.out)

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    @patch("subscription_manager.syspurposelib.SyspurposeSyncActionCommand")
    def test_setting_syspurpose_role(self, mock_syspurpose_sync, mock_syspurpose):
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {}
        instance_syspurpose_store.set = MagicMock(return_value=True)
        instance_syspurpose_store.write = MagicMock(return_value=None)
        instance_syspurpose_store.get_cached_contents = Mock(return_value={"role": "Foo"})
        mock_syspurpose.return_value = instance_syspurpose_store

        mock_syspurpose_sync.return_value = Mock()
        instance_mock_syspurpose_sync = mock_syspurpose_sync.return_value
        instance_mock_syspurpose_sync.perform = Mock(return_value=({}, {"role": "Foo"}))

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = 'Foo'
        self.cc.options.unset = False

        with Capture() as cap:
            self.cc._do_command()

        self.assertIn('role set to "Foo"', cap.out)
        instance_syspurpose_store.set.assert_called_once_with('role', 'Foo')
        instance_syspurpose_store.sync.assert_called_once()

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    @patch("subscription_manager.syspurposelib.SyspurposeSyncActionCommand")
    def test_setting_conflicting_syspurpose_role(self, mock_syspurpose_sync, mock_syspurpose):
        """
        Test the case, when there is conflict with value set by administrator on server
        """
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {}
        instance_syspurpose_store.set = MagicMock(return_value=True)
        instance_syspurpose_store.write = MagicMock(return_value=None)
        instance_syspurpose_store.get_cached_contents = Mock(return_value={"role": "Foo"})
        mock_syspurpose.return_value = instance_syspurpose_store

        mock_syspurpose_sync.return_value = Mock()
        instance_mock_syspurpose_sync = mock_syspurpose_sync.return_value
        instance_mock_syspurpose_sync.perform = Mock(return_value=({}, {"role": "Foo"}))

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = 'Bar'
        self.cc.options.unset = False

        with Capture() as cap:
            with self.assertRaises(SystemExit) as cm:
                self.cc._do_command()
            self.assertEqual(cm.exception.code, 70)

        self.assertIn(
            'Warning: A role of "Foo" was recently set for this system by the entitlement server administrator.',
            cap.err
        )
        self.assertIn(
            'If you\'d like to overwrite the server side change please run: subscription-manager role --set "Bar"',
            cap.err
        )

    @patch("subscription_manager.cli_command.abstract_syspurpose.SyncedStore")
    @patch("subscription_manager.syspurposelib.SyspurposeSyncActionCommand")
    def test_unsetting_syspurpose_role(self, mock_syspurpose_sync, mock_syspurpose):
        mock_syspurpose.read = Mock()
        mock_syspurpose.read.return_value = Mock()
        instance_syspurpose_store = mock_syspurpose.read.return_value
        instance_syspurpose_store.contents = {'role': 'Foo'}
        instance_syspurpose_store.unset = MagicMock(return_value=True)
        instance_syspurpose_store.write = MagicMock(return_value=None)
        instance_syspurpose_store.get_cached_contents = MagicMock(return_value={})
        mock_syspurpose.return_value = instance_syspurpose_store

        mock_syspurpose_sync.return_value = Mock()
        instance_mock_syspurpose_sync = mock_syspurpose_sync.return_value
        instance_mock_syspurpose_sync.perform = Mock(return_value=({}, {"role": ""}))

        self.cc.options = Mock(spec=['set', 'unset'])
        self.cc.options.set = None
        self.cc.options.unset = True
        with Capture() as cap:
            self.cc._do_command()

        self.assertIn("role unset", cap.out)
        instance_syspurpose_store.unset.assert_called_once_with('role')
        instance_syspurpose_store.sync.assert_called_once()

    def test_is_provided_value_valid(self):
        self.cc = AbstractSyspurposeCommand("role", None, shortdesc="role", primary=False, attr="role")
        self.cc._get_valid_fields = Mock()
        self.cc._get_valid_fields.return_value = {"role": ["Welcome to the Machine"]}
        res = self.cc._is_provided_value_valid("wElcOme To The mAChiNE")
        self.assertTrue(res)
