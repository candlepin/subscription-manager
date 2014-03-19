import difflib
import pprint
import unittest
import sys
import StringIO

from mock import Mock, NonCallableMock, patch

import stubs
import subscription_manager.injection as inj

# use instead of the normal pid file based ActionLock
from threading import RLock


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
        id_mock = Mock(name='FixtureIdentityMock')
        id_mock.exists_and_valid = Mock(return_value=True)

        # Don't really care about date ranges here:
        self.mock_calc = NonCallableMock()
        self.mock_calc.calculate.return_value = None

        inj.provide(inj.IDENTITY, id_mock)
        inj.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR, self.mock_calc)

        inj.provide(inj.ENTITLEMENT_STATUS_CACHE, stubs.StubEntitlementStatusCache())
        inj.provide(inj.PROD_STATUS_CACHE, stubs.StubProductStatusCache())
        inj.provide(inj.OVERRIDE_STATUS_CACHE, stubs.StubOverrideStatusCache())
        inj.provide(inj.PROFILE_MANAGER, stubs.StubProfileManager())
        # By default set up an empty stub entitlement and product dir.
        # Tests need to modify or create their own but nothing should hit
        # the system.
        self.ent_dir = stubs.StubEntitlementDirectory()
        inj.provide(inj.ENT_DIR, self.ent_dir)
        self.prod_dir = stubs.StubProductDirectory()
        inj.provide(inj.PROD_DIR, self.prod_dir)

        # Installed products manager needs PROD_DIR injected first
        inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, stubs.StubInstalledProductsManager())

        self.stub_cp_provider = stubs.StubCPProvider()
        inj.provide(inj.CP_PROVIDER, self.stub_cp_provider)
        inj.provide(inj.CERT_SORTER, stubs.StubCertSorter())

        # setup and mock the plugin_manager
        plugin_manager_mock = Mock(name='FixturePluginManagerMock')
        inj.provide(inj.PLUGIN_MANAGER, plugin_manager_mock)
        inj.provide(inj.DBUS_IFACE, Mock(name='FixtureDbusIfaceMock'))

        pooltype_cache = Mock()
        inj.provide(inj.POOLTYPE_CACHE, pooltype_cache)
        # don't use file based locks for tests
        inj.provide(inj.ACTION_LOCK, RLock)

        inj.provide(inj.FACTS, stubs.StubFacts())

        self.dbus_patcher = patch('subscription_manager.managercli.CliCommand._request_validity_check')
        self.dbus_patcher.start()

    def tearDown(self):
        self.dbus_patcher.stop()

    def get_consumer_cp(self):
        cp_provider = inj.require(inj.CP_PROVIDER)
        consumer_cp = cp_provider.get_consumer_auth_cp()
        return consumer_cp

    # For changing injection consumer id to one that fails "is_valid"
    def _inject_mock_valid_consumer(self, uuid=None):
        """For changing injected consumer identity to one that passes is_valid()

        Returns the injected identity if it need to be examined.
        """
        identity = NonCallableMock(name='ValidIdentityMock')
        identity.uuid = uuid or "VALIDCONSUMERUUID"
        identity.is_valid = Mock(return_value=True)
        inj.provide(inj.IDENTITY, identity)
        return identity

    def _inject_mock_invalid_consumer(self, uuid=None):
        """For chaning injected consumer identity to one that fails is_valid()

        Returns the injected identity if it need to be examined.
        """
        invalid_identity = NonCallableMock(name='InvalidIdentityMock')
        invalid_identity.is_valid = Mock(return_value=False)
        invalid_identity.uuid = uuid or "INVALIDCONSUMERUUID"
        inj.provide(inj.IDENTITY, invalid_identity)
        return invalid_identity

    # use our naming convention here to make it clear
    # this is our extension. Note that python 2.7 adds a
    # assertMultilineEquals that assertEqual of strings does
    # automatically
    def assert_string_equals(self, expected_str, actual_str, msg=None):
        if expected_str != actual_str:
            expected_lines = expected_str.splitlines(True)
            actual_lines = actual_str.splitlines(True)
            delta = difflib.unified_diff(expected_lines, actual_lines, "expected", "actual")
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

    def assert_items_equals(self, a, b):
        """Assert that two lists contain the same items regardless of order."""
        if sorted(a) != sorted(b):
            self.fail("%s != %s" % (a, b))
        return True


class Capture(object):
    class Tee(object):
        def __init__(self, stream, silent):
            self.buf = StringIO.StringIO()
            self.stream = stream
            self.silent = silent

        def write(self, data):
            self.buf.write(data)
            if not self.silent:
                self.stream.write(data)

        def getvalue(self):
            return self.buf.getvalue()

    def __init__(self, silent=False):
        self.silent = silent

    def __enter__(self):
        self.buffs = (self.Tee(sys.stdout, self.silent), self.Tee(sys.stderr, self.silent))
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout, sys.stderr = self.buffs
        return self

    @property
    def out(self):
        return self.buffs[0].getvalue()

    @property
    def err(self):
        return self.buffs[1].getvalue()

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
