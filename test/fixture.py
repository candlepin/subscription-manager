from __future__ import print_function, division, absolute_import

import difflib
import locale
import os
import pprint
import six
import sys
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest


# just log py.warnings (and pygtk warnings in particular)
import logging
try:
    # 2.7+
    logging.captureWarnings(True)
except AttributeError:
    pass

from mock import Mock, MagicMock, NonCallableMock, patch, mock_open
from contextlib import contextmanager

from . import stubs
import subscription_manager.injection as inj
import subscription_manager.managercli
from rhsmlib.services import config

# use instead of the normal pid file based ActionLock
from threading import RLock

if six.PY2:
    OPEN_FUNCTION = '__builtin__.open'
else:
    OPEN_FUNCTION = 'builtins.open'


@contextmanager
def open_mock(content=None, **kwargs):
    content_out = six.StringIO()
    m = mock_open(read_data=content)
    with patch(OPEN_FUNCTION, m, create=True, **kwargs) as mo:
        stream = six.StringIO(content)
        rv = mo.return_value
        rv.write = lambda x: content_out.write(x)
        rv.content_out = lambda: content_out.getvalue()
        rv.__iter__ = lambda x: iter(stream.readlines())
        yield rv


@contextmanager
def temp_file(content, *args, **kwargs):
    try:
        kwargs['delete'] = False
        kwargs.setdefault('prefix', 'sub-man-test')
        fh = tempfile.NamedTemporaryFile(mode='w+', *args, **kwargs)
        fh.write(content)
        fh.close()
        yield fh.name
    finally:
        os.unlink(fh.name)


@contextmanager
def locale_context(new_locale, category=None):
    old_category = category or locale.LC_CTYPE
    old_locale = locale.getlocale(old_category)
    category = category or locale.LC_ALL
    locale.setlocale(category, new_locale)
    try:
        yield
    finally:
        locale.setlocale(category, old_locale)


class FakeLogger(object):
    def __init__(self):
        self.expected_msg = ""
        self.msg = None
        self.logged_exception = None

    def debug(self, buf, *args, **kwargs):
        self.msg = buf

    def error(self, buf, *args, **kwargs):
        self.msg = buf

    def exception(self, e, *args, **kwargs):
        self.logged_exception = e

    def set_expected_msg(self, msg):
        self.expected_msg = msg

    def info(self, buf, *args, **kwargs):
        self.msg = buf

    def warning(self, buf, *args, **kwargs):
        self.msg = buf


class FakeException(Exception):
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class Matcher(object):
    @staticmethod
    def set_eq(first, second):
        """Useful for dealing with sets that have been cast to or instantiated as lists."""
        return set(first) == set(second)

    def __init__(self, compare, some_obj):
        self.compare = compare
        self.some_obj = some_obj

    def __eq__(self, other):
        return self.compare(self.some_obj, other)


class SubManFixture(unittest.TestCase):
    def set_facts(self):
        """Override if you need to set facts for a test."""
        return {"mock.facts": "true"}

    """
    Can be extended by any subscription manager test case to make
    sure nothing on the actual system is read/touched, and appropriate
    mocks/stubs are in place.
    """
    def setUp(self):
        # No matter what, stop all patching (even if we have a failure in setUp itself)
        self.addCleanup(patch.stopall)

        # Never attempt to use the actual managercli.cfg which points to a
        # real file in etc.

        self.mock_cfg_parser = stubs.StubConfig()

        original_conf = subscription_manager.managercli.conf

        def unstub_conf():
            subscription_manager.managercli.conf = original_conf

        # Mock makes it damn near impossible to mock a module attribute (which we shouldn't be using
        # in the first place because it's terrible) so we monkey-patch it ourselves.
        # TODO Fix this idiocy by not reading the damn config on module import
        subscription_manager.managercli.conf = config.Config(self.mock_cfg_parser)
        self.addCleanup(unstub_conf)

        facts_host_patcher = patch('rhsmlib.dbus.facts.FactsClient', auto_spec=True)
        self.mock_facts_host = facts_host_patcher.start()
        self.mock_facts_host.return_value.GetFacts.return_value = self.set_facts()

        # By default mock that we are registered. Individual test cases
        # can override if they are testing disconnected scenario.
        id_mock = NonCallableMock(name='FixtureIdentityMock')
        id_mock.exists_and_valid = Mock(return_value=True)
        id_mock.uuid = 'fixture_identity_mock_uuid'
        id_mock.name = 'fixture_identity_mock_name'
        id_mock.cert_dir_path = "/not/a/real/path/to/pki/consumer/"
        id_mock.keypath.return_value = "/not/a/real/key/path"
        id_mock.certpath.return_value = "/not/a/real/cert/path"

        # Don't really care about date ranges here:
        self.mock_calc = NonCallableMock()
        self.mock_calc.calculate.return_value = None

        # Avoid trying to read real /etc/yum.repos.d/redhat.repo
        self.mock_repofile_path_exists_patcher = patch('subscription_manager.repolib.YumRepoFile.path_exists')
        mock_repofile_path_exists = self.mock_repofile_path_exists_patcher.start()
        mock_repofile_path_exists.return_value = True

        inj.provide(inj.IDENTITY, id_mock)
        inj.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR, self.mock_calc)

        inj.provide(inj.ENTITLEMENT_STATUS_CACHE, stubs.StubEntitlementStatusCache())
        inj.provide(inj.POOL_STATUS_CACHE, stubs.StubPoolStatusCache())
        inj.provide(inj.PROD_STATUS_CACHE, stubs.StubProductStatusCache())
        inj.provide(inj.OVERRIDE_STATUS_CACHE, stubs.StubOverrideStatusCache())
        inj.provide(inj.RELEASE_STATUS_CACHE, stubs.StubReleaseStatusCache())
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
        self._release_versions = []
        self.stub_cp_provider.content_connection.get_versions = self._get_release_versions

        inj.provide(inj.CP_PROVIDER, self.stub_cp_provider)
        inj.provide(inj.CERT_SORTER, stubs.StubCertSorter())

        # setup and mock the plugin_manager
        plugin_manager_mock = MagicMock(name='FixturePluginManagerMock')
        plugin_manager_mock.runiter.return_value = iter([])
        inj.provide(inj.PLUGIN_MANAGER, plugin_manager_mock)
        inj.provide(inj.DBUS_IFACE, Mock(name='FixtureDbusIfaceMock'))

        pooltype_cache = Mock()
        inj.provide(inj.POOLTYPE_CACHE, pooltype_cache)
        # don't use file based locks for tests
        inj.provide(inj.ACTION_LOCK, RLock)

        self.stub_facts = stubs.StubFacts()
        inj.provide(inj.FACTS, self.stub_facts)

        content_access_cache_mock = MagicMock(name='ContentAccessCacheMock')
        inj.provide(inj.CONTENT_ACCESS_CACHE, content_access_cache_mock)

        self.dbus_patcher = patch('subscription_manager.managercli.CliCommand._request_validity_check')
        self.dbus_patcher.start()

        # No tests should be trying to connect to any configure or test server
        # so really, everything needs this mock. May need to be in __init__, or
        # better, all test classes need to use SubManFixture
        self.is_valid_server_patcher = patch("subscription_manager.managercli.is_valid_server_info")
        is_valid_server_mock = self.is_valid_server_patcher.start()
        is_valid_server_mock.return_value = True

        # No tests should be trying to test the proxy connection
        # so really, everything needs this mock. May need to be in __init__, or
        # better, all test classes need to use SubManFixture
        self.test_proxy_connection_patcher = patch("subscription_manager.managercli.CliCommand.test_proxy_connection")
        test_proxy_connection_mock = self.test_proxy_connection_patcher.start()
        test_proxy_connection_mock.return_value = True

        self.syncedstore_patcher = patch('subscription_manager.syspurposelib.SyncedStore')
        syncedstore_mock = self.syncedstore_patcher.start()

        set_up_mock_sp_store(syncedstore_mock)

        self.files_to_cleanup = []

    def tearDown(self):
        if not hasattr(self, 'files_to_cleanup'):
            return
        for f in self.files_to_cleanup:
            # Assuming these are tempfile.NamedTemporaryFile, created with
            # the write_tempfile() method in this class.
            f.close()

    def write_tempfile(self, contents):
        """
        Write out a tempfile and append it to the list of those to be
        cleaned up in tearDown.
        """
        fid = tempfile.NamedTemporaryFile(mode='w+', suffix='.tmp')
        fid.write(contents)
        fid.seek(0)
        self.files_to_cleanup.append(fid)
        return fid

    def set_consumer_auth_cp(self, consumer_auth_cp):
        cp_provider = inj.require(inj.CP_PROVIDER)
        cp_provider.consumer_auth_cp = consumer_auth_cp

    def get_consumer_cp(self):
        cp_provider = inj.require(inj.CP_PROVIDER)
        consumer_cp = cp_provider.get_consumer_auth_cp()
        return consumer_cp

    # The ContentConnection used for reading release versions from
    # the cdn. The injected one uses this.
    def _get_release_versions(self, listing_path, ent_cert_key_pairs):
        return self._release_versions

    # For changing injection consumer id to one that fails "is_valid"
    def _inject_mock_valid_consumer(self, uuid=None):
        """For changing injected consumer identity to one that passes is_valid()

        Returns the injected identity if it need to be examined.
        """
        identity = NonCallableMock(name='ValidIdentityMock')
        identity.uuid = uuid or "VALIDCONSUMERUUID"
        identity.is_valid = Mock(return_value=True)
        identity.cert_dir_path = "/not/a/real/path/to/pki/consumer/"
        inj.provide(inj.IDENTITY, identity)
        return identity

    def _inject_mock_invalid_consumer(self, uuid=None):
        """For chaining injected consumer identity to one that fails is_valid()

        Returns the injected identity if it need to be examined.
        """
        invalid_identity = NonCallableMock(name='InvalidIdentityMock')
        invalid_identity.is_valid = Mock(return_value=False)
        invalid_identity.uuid = uuid or "INVALIDCONSUMERUUID"
        invalid_identity.cert_dir_path = "/not/a/real/path/to/pki/consumer/"
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
        if sorted(a, key=lambda item: str(item)) != sorted(b, key=lambda item: str(item)):
            self.fail("%s != %s" % (a, b))
        return True


class Capture(object):
    class Tee(object):
        def __init__(self, stream, silent):
            self.buf = six.StringIO()
            self.stream = stream
            self.silent = silent

        def write(self, data):
            self.buf.write(data)
            if not self.silent:
                self.stream.write(data)

        def flush(self):
            pass

        def getvalue(self):
            return self.buf.getvalue()

        def isatty(self):
            return False

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


def set_up_mock_sp_store(mock_sp_store):
    """
    Sets up the mock syspurpose store with methods that are mock versions of the real deal.
    Allows us to test in the absence of the syspurpose module.
    This documents the essential expected behaviour of the methods subman relies upon
    from the syspurpose codebase.
    :return:
    """
    contents = {}
    mock_sp_store_contents = contents

    def set(item, value):
        contents[item] = value

    def read(path, raise_on_error=False):
        return mock_sp_store

    def unset(item):
        contents[item] = None

    def add(item, value):
        current = contents.get(item, [])
        if value not in current:
            current.append(value)
        contents[item] = current

    def remove(item, value):
        current = contents.get(item)
        if current is not None and isinstance(current, list) and value in current:
            current.remove(value)

    def get_local_contents():
        return contents

    def update_local(data):
        global contents
        contents = data

    mock_sp_store.return_value.set = Mock(side_effect=set)
    mock_sp_store.return_value.read = Mock(side_effect=read)
    mock_sp_store.return_value.unset = Mock(side_effect=unset)
    mock_sp_store.return_value.add = Mock(side_effect=add)
    mock_sp_store.return_value.remove = Mock(side_effect=remove)
    mock_sp_store.return_value.local_contents = mock_sp_store_contents
    mock_sp_store.return_value.get_local_contents = Mock(side_effect=get_local_contents)
    mock_sp_store.return_value.update_local = Mock(side_effect=update_local)

    return mock_sp_store, mock_sp_store_contents
