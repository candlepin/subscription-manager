import difflib
import pprint
import unittest

from mock import Mock, NonCallableMock, patch

import stubs
import subscription_manager.injection as inj


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

        # By default set up an empty stub entitlement and product dir.
        # Tests need to modify or create their own but nothing should hit
        # the system.
        self.ent_dir = stubs.StubEntitlementDirectory()
        inj.provide(inj.ENT_DIR, self.ent_dir)
        self.prod_dir = stubs.StubProductDirectory()
        inj.provide(inj.PROD_DIR, self.prod_dir)

        self.dbus_patcher = patch('subscription_manager.managercli.CliCommand._request_validity_check')
        self.dbus_patcher.start()

    def tearDown(self):
        self.dbus_patcher.stop()

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
