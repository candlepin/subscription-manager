# -*- coding: utf-8 -*-

import unittest

from subscription_manager.cli_command.list import AVAILABLE_SUBS_MATCH_COLUMNS
from subscription_manager.cli_command import status
from subscription_manager.printing_utils import format_name, columnize, echo_columnize_callback, \
    none_wrap_columnize_callback, highlight_by_filter_string_columnize_cb, FONT_BOLD, FONT_RED, FONT_NORMAL

from mock import patch, Mock


class TestFormatName(unittest.TestCase):
    def setUp(self):
        self.indent = 1
        self.max_length = 40

    def test_format_name_long(self):
        name = "This is a Really Long Name For A Product That We Do Not Want To See But Should Be Able To Deal With"
        format_name(name, self.indent, self.max_length)

    def test_format_name_short(self):
        name = "a"
        format_name(name, self.indent, self.max_length)

    def test_format_name_empty(self):
        name = ''
        new_name = format_name(name, self.indent, self.max_length)
        self.assertEqual(name, new_name)

    def test_format_name_null_width(self):
        name = "This is a Really Long Name For A Product That We Do Not Want To See But Should Be Able To Deal With"
        new_name = format_name(name, self.indent, None)
        self.assertEqual(name, new_name)

    def test_format_name_none(self):
        name = None
        new_name = format_name(name, self.indent, self.max_length)
        self.assertTrue(new_name is None)

    def test_leading_spaces(self):
        name = " " * 4 + "I have four leading spaces"
        new_name = format_name(name, 3, 10)
        self.assertEqual("    I have\n   four\n   leading\n   spaces", new_name)

    def test_leading_tabs(self):
        name = "\t" * 4 + "I have four leading tabs"
        new_name = format_name(name, self.indent, self.max_length)
        self.assertEqual("\t" * 4, new_name[0:4])


class TestHighlightByFilter(unittest.TestCase):
    def test_highlight_by_filter_string(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "Super*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_cb("Subscription Name:    %s", *args, **kwargs)
        self.assertEqual(result, 'Subscription Name:    ' + FONT_BOLD + FONT_RED + 'Super Test Subscription' + FONT_NORMAL)

    def test_highlight_by_filter_string_single(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "*Subscriptio?",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_cb("Subscription Name:    %s", *args, **kwargs)
        self.assertEqual(result, 'Subscription Name:    ' + FONT_BOLD + FONT_RED + 'Super Test Subscription' + FONT_NORMAL)

    def test_highlight_by_filter_string_all(self):
        args = ['Super Test Subscription']
        kwargs = {"filter_string": "*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_cb("Subscription Name:    %s", *args, **kwargs)
        self.assertEqual(result, 'Subscription Name:    Super Test Subscription')

    def test_highlight_by_filter_string_exact(self):
        args = ['Premium']
        kwargs = {"filter_string": "Premium",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Service Level:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_cb("Service Level:    %s", *args, **kwargs)
        self.assertEqual(result, 'Service Level:    ' + FONT_BOLD + FONT_RED + 'Premium' + FONT_NORMAL)

    def test_highlight_by_filter_string_list_row(self):
        args = ['Awesome-os-stacked']
        kwargs = {"filter_string": "Awesome*",
                  "match_columns": AVAILABLE_SUBS_MATCH_COLUMNS,
                  "caption": "Subscription Name:",
                  "is_atty": True}
        result = highlight_by_filter_string_columnize_cb("    %s", *args, **kwargs)
        self.assertEqual(result, '    ' + FONT_BOLD + FONT_RED + 'Awesome-os-stacked' + FONT_NORMAL)


class TestNoneWrap(unittest.TestCase):
    def test_none_wrap(self):
        result = none_wrap_columnize_callback('foo %s %s', 'doberman pinscher', None)
        self.assertEqual(result, 'foo doberman pinscher None')


class TestColumnize(unittest.TestCase):
    def setUp(self):
        self.old_method = status.get_terminal_width
        status.get_terminal_width = Mock(return_value=500)

    def tearDown(self):
        status.get_terminal_width = self.old_method

    def test_columnize(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, "world", "bar")
        self.assertEqual(result, "Hello: world\nFoo:   bar")

    def test_columnize_with_list(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, ["world", "space"], "bar")
        self.assertEqual(result, "Hello: world\n       space\nFoo:   bar")

    def test_columnize_with_empty_list(self):
        result = columnize(["Hello:", "Foo:"], echo_columnize_callback, [], "bar")
        self.assertEqual(result, "Hello: \nFoo:   bar")

    @patch('subscription_manager.printing_utils.get_terminal_width')
    def test_columnize_with_small_term(self, term_width_mock):
        term_width_mock.return_value = None
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                           echo_columnize_callback, "This is a testing string", "This_is_another_testing_string")
        expected = 'Hello\nHello\nHello\nHello\n:     This\n      is a\n      ' \
                   'testin\n      g\n      string\nFoo\nFoo\nFoo\nFoo:  ' \
                   'This_i\n      s_anot\n      her_te\n      sting_\n      string'
        self.assertNotEqual(result, expected)
        term_width_mock.return_value = 12
        result = columnize(["Hello Hello Hello Hello:", "Foo Foo Foo Foo:"],
                           echo_columnize_callback, "This is a testing string", "This_is_another_testing_string")
        self.assertEqual(result, expected)

    def test_format_name_no_break_no_indent(self):
        result = format_name('testing string testing st', 0, 10)
        expected = 'testing\nstring\ntesting st'
        self.assertEqual(result, expected)

    def test_format_name_no_break(self):
        result = format_name('testing string testing st', 1, 11)
        expected = 'testing\n string\n testing st'
        self.assertEqual(result, expected)
        result = format_name('testing string testing st', 2, 12)
        expected = 'testing\n  string\n  testing st'
        self.assertEqual(result, expected)

    def test_format_name_break(self):
        result = format_name('a' * 10, 0, 10)
        expected = 'a' * 10
        self.assertEqual(result, expected)
        result = format_name('a' * 11, 0, 10)
        expected = 'a' * 10 + '\na'
        self.assertEqual(result, expected)
        result = format_name('a' * 11 + ' ' + 'a' * 9, 0, 10)
        expected = 'a' * 10 + '\na\n' + 'a' * 9
        self.assertEqual(result, expected)

    def test_format_name_break_indent(self):
        result = format_name('a' * 20, 1, 10)
        expected = 'a' * 9 + '\n ' + 'a' * 9 + '\n ' + 'aa'
        self.assertEqual(result, expected)

    @patch('subscription_manager.printing_utils.get_terminal_width')
    def test_columnize_multibyte(self, term_width_mock):
        multibyte_str = u"このシステム用に"
        term_width_mock.return_value = 40
        result = columnize([multibyte_str], echo_columnize_callback, multibyte_str)
        expected = u"このシステム用に このシステム用に"
        self.assertEqual(result, expected)
        term_width_mock.return_value = 14
        result = columnize([multibyte_str], echo_columnize_callback, multibyte_str)
        expected = u"このシ\nステム\n用に   このシ\n       ステム\n       用に"
        self.assertEqual(result, expected)
