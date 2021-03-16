# -*- coding: utf-8 -*-

import re
import sys

from ..test_managercli import TestCliCommand
from subscription_manager import managercli
from subscription_manager.repolib import Repo

from ..fixture import Capture, Matcher, set_up_mock_sp_store

from mock import patch, Mock, call


class TestReposCommand(TestCliCommand):
    command_class = managercli.ReposCommand

    def setUp(self):
        super(TestReposCommand, self).setUp(False)
        argv_patcher = patch.object(sys, 'argv', ['subscription-manager', 'repos'])
        argv_patcher.start()
        self.addCleanup(argv_patcher.stop)
        self.cc.cp = Mock()
        syspurpose_patch = patch('subscription_manager.syspurposelib.SyncedStore')
        self.mock_sp_store = syspurpose_patch.start()
        self.mock_sp_store, self.mock_sp_store_contents = set_up_mock_sp_store(self.mock_sp_store)
        self.addCleanup(syspurpose_patch.stop)

    def check_output_for_repos(self, output, repos):
        """
        Checks the given output string for the specified repos' ids.

        Returns a tuple of booleans specifying whether or not the repo in the corresponding position
        was found in the output.
        """
        searches = []
        for repo in repos:
            # Impl note: This may break if a repo's ID contains special regex characters.
            searches.append(re.search("^Repo ID:\\s+%s$" % repo.id, output, re.MULTILINE) is not None)

        return tuple(searches)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_default(self, mock_invoker):
        self.cc.main()
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list(self, mock_invoker):
        self.cc.main(["--list"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_with_enabled(self, mock_invoker):
        self.cc.main(["--list", "--list-enabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_with_disabled(self, mock_invoker):
        self.cc.main(["--list", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_with_enabled_and_disabled(self, mock_invoker):
        self.cc.main(["--list", "--list-disabled", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_enabled(self, mock_invoker):
        self.cc.main(["--list-enabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")]),
                 Repo("a", [("enabled", "false")]), Repo("b", [("enabled", "False")]), Repo("c", [("enabled", "true")])
                 ]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, False, False, False, False, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_disabled(self, mock_invoker):
        self.cc.main(["--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((False, True, True), result)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_list_enabled_and_disabled(self, mock_invoker):
        self.cc.main(["--list-enabled", "--list-disabled"])
        self.cc._validate_options()

        repos = [Repo("x", [("enabled", "1")]), Repo("y", [("enabled", "0")]), Repo("z", [("enabled", "0")])]
        mock_invoker.return_value.get_repos.return_value = repos

        with Capture() as cap:
            self.cc._do_command()

        result = self.check_output_for_repos(cap.out, repos)
        self.assertEqual((True, True, True), result)

    def test_enable(self):
        self.cc.main(["--enable", "one", "--enable", "two"])
        self.cc._validate_options()

    def test_disable(self):
        self.cc.main(["--disable", "one", "--disable", "two"])
        self.cc._validate_options()

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_set_repo_status(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('x'), Repo('y'), Repo('z')]
        items = [('0', 'x'), ('0', 'y')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [{'contentLabel': i, 'name': 'enabled', 'value': '0'} for (_action, i) in items]
        metadata_overrides = [{'contentLabel': i, 'name': 'enabled_metadata', 'value': '0'} for (_action, i) in items]
        expected_overrides.extend(metadata_overrides)

        # The list of overrides sent to setContentOverrides is really a set of
        # dictionaries (since we don't know the order of the overrides).
        # However, since the dict class is not hashable, we can't actually use
        # a set.  So we need a custom matcher to make sure that the
        # JSON passed in to setContentOverrides is what we expect.
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_set_repo_status_with_wildcards(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('0', 'z*')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [{'contentLabel': i.id, 'name': 'enabled', 'value': '0'} for i in repos]
        metadata_overrides = [{'contentLabel': i.id, 'name': 'enabled_metadata', 'value': '0'} for i in repos]
        expected_overrides.extend(metadata_overrides)
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id', match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_set_repo_status_disable_all_enable_some(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('0', '*'), ('1', 'zoo'),
            ('1', 'zip')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zebra', 'name': 'enabled_metadata', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'zoo', 'name': 'enabled_metadata', 'value': '1'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'zip', 'name': 'enabled_metadata', 'value': '1'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_set_repo_status_enable_all_disable_some(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('1', '*'), ('0', 'zoo'),
            ('0', 'zip')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '1'},
            {'contentLabel': 'zebra', 'name': 'enabled_metadata', 'value': '1'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled_metadata', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled_metadata', 'value': '0'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @patch("subscription_manager.cli_command.repos.RepoActionInvoker")
    def test_set_repo_status_enable_all_disable_all(self, mock_repolib):
        repolib_instance = mock_repolib.return_value
        self._inject_mock_valid_consumer('fake_id')

        repos = [Repo('zoo'), Repo('zebra'), Repo('zip')]
        items = [('1', '*'), ('0', '*')]
        self.cc.use_overrides = True
        self.cc._set_repo_status(repos, repolib_instance, items)

        expected_overrides = [
            {'contentLabel': 'zebra', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zebra', 'name': 'enabled_metadata', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zoo', 'name': 'enabled_metadata', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled', 'value': '0'},
            {'contentLabel': 'zip', 'name': 'enabled_metadata', 'value': '0'}
        ]
        match_dict_list = Matcher(self.assert_items_equals, expected_overrides)
        self.cc.cp.setContentOverrides.assert_called_once_with('fake_id',
                match_dict_list)
        self.assertTrue(repolib_instance.update.called)

    @patch("subscription_manager.cli_command.repos.YumRepoFile")
    def test_set_repo_status_when_disconnected(self, mock_repofile):
        self._inject_mock_invalid_consumer()
        mock_repofile_inst = mock_repofile.return_value

        enabled = list({'enabled': '1'}.items())
        disabled = list({'enabled': '0'}.items())

        zoo = Repo('zoo', enabled)
        zebra = Repo('zebra', disabled)
        zippy = Repo('zippy', enabled)
        zero = Repo('zero', disabled)
        repos = [zoo, zebra, zippy, zero]
        items = [('0', 'z*')]

        self.cc._set_repo_status(repos, None, items)
        calls = [call(r) for r in repos if r['enabled'] == 1]
        mock_repofile_inst.update.assert_has_calls(calls)
        for r in repos:
            self.assertEqual('0', r['enabled'])
        mock_repofile_inst.write.assert_called_once_with()
