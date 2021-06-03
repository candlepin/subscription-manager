# -*- coding: utf-8 -*-

import re
import sys

from ..test_managercli import TestCliProxyCommand
from subscription_manager import managercli
from subscription_manager.overrides import Override

from ..fixture import Capture

from mock import patch


class TestOverrideCommand(TestCliProxyCommand):
    command_class = managercli.OverrideCommand

    def _test_exception(self, args):
        self.cc.main(args)
        self.assertRaises(SystemExit, self.cc._validate_options)

    def test_bad_add_format(self):
        self._test_exception(["--add", "hello"])
        self._test_exception(["--add", "hello:"])

    def test_add_and_remove_with_no_repo(self):
        self._test_exception(["--add", "hello:world"])
        self._test_exception(["--remove", "hello"])

    def test_add_and_remove_with_list(self):
        self._test_exception(["--add", "x:y", "--repo", "x", "--list"])
        self._test_exception(["--remove", "y", "--repo", "x", "--list"])

    def test_add_and_remove_with_remove_all(self):
        self._test_exception(["--add", "x:y", "--repo", "x", "--remove-all"])
        self._test_exception(["--remove", "y", "--repo", "x", "--remove-all"])

    def test_list_and_remove_all_mutuall_exclusive(self):
        self._test_exception(["--list", "--remove-all"])

    def test_no_bare_repo(self):
        self._test_exception(["--repo", "x"])

    def test_list_by_default(self):
        with patch.object(sys, 'argv', ['subscription-manager', 'repo-override']):
            self.cc.main([])
            self.cc._validate_options()
            self.assertTrue(self.cc.options.list)

    def test_list_by_default_with_options_from_super_class(self):
        self.cc.main(["--proxy", "http://www.example.com", "--proxyuser", "foo", "--proxypassword", "bar"])
        self.cc._validate_options()
        self.assertTrue(self.cc.options.list)

    def test_add_with_multiple_colons(self):
        self.cc.main(["--repo", "x", "--add", "url:http://example.com"])
        self.cc._validate_options()
        self.assertEqual(self.cc.options.additions, {'url': 'http://example.com'})

    def test_add_and_remove_with_multi_repos(self):
        self.cc.main(["--repo", "x", "--repo", "y", "--add", "a:b", "--remove", "a"])
        self.cc._validate_options()
        self.assertEqual(self.cc.options.repos, ['x', 'y'])
        self.assertEqual(self.cc.options.additions, {'a': 'b'})
        self.assertEqual(self.cc.options.removals, ['a'])

    def test_remove_empty_arg(self):
        self._test_exception(["--repo", "x", "--remove", ""])

    def test_remove_multiple_args_empty_arg(self):
        self._test_exception(["--repo", "x", "--remove", "foo", "--remove", ""])

    def test_add_empty_arg(self):
        self._test_exception(["--repo", "x", "--add", ""])

    def test_add_empty_name(self):
        self._test_exception(["--repo", "x", "--add", ":foo"])

    def test_add_multiple_args_empty_arg(self):
        self._test_exception(["--repo", "x", "--add", "foo:bar", "--add", ""])

    def test_list_and_remove_all_work_with_repos(self):
        self.cc.main(["--repo", "x", "--list"])
        self.cc._validate_options()
        self.cc.main(["--repo", "x", "--remove-all"])
        self.cc._validate_options()

    def _build_override(self, repo, name=None, value=None):
        data = {'contentLabel': repo}
        if name:
            data['name'] = name
        if value:
            data['value'] = value
        return data

    def test_list_function(self):
        data = [
            Override('x', 'hello', 'world'),
            Override('x', 'blast-off', 'space'),
            Override('y', 'goodbye', 'earth'),
            Override('z', 'greetings', 'mars')
        ]
        with Capture() as cap:
            self.cc._list(data, None)
            output = cap.out
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))
            self.assertTrue(re.search('\s+blast-off:\s+space', output))
            self.assertTrue(re.search('Repository: y', output))
            self.assertTrue(re.search('\s+goodbye:\s+earth', output))
            self.assertTrue(re.search('Repository: z', output))
            self.assertTrue(re.search('\s+greetings:\s+mars', output))

    def test_list_specific_repos(self):
        data = [
            Override('x', 'hello', 'world'),
            Override('z', 'greetings', 'mars')
        ]
        with Capture() as cap:
            self.cc._list(data, ['x'])
            output = cap.out
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))
            self.assertFalse(re.search('Repository: z', output))

    def test_list_nonexistant_repos(self):
        data = [
            Override('x', 'hello', 'world')
        ]
        with Capture() as cap:
            self.cc._list(data, ['x', 'z'])
            output = cap.out
            self.assertTrue(re.search("Nothing is known about 'z'", output))
            self.assertTrue(re.search('Repository: x', output))
            self.assertTrue(re.search('\s+hello:\s+world', output))
