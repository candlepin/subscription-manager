import difflib
import pprint
import unittest

from contextlib import contextmanager
from mock import Mock, NonCallableMock, patch

import stubs
import subscription_manager.injection as inj


class FakeLogger:
    def __init__(self):
        self.expected_msg = ""
        self.msg = None
        self.logged_exception = None

    def debug(self, buf):
        self.msg = buf

    def error(self, buf):
        self.msg = buf

    def exception(self, e):
        self.logged_exception = e

    def set_expected_msg(self, msg):
        self.expected_msg = msg

    def info(self, buf):
        self.msg = buf


class FakeException(Exception):
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class Matcher(object):
    def __init__(self, compare, some_obj):
        self.compare = compare
        self.some_obj = some_obj

    def __eq__(self, other):
        return self.compare(self.some_obj, other)


class SubManFixture(unittest.TestCase):
    """
    Can be extended by any subscription manager test case to make
    sure nothing on the actual system is read/touched, and appropriate
    mocks/stubs are in place.
    """
    def setUp(self):
        # By default mock that we are registered. Individual test cases
        # can override if they are testing disconnected scenario.
        id_mock = Mock()
        id_mock.exists_and_valid = Mock(return_value=True)

        # Don't really care about date ranges here:
        self.mock_calc = NonCallableMock()
        self.mock_calc.calculate.return_value = None

        inj.provide(inj.IDENTITY, id_mock)
        inj.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR, self.mock_calc)

        inj.provide(inj.ENTITLEMENT_STATUS_CACHE, stubs.StubEntitlementStatusCache())
        inj.provide(inj.PROD_STATUS_CACHE, stubs.StubProductStatusCache())
        inj.provide(inj.OVERRIDE_STATUS_CACHE, stubs.StubOverrideStatusCache())
        # By default set up an empty stub entitlement and product dir.
        # Tests need to modify or create their own but nothing should hit
        # the system.
        self.ent_dir = stubs.StubEntitlementDirectory()
        inj.provide(inj.ENT_DIR, self.ent_dir)
        self.prod_dir = stubs.StubProductDirectory()
        inj.provide(inj.PROD_DIR, self.prod_dir)
        inj.provide(inj.CP_PROVIDER, stubs.StubCPProvider())
        inj.provide(inj.CERT_SORTER, stubs.StubCertSorter())

        # setup and mock the plugin_manager
        plugin_manager_mock = Mock()
        inj.provide(inj.PLUGIN_MANAGER, plugin_manager_mock)
        inj.provide(inj.DBUS_IFACE, Mock())

        self.dbus_patcher = patch('subscription_manager.managercli.CliCommand._request_validity_check')
        self.dbus_patcher.start()

    def tearDown(self):
        self.dbus_patcher.stop()

    def get_consumer_cp(self):
        cp_provider = inj.require(inj.CP_PROVIDER)
        consumer_cp = cp_provider.get_consumer_auth_cp()
        return consumer_cp

    # use our naming convention here to make it clear
    # this is our extension. Note that python 2.7 adds a
    # assertMultilineEquals that assertEqual of strings does
    # automatically
    def assert_string_equals(self, first_str, second_str, msg=None):
        if first_str != second_str:
            first_lines = first_str.splitlines(True)
            second_lines = second_str.splitlines(True)
            delta = difflib.unified_diff(first_lines, second_lines)
            message = ''.join(delta)

            if msg:
                message += " : " + msg

            self.fail("Multi-line strings are unequal:\n" + message)

    def assert_equal_dict(self, expected_dict, actual_dict):
        mismatches = []
        missing_keys = []
        extra = []

        for key in expected_dict:
            if key not in actual_dict:
                missing_keys.append(key)
                continue
            if expected_dict[key] != actual_dict[key]:
                mismatches.append((key, expected_dict[key], actual_dict[key]))

        for key in actual_dict:
            if key not in expected_dict:
                extra.append(key)

        message = ""
        if missing_keys or extra:
            message += "Keys in only one dict: \n"
            if missing_keys:
                for key in missing_keys:
                    message += "actual_dict:  %s\n" % key
            if extra:
                for key in extra:
                    message += "expected_dict: %s\n" % key
        if mismatches:
            message += "Unequal values: \n"
            for info in mismatches:
                message += "%s: %s != %s\n" % info

        # pprint the dicts
        message += "\n"
        message += "expected_dict:\n"
        message += pprint.pformat(expected_dict)
        message += "\n"
        message += "actual_dict:\n"
        message += pprint.pformat(actual_dict)

        if mismatches or missing_keys or extra:
            self.fail(message)


def dict_list_equals(a, b):
    """
    Meant to compare two lists of dictionaries and see if they
    contain the same dictionaries regardless of order.  We can't
    actually use set() with dictionaries because dictionaries are
    not hashable.
    """
    if a is b:
        return True
    if len(a) != len(b):
        return False
    b = list(b)
    for a_item in a:
        for b_item in b:
            if a_item == b_item:
                b.remove(b_item)
                break
        else:
            return False
    return len(b) == 0


class TestDictListEquals(unittest.TestCase):
    def test_identical(self):
        a = [{'a': 'b'}]
        b = a
        self.assertTrue(dict_list_equals(a, b))

    def test_equal(self):
        a = [{'a': 'b'}]
        b = [{'a': 'b'}]
        self.assertTrue(dict_list_equals(a, b))

    def test_same_dicts_different_order(self):
        a = [{'c': 'd'}, {'a': 'b'}]
        b = [{'a': 'b'}, {'c': 'd'}]
        self.assertTrue(dict_list_equals(a, b))

    def test_b_has_others(self):
        a = [{'c': 'd'}, {'e': 'f'}]
        b = [{'a': 'b'}, {'c': 'd'}]
        self.assertFalse(dict_list_equals(a, b))

    def test_a_has_extras(self):
        a = [{'a': 'b'}, {'c': 'd'}]
        b = [{'c': 'd'}]
        self.assertFalse(dict_list_equals(a, b))

    def test_not_equals_at_all(self):
        a = [{'a': 'b'}]
        b = [{'c': 'd'}]
        self.assertFalse(dict_list_equals(a, b))

    def test_equals_with_dupes(self):
        a = [{'a': 'b'}, {'a': 'b'}, {'c': 'd'}]
        b = [{'c': 'd'}, {'a': 'b'}, {'a': 'b'}]
        self.assertTrue(dict_list_equals(a, b))

    def test_one_dict_is_super_set(self):
        a = [{'a': 'b'}]
        b = [{'a': 'b', 'c': 'd'}]
        self.assertFalse(dict_list_equals(a, b))


@contextmanager
def capture():
    import sys
    import StringIO
    old_out = sys.stdout
    try:
        out = StringIO.StringIO()
        sys.stdout = out
        yield out
    finally:
        sys.stdout = old_out
