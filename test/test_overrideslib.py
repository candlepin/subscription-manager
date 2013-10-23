# -*- coding: utf-8 -*-
from fixture import SubManFixture, dict_list_equals
from subscription_manager.overrides import OverrideLib
from subscription_manager.injection import require, CP_PROVIDER

class OverrideTests(SubManFixture):

    def setUp(self):
        SubManFixture.setUp(self)
        self.cp = require(CP_PROVIDER).consumer_auth_cp
        self.override_lib = OverrideLib(self.cp)

    def test_add_function(self):
        repos = ['x', 'y']
        overrides = {'a': 'b', 'c': 'd'}
        expected = [
            {'contentLabel': 'x', 'name': 'a', 'value': 'b'},
            {'contentLabel': 'x', 'name': 'c', 'value': 'd'},
            {'contentLabel': 'y', 'name': 'a', 'value': 'b'},
            {'contentLabel': 'y', 'name': 'c', 'value': 'd'},
        ]
        result = self.override_lib._add(repos, overrides)
        self.assertTrue(dict_list_equals(expected, result))

    def test_remove_function(self):
        repos = ['x', 'y']
        removes = ['a', 'b']
        expected = [
            {'contentLabel': 'x', 'name': 'a'},
            {'contentLabel': 'x', 'name': 'b'},
            {'contentLabel': 'y', 'name': 'a'},
            {'contentLabel': 'y', 'name': 'b'},
        ]
        result = self.override_lib._remove(repos, removes)
        self.assertTrue(dict_list_equals(expected, result))

    def test_remove_all(self):
        repos = ['x', 'y']
        expected = [
            {'contentLabel': 'x'},
            {'contentLabel': 'y'},
        ]
        result = self.override_lib._remove_all(repos)
        self.assertTrue(dict_list_equals(expected, result))

    def test_remove_all_with_no_repos_given(self):
        repos = []
        result = self.override_lib._remove_all(repos)
        self.assertEquals(None, result)
