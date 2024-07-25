# Copyright (c) 2010, 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import os
import unittest

import io
import re
from importlib import reload
from . import fixture

from iniparse import RawConfigParser, SafeConfigParser
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
from iniparse import ConfigParser

import rhsm.connection
from subscription_manager import repofile

# repofile must be patched and reloaded to import AptRepofile, otherwise
# the class is not defined in the first place
deb_mock = MagicMock()
deb_mock.Deb822 = dict
with patch.dict("subscription_manager.repofile.sys.modules", {"debian.deb822": deb_mock}):
    reload(repofile)
    from subscription_manager.repofile import AptRepoFile
reload(repofile)

from .stubs import (
    StubProductCertificate,
    StubProduct,
    StubEntitlementCertificate,
    StubContent,
    StubProductDirectory,
    StubConsumerIdentity,
    StubEntitlementDirectory,
    StubDeb822,
)
from subscription_manager.repolib import (
    RepoActionInvoker,
    RepoUpdateActionCommand,
    YumReleaseverSource,
    YumPluginManager,
)
from subscription_manager.repofile import Repo, TidyWriter, YumRepoFile
from subscription_manager import injection as inj
from rhsm.config import RhsmConfigParser
from rhsmlib.services import config

from subscription_manager import repolib
from subscription_manager.entcertlib import CONTENT_ACCESS_CERT_TYPE


# always pretend to run tests with yum in order to have 'ui_repoid_vars' available
repofile.HAS_YUM = True


class ConfigFromString(config.Config):
    def __init__(self, config_string):
        parser = RhsmConfigParserFromString(config_string)
        super(ConfigFromString, self).__init__(parser)


class RhsmConfigParserFromString(RhsmConfigParser):
    def __init__(self, config_string):
        SafeConfigParser.__init__(self)
        self.stringio = io.StringIO(config_string)
        self.readfp(self.stringio)


class TestRepoActionInvoker(fixture.SubManFixture):
    def _stub_content(self, include_content_access=False):
        stub_prod = StubProduct("stub_product", provided_tags="stub-product")

        stub_content = StubContent("a_test_repo", required_tags="stub-product")

        stub_content2 = StubContent("test_repo_2", required_tags="stub-product")

        stub_ent_cert = StubEntitlementCertificate(stub_prod, content=[stub_content])
        stub_prod_cert = StubProductCertificate(stub_prod)

        certs = [stub_ent_cert]
        if include_content_access:
            self.stub_content_access_cert = StubEntitlementCertificate(
                stub_prod, content=[stub_content, stub_content2], entitlement_type=CONTENT_ACCESS_CERT_TYPE
            )
            # content access cert is first and last, so naively wrong implementations will prioritize it.
            certs = [self.stub_content_access_cert, stub_ent_cert, self.stub_content_access_cert]
        stub_ent_dir = StubEntitlementDirectory(certs)
        stub_prod_dir = StubProductDirectory([stub_prod_cert])

        inj.provide(inj.ENT_DIR, stub_ent_dir)
        inj.provide(inj.PROD_DIR, stub_prod_dir)

    def test_is_managed(self):
        self._stub_content()
        repo_action_invoker = RepoActionInvoker()
        repo_label = "a_test_repo"

        im_result = repo_action_invoker.is_managed(repo_label)

        self.assertTrue(im_result)

    def test_get_repo_file(self):
        repo_action_invoker = RepoActionInvoker()

        repo_file = repo_action_invoker.get_repo_file()
        self.assertFalse(repo_file is None)

    def test_get_repos_empty_dirs(self):
        repo_action_invoker = RepoActionInvoker()
        repos = repo_action_invoker.get_repos()
        if repos:
            self.fail("get_repos() should have returned an empty set but did not.")

    def test_get_repos(self):
        self._stub_content(include_content_access=True)
        repo_action_invoker = RepoActionInvoker()
        repos = repo_action_invoker.get_repos()
        self.assertEqual(2, len(repos), "Should produce two repos")
        matching_repos = [repo for repo in repos if repo.id == "a_test_repo"]
        self.assertEqual(1, len(matching_repos), 'Should only produce one repo for "a_test_repo"')
        repo = matching_repos[0]
        certpath = repo.get("sslclientcert")
        self.assertNotEqual(certpath, self.stub_content_access_cert.path)


PROXY_NO_PROTOCOL = """
[server]
proxy_hostname = fake.server.com
proxy_port = 3129
"""

PROXY_EMPTY_PROTOCOL = """
[server]
proxy_hostname = fake.server.com
proxy_port = 3129
proxy_scheme =
"""

PROXY_HTTP_PROTOCOL = """
[server]
proxy_hostname = fake.server.com
proxy_scheme = http
proxy_port = 3129
"""

PROXY_HTTPS_PROTOCOL = """
[server]
proxy_hostname = fake.server.com
proxy_scheme = https
proxy_port = 3129
"""

PROXY_EXTRA_SCHEME = """
[server]
proxy_hostname = fake.server.com
proxy_scheme = https://
proxy_port = 3129
"""


class RepoTests(unittest.TestCase):
    """
    Tests for the repolib Repo class
    """

    def test_valid_label_for_id(self):
        repo_id = "valid-label"
        repo = Repo(repo_id)
        self.assertEqual(repo_id, repo.id)

    def test_valid_unicode_just_ascii_label_for_id(self):
        repo_id = "valid-label"
        repo = Repo(repo_id)
        self.assertEqual(repo_id, repo.id)

    def test_invalid_unicode_label_for_id(self):
        repo_id = "valid-不明-label"
        repo = Repo(repo_id)
        expected = "valid----label"
        self.assertEqual(expected, repo.id)

    def test_invalid_label_with_spaces(self):
        repo_id = "label with spaces"
        repo = Repo(repo_id)
        self.assertEqual("label-with-spaces", repo.id)

    def test_existing_order_is_preserved(self):
        config = (("key 1", "value 1"), ("key b", "value b"), ("key 3", "value 3"))
        repo = Repo("testrepo", config)
        self.assertEqual(config, tuple(repo.items())[:3])

    def test_empty_strings_not_set_in_file(self):
        r = Repo("testrepo", (("proxy", ""),))
        r["proxy"] = ""
        self.assertFalse(("proxy", "") in list(r.items()))

    def test_unknown_property_is_preserved(self):
        existing_repo = Repo("testrepo")
        existing_repo["fake_prop"] = "fake"
        self.assertTrue(("fake_prop", "fake") in list(existing_repo.items()))

    @patch.object(repofile, "conf", ConfigFromString(config_string=PROXY_NO_PROTOCOL))
    def test_http_by_default(self):
        repo = Repo("testrepo")
        r = Repo._set_proxy_info(repo)
        self.assertEqual(r["proxy"], "http://fake.server.com:3129")

    @patch.object(repofile, "conf", ConfigFromString(config_string=PROXY_EMPTY_PROTOCOL))
    def test_http_by_empty(self):
        repo = Repo("testrepo")
        r = Repo._set_proxy_info(repo)
        self.assertEqual(r["proxy"], "http://fake.server.com:3129")

    @patch.object(repofile, "conf", ConfigFromString(config_string=PROXY_HTTP_PROTOCOL))
    def test_http(self):
        repo = Repo("testrepo")
        r = Repo._set_proxy_info(repo)
        self.assertEqual(r["proxy"], "http://fake.server.com:3129")

    @patch.object(repofile, "conf", ConfigFromString(config_string=PROXY_HTTPS_PROTOCOL))
    def test_https(self):
        repo = Repo("testrepo")
        r = Repo._set_proxy_info(repo)
        self.assertEqual(r["proxy"], "https://fake.server.com:3129")

    @patch.object(repofile, "conf", ConfigFromString(config_string=PROXY_EXTRA_SCHEME))
    def test_extra_chars_in_scheme(self):
        repo = Repo("testrepo")
        r = Repo._set_proxy_info(repo)
        self.assertEqual(r["proxy"], "https://fake.server.com:3129")


class RepoActionReportTests(fixture.SubManFixture):
    def test(self):
        report = repolib.RepoActionReport()
        repo = self._repo("a-unicode-content-label", "A unicode repo name")
        report.repo_updates.append(repo)
        report.repo_added.append(repo)
        deleted_section = "einige-repo-name"
        deleted_section_2 = "一些回購名稱"
        report.repo_deleted = [deleted_section, deleted_section_2]

        str(report)

        with fixture.locale_context("de_DE.utf8"):
            str(report)

    def _repo(self, id, name):
        repo = repolib.Repo(repo_id=id)
        repo["name"] = name
        return repo

    def test_empty(self):
        report = repolib.RepoActionReport()
        self.assertEqual(report.updates(), 0)
        "%s" % report
        str(report)

    def test_format(self):
        report = repolib.RepoActionReport()
        repo = self._repo("a-repo-label", "A Repo Name")
        report.repo_updates.append(repo)
        res = str(report)
        # needs tests run in eng locale, coupled to report format since
        # I managed to typo them
        report_label_regexes = [
            "^Repo updates$",
            "^Total repo updates:",
            "^Updated$",
            r"^Added \(new\)$",
            "^Deleted$",
        ]
        for report_label_regex in report_label_regexes:
            if not re.search(report_label_regex, res, re.MULTILINE):
                self.fail("Expected to match the report label regex  %s but did not" % report_label_regex)


class RepoUpdateActionTests(fixture.SubManFixture):
    def setUp(self):
        super(RepoUpdateActionTests, self).setUp()
        stub_prod = StubProduct("fauxprod", provided_tags="TAG1,TAG2")
        stub_prod2 = StubProduct("fauxprovidedprod", provided_tags="TAG4")
        stub_prod_cert = StubProductCertificate(stub_prod, provided_products=[stub_prod2])
        stub_prod2 = StubProduct("fauxprod2", provided_tags="TAG5,TAG6")
        stub_prod2_cert = StubProductCertificate(stub_prod2)
        prod_dir = StubProductDirectory([stub_prod_cert, stub_prod2_cert])
        inj.provide(inj.PROD_DIR, prod_dir)

        stub_content = [
            StubContent("c1", required_tags="", gpg=None),  # no required tags
            StubContent("c2", required_tags="TAG1", gpg=""),
            StubContent("c3", required_tags="TAG1,TAG2,TAG3"),  # should get skipped
            StubContent("c4", required_tags="TAG1,TAG2,TAG4,TAG5,TAG6", gpg="/gpg.key", url="/$some/$path"),
            StubContent("c5", content_type="file", required_tags="", gpg=None),
            StubContent("c6", content_type="file", required_tags="", gpg=None),
        ]
        self.stub_ent_cert = StubEntitlementCertificate(stub_prod, content=stub_content)
        ent_dir = StubEntitlementDirectory([self.stub_ent_cert])
        inj.provide(inj.ENT_DIR, ent_dir)

        repolib.ConsumerIdentity = StubConsumerIdentity

    def _find_content(self, content_list, name):
        """
        Scan list of content for one with name.
        """
        for content in content_list:
            if content["name"] == name:
                return content
        return None

    def test_override_cache_update_skipped_when_overrides_not_supported_on_server(self):
        inj.provide(inj.OVERRIDE_STATUS_CACHE, Mock())
        override_cache_mock = inj.require(inj.OVERRIDE_STATUS_CACHE)

        mock_uep = Mock()
        mock_uep.supports_resource = Mock(return_value=False)
        mock_uep.get_supported_resources = Mock(return_value=[])
        mock_uep.getCertificates = Mock(return_value=[])
        mock_uep.getCertificateSerials = Mock(return_value=[])
        mock_uep.getRelease = Mock(return_value={"releaseVer": "dummyrelease"})

        self.set_consumer_auth_cp(mock_uep)

        RepoUpdateActionCommand()

        # No cache calls should be made if overrides are not supported
        self.assertFalse(override_cache_mock.read_cache.called)
        self.assertFalse(override_cache_mock.load_status.called)

    def test_overrides_trump_ent_cert(self):
        update_action = RepoUpdateActionCommand()
        update_action.overrides = {"x": {"gpgcheck": "blah"}}
        r = Repo("x", [("gpgcheck", "original"), ("gpgkey", "some_key")])
        self.assertEqual("original", r["gpgcheck"])
        update_action._set_override_info(r)
        self.assertEqual("blah", r["gpgcheck"])
        self.assertEqual("some_key", r["gpgkey"])

    def test_overrides_trump_existing(self):
        update_action = RepoUpdateActionCommand()
        update_action.overrides = {"x": {"gpgcheck": "blah"}}
        values = [("gpgcheck", "original"), ("gpgkey", "some_key")]
        old_repo = Repo("x", values)
        new_repo = Repo(old_repo.id, values)
        update_action._set_override_info(new_repo)
        self.assertEqual("original", old_repo["gpgcheck"])
        update_action.update_repo(old_repo, new_repo)
        self.assertEqual("blah", old_repo["gpgcheck"])
        self.assertEqual("some_key", old_repo["gpgkey"])

    @patch("subscription_manager.repolib.get_repo_file_classes")
    def test_update_when_new_repo(self, mock_get_repo_file_classes):
        mock_file = MagicMock()
        mock_file.CONTENT_TYPES = [None]
        mock_file.fix_content = lambda x: x
        mock_file.section.return_value = None
        mock_class = MagicMock(return_value=mock_file)
        mock_get_repo_file_classes.return_value = [(mock_class, mock_class)]

        def stub_content():
            return [Repo("x", [("gpgcheck", "original"), ("gpgkey", "some_key")])]

        update_action = RepoUpdateActionCommand()
        update_action.get_unique_content = stub_content
        update_report = update_action.perform()
        written_repo = mock_file.add.call_args[0][0]
        self.assertEqual("original", written_repo["gpgcheck"])
        self.assertEqual("some_key", written_repo["gpgkey"])
        self.assertEqual(1, update_report.updates())

    @patch("subscription_manager.repolib.get_repo_file_classes")
    def test_update_when_repo_not_modified_on_mutable(self, mock_get_repo_file_classes):
        self._inject_mock_invalid_consumer()
        modified_repo = Repo("x", [("gpgcheck", "original"), ("gpgkey", "some_key")])
        server_repo = Repo("x", [("gpgcheck", "original")])
        mock_file = MagicMock()
        mock_file.CONTENT_TYPES = [None]
        mock_file.fix_content = lambda x: x
        mock_file.section.side_effect = [modified_repo, server_repo]
        mock_class = MagicMock(return_value=mock_file)
        mock_get_repo_file_classes.return_value = [(mock_class, mock_class)]

        def stub_content():
            return [Repo("x", [("gpgcheck", "new"), ("gpgkey", "new_key"), ("name", "test")])]

        update_action = RepoUpdateActionCommand()
        update_action.get_unique_content = stub_content
        current = update_action.perform()
        # confirming that the assessed value does change when repo file
        # is the same as the server value file.
        self.assertEqual("new", current.repo_updates[0]["gpgcheck"])

        # this is the ending server value file.
        written_repo = mock_file.update.call_args[0][0]
        self.assertEqual("new", written_repo["gpgcheck"])
        self.assertEqual(None, written_repo["gpgkey"])

    @patch("subscription_manager.repolib.get_repo_file_classes")
    def test_update_when_repo_modified_on_mutable(self, mock_get_repo_file_classes):
        self._inject_mock_invalid_consumer()
        modified_repo = Repo("x", [("gpgcheck", "unoriginal"), ("gpgkey", "some_key")])
        server_repo = Repo("x", [("gpgcheck", "original")])
        mock_file = MagicMock()
        mock_file.CONTENT_TYPES = [None]
        mock_file.fix_content = lambda x: x
        mock_file.section.side_effect = [modified_repo, server_repo]
        mock_class = MagicMock(return_value=mock_file)
        mock_get_repo_file_classes.return_value = [(mock_class, mock_class)]

        def stub_content():
            return [Repo("x", [("gpgcheck", "new"), ("gpgkey", "new_key"), ("name", "test")])]

        update_action = RepoUpdateActionCommand()
        update_action.get_unique_content = stub_content
        current = update_action.perform()
        # confirming that the assessed value does not change when repo file
        # is different from the server value file.
        self.assertEqual("unoriginal", current.repo_updates[0]["gpgcheck"])

        # this is the ending server value file
        written_repo = mock_file.update.call_args[0][0]
        self.assertEqual("new", written_repo["gpgcheck"])
        self.assertEqual(None, written_repo["gpgkey"])

    def test_no_gpg_key(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c1 = self._find_content(content, "c1")
        self.assertEqual("", c1["gpgkey"])
        self.assertEqual("0", c1["gpgcheck"])

        c2 = self._find_content(content, "c2")
        self.assertEqual("", c2["gpgkey"])
        self.assertEqual("0", c2["gpgcheck"])

    def test_gpg_key(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c4 = self._find_content(content, "c4")
        self.assertEqual("http://example.com/gpg.key", c4["gpgkey"])
        self.assertEqual("1", c4["gpgcheck"])

    def test_ui_repoid_vars(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c4 = self._find_content(content, "c4")
        self.assertEqual("some path", c4["ui_repoid_vars"])
        c2 = self._find_content(content, "c2")
        self.assertEqual(None, c2["ui_repoid_vars"])

    def test_tags_found(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_unique_content()
        self.assertEqual(3, len(content))

    def test_only_allow_content_of_type_yum(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        self.assertTrue(self._find_content(content, "c1") is not None)
        self.assertTrue(self._find_content(content, "c5") is None)
        self.assertTrue(self._find_content(content, "c6") is None)

    def test_mutable_property(self):
        update_action = RepoUpdateActionCommand()
        self._inject_mock_invalid_consumer()
        existing_repo = Repo("testrepo")
        existing_repo["metadata_expire"] = 1000
        incoming_repo = {"metadata_expire": 2000}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo["metadata_expire"])

    def test_mutable_property_is_server(self):
        update_action = RepoUpdateActionCommand()
        self._inject_mock_invalid_consumer()
        existing_repo = Repo("testrepo")
        server_val_repo = Repo("servertestrepo")
        existing_repo["metadata_expire"] = 1000
        server_val_repo["metadata_expire"] = 1000
        incoming_repo = {"metadata_expire": 2000}
        update_action.update_repo(existing_repo, incoming_repo, server_val_repo)
        self.assertEqual(2000, existing_repo["metadata_expire"])

    def test_gpgcheck_is_mutable(self):
        update_action = RepoUpdateActionCommand()
        self._inject_mock_invalid_consumer()
        existing_repo = Repo("testrepo")
        existing_repo["gpgcheck"] = "0"
        incoming_repo = {"gpgcheck": "1"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("0", existing_repo["gpgcheck"])

    def test_mutable_property_in_repo_but_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["metadata_expire"] = 1000
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo["metadata_expire"])

    def test_immutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["name"] = "meow"
        incoming_repo = {"name": "woof"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo["name"])

    # If the user removed a mutable property completely, or the property
    # is new in a new version of the entitlement certificate, the new value
    # should get written out.
    def test_unset_mutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        incoming_repo = {"metadata_expire": 2000}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(2000, existing_repo["metadata_expire"])

    def test_unset_immutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        incoming_repo = {"name": "woof"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo["name"])

    # Test repo on disk has an immutable property set which has since been
    # unset in the new repo definition. This property should be removed.
    def test_set_immutable_property_now_empty(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["proxy_username"] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertFalse("proxy_username" in list(existing_repo.keys()))

    def test_set_mutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["metadata_expire"] = "blah"
        incoming_repo = {"metadata_expire": ""}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in list(existing_repo.keys()))

    def test_set_custom_property_removed(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["exclude"] = "1"
        # 'exclude' is not in the updated repo listing.
        # this is how an override delete is passed into
        # the update method
        incoming_repo = Repo("testrepo")
        update_action.update_repo(existing_repo, incoming_repo, existing_repo)
        self.assertFalse("exclude" in list(existing_repo.keys()))

    def test_set_immutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["proxy_username"] = "blah"
        incoming_repo = {"proxy_username": ""}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in list(existing_repo.keys()))

    def test_set_mutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["metadata_expire"] = "blah"
        incoming_repo = {"metadata_expire": None}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in list(existing_repo.keys()))

    def test_set_mutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["metadata_expire"] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in list(existing_repo.keys()))

    def test_set_immutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["proxy_username"] = "blah"
        incoming_repo = {"proxy_username": None}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in list(existing_repo.keys()))

    def test_set_immutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo("testrepo")
        existing_repo["proxy_username"] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in list(existing_repo.keys()))

    def test_overrides_removed_revert_to_default(self):
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {"x": {"gpgcheck": "blah"}}
        update_action.overrides = {}
        old_repo = Repo("x", [("gpgcheck", "blah"), ("gpgkey", "some_key")])
        new_repo = Repo(old_repo.id, [("gpgcheck", "original"), ("gpgkey", "some_key")])
        update_action._set_override_info(new_repo)
        # The value from the current repo file (with the old override) should exist pre-update
        self.assertEqual("blah", old_repo["gpgcheck"])
        update_action.update_repo(old_repo, new_repo)
        # Because the override has been removed, the value is reset to the default
        self.assertEqual("original", old_repo["gpgcheck"])
        self.assertEqual("some_key", old_repo["gpgkey"])

    def test_overrides_removed_and_edited(self):
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {"x": {"gpgcheck": "override_value"}}
        update_action.overrides = {}
        old_repo = Repo("x", [("gpgcheck", "hand_edit"), ("gpgkey", "some_key")])
        new_repo = Repo(old_repo.id, [("gpgcheck", "original"), ("gpgkey", "some_key")])
        update_action._set_override_info(new_repo)
        # The value from the current repo file (with the old hand edit) should exist pre-update
        self.assertEqual("hand_edit", old_repo["gpgcheck"])
        update_action.update_repo(old_repo, new_repo)
        # Because the current value doesn't match the override, we don't modify it
        self.assertEqual("hand_edit", old_repo["gpgcheck"])
        self.assertEqual("some_key", old_repo["gpgkey"])

    def test_non_default_overrides_added_to_existing(self):
        """
        Test that overrides for values that aren't found in Repo.PROPERTIES are written
        to existing repos
        """
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {}
        update_action.overrides = {"x": {"somekey": "someval"}}
        old_repo = Repo("x", [])
        new_repo = Repo(old_repo.id, [])
        update_action._set_override_info(new_repo)
        update_action.update_repo(old_repo, new_repo)
        self.assertEqual("someval", old_repo["somekey"])

    def test_non_default_override_removed_deleted(self):
        """
        Test that overrides for values that aren't found in Repo.PROPERTIES are
        removed from redhat.repo once the override is removed
        """
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {"x": {"somekey": "someval"}}
        update_action.overrides = {}
        old_repo = Repo("x", [("somekey", "someval")])
        new_repo = Repo(old_repo.id, [])
        update_action._set_override_info(new_repo)
        update_action.update_repo(old_repo, new_repo)
        self.assertFalse("somekey" in old_repo)

    @patch.object(RepoUpdateActionCommand, "get_consumer_auth_cp")
    def test_no_ssl_verify_status(self, mock_get_consumer_auth_cp):
        mock_cp = Mock()
        mock_cp.has_capability = Mock(return_value=False)
        mock_get_consumer_auth_cp.return_value = mock_cp
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c1 = self._find_content(content, "c1")
        self.assertIsNone(c1["sslverifystatus"])

    @patch.object(RepoUpdateActionCommand, "get_consumer_auth_cp")
    def test_with_ssl_verify_status(self, mock_get_consumer_auth_cp):
        mock_cp = Mock()
        mock_cp.has_capability = Mock(return_value=True)
        mock_get_consumer_auth_cp.return_value = mock_cp
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c1 = self._find_content(content, "c1")
        self.assertEqual("1", c1["sslverifystatus"])

    @patch.object(RepoUpdateActionCommand, "get_consumer_auth_cp")
    def test_with_ssl_verify_ConnectionException(self, mock_get_consumer_auth_cp):
        """Test that network exception is handled and does not use SSL verification."""
        mock_cp = Mock()
        mock_cp.has_capability = Mock(side_effect=rhsm.connection.ConnectionException)
        mock_get_consumer_auth_cp.return_value = mock_cp

        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c1 = self._find_content(content, "c1")
        self.assertIsNone(c1["sslverifystatus"])

    @patch.object(RepoUpdateActionCommand, "get_consumer_auth_cp")
    def test_with_ssl_verify_ProxyException(self, mock_get_consumer_auth_cp):
        """Test that proxy exception is handled and does not use SSL verification."""
        mock_cp = Mock()
        mock_cp.has_capability = Mock(side_effect=rhsm.connection.ProxyException(hostname="host", port=1234))
        mock_get_consumer_auth_cp.return_value = mock_cp

        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com", ca_cert=None)
        c1 = self._find_content(content, "c1")
        self.assertIsNone(c1["sslverifystatus"])


class TidyWriterTests(unittest.TestCase):
    def test_just_newlines_compressed_to_one(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("\n\n\n\n")
        tidy_writer.close()

        self.assertEqual("\n", output.getvalue())

    def test_newline_added_to_eof(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("a line\n")
        tidy_writer.write("another line")
        tidy_writer.close()

        self.assertEqual("a line\nanother line\n", output.getvalue())

    def test_newline_preserved_on_eof(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("a line\n")
        tidy_writer.write("another line\n")
        tidy_writer.close()

        self.assertEqual("a line\nanother line\n", output.getvalue())

    def test_compression_preserves_a_single_blank_line(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\ntest\n")
        tidy_writer.close()

        self.assertEqual("test stuff\n\ntest\n", output.getvalue())

    def test_newlines_compressed_in_single_write(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\n\ntest\n")
        tidy_writer.close()

        self.assertEqual("test stuff\n\ntest\n", output.getvalue())

    def test_newlines_compressed_across_writes(self):
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\n")
        tidy_writer.write("\ntest\n")
        tidy_writer.close()

        self.assertEqual("test stuff\n\ntest\n", output.getvalue())

        # now try the other split
        output = io.StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n")
        tidy_writer.write("\n\ntest\n")
        tidy_writer.close()

        self.assertEqual("test stuff\n\ntest\n", output.getvalue())


class YumReleaseverSourceTest(fixture.SubManFixture):
    def test_init(self):
        # inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        # override_cache_mock = inj.require(inj.OVERRIDE_STATUS_CACHE)

        release_source = YumReleaseverSource()
        self.assertEqual(release_source._expansion, None)
        self.assertEqual(release_source.marker, "$releasever")
        self.assertEqual(release_source.marker, release_source.default)

    def test_default(self):
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()
        self.assertEqual(exp, "$releasever")

    def test_mem_cache_works(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = "MockServer"
        mock_release = {"releaseVer": release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()
        self.assertEqual(exp, release)
        self.assertEqual(release_source._expansion, release)

        exp = release_source.get_expansion()
        self.assertEqual(exp, release)

    def test_mem_cache_pre_cached(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = "MockServer"
        mock_release = {"releaseVer": release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        cached_release = "CachedMockServer"
        release_source._expansion = cached_release
        exp = release_source.get_expansion()
        self.assertEqual(exp, cached_release)
        self.assertEqual(release_source._expansion, cached_release)

    def test_read_status_not_set(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = ""
        mock_release = {"releaseVer": release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()

        # we were unset, should return the default
        self.assertEqual(exp, YumReleaseverSource.default)
        # and cache it
        self.assertEqual(release_source._expansion, YumReleaseverSource.default)


class YumReleaseverSourceIsNotEmptyTest(fixture.SubManFixture):
    def test_empty_string(self):
        self.assertFalse(YumReleaseverSource.is_not_empty(""))

    def test_none(self):
        self.assertFalse(YumReleaseverSource.is_not_empty(None))

    def test_empty_list(self):
        self.assertFalse(YumReleaseverSource.is_not_empty([]))

    def test_number(self):
        self.assertTrue(YumReleaseverSource.is_not_empty("7"))

    def test_string(self):
        self.assertTrue(YumReleaseverSource.is_not_empty("Super"))


class YumReleaseverSourceIsSetTest(fixture.SubManFixture):
    def test_none(self):
        self.assertFalse(YumReleaseverSource.is_set(None))

    def test_key_error(self):
        self.assertFalse(YumReleaseverSource.is_set({"not_release_ver": "blippy"}))

    def test_not_a_dict(self):
        self.assertFalse(YumReleaseverSource.is_set(["some string"]))

    def test_releasever_zero(self):
        self.assertFalse(YumReleaseverSource.is_set({"releaseVer": 0}))

    def test_releasever_none(self):
        self.assertFalse(YumReleaseverSource.is_set({"releaseVer": None}))

    def test_releasever_7server(self):
        self.assertTrue(YumReleaseverSource.is_set({"releaseVer": "7Server"}))

    def test_releasever_the_string_none(self):
        # you laugh, but someone thinks that would be an awesome product name.
        self.assertTrue(YumReleaseverSource.is_set({"releaseVer": "None"}))


class AptRepoFileTest(unittest.TestCase):
    def _helper_stub_repo(self, *args, **kwargs):
        with patch("subscription_manager.repofile.HAS_DEB822", True):
            repo = Repo(*args, **kwargs)
        return repo

    def _helper_stub_repofile(self, *args, **kwargs):
        my_mock = MagicMock()
        with patch("subscription_manager.repofile.RepoFileBase.create", my_mock):
            repofile = AptRepoFile(*args, **kwargs)
        return repofile

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_includes_yum_parameters(self, mock_file):
        # Setup mock
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        ar = self._helper_stub_repofile()
        yr = YumRepoFile()
        mock_repo = self._helper_stub_repo(
            "mock", existing_values=[("baseurl", "https://example.org.org/"), ("sslclientcert", "mypem.pem")]
        )
        # Modify data using different backends (Apt,Yum)
        ar_fixed_content = ar.fix_content(mock_repo)
        yr_fixed_content = yr.fix_content(mock_repo)
        # Yum parameters must be included in Apt as well (garuantee compatibility)
        for key in yr_fixed_content:
            self.assertIn(key, ar_fixed_content)

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_globals(self, mock_file):
        # Setup mock
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        # Setup expected results
        exp_path = "etc/apt/sources.list.d"
        exp_name = "rhsm.sources"
        exp_content_types = ["deb"]
        exp_repofile_header = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be overwritten. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed, consider
# running "apt-get update" to refresh the available repositories.
#
# *** DO NOT EDIT THIS FILE ***
#
"""
        ar = self._helper_stub_repofile()
        # Test actual data against expected results
        self.assertEqual(ar.PATH, exp_path)
        self.assertEqual(ar.NAME, exp_name)
        self.assertEqual(ar.CONTENT_TYPES, exp_content_types)
        self.assertEqual(ar.REPOFILE_HEADER, exp_repofile_header)

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_add_repo(self, mock_file):
        # Setup mock
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        ar = self._helper_stub_repofile()
        mock_repo = self._helper_stub_repo("mock")
        mock_dict = dict([(str(k), str(v)) for (k, v) in mock_repo.items()])
        mock_deb822 = StubDeb822(mock_dict)
        # Modify data
        ar.add(mock_repo)
        # Test modification
        act_repo = ar.repos822[0]
        for key in mock_deb822:
            self.assertIn(key, act_repo)
            self.assertEqual(act_repo[key], mock_repo[key])

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_delete_repo(self, mock_file):
        # Setup mock
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        ar = self._helper_stub_repofile()
        mock_repo_a = self._helper_stub_repo("a")
        mock_repo_b = self._helper_stub_repo("b")
        mock_repo_c = self._helper_stub_repo("c")
        ar.add(mock_repo_a)
        ar.add(mock_repo_b)
        ar.add(mock_repo_c)
        # Modify data
        ar.delete(mock_repo_b.id)
        # Test modification
        self.assertEqual(len(ar.repos822), 2)
        self.assertEqual(ar.repos822[0]["id"], "a")
        self.assertEqual(ar.repos822[1]["id"], "c")

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_update_repo(self, mock_file):
        # Setup mock
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        ar = self._helper_stub_repofile()
        mock_repo_a = self._helper_stub_repo("a", existing_values=[("baseurl", "url")])
        ar.add(mock_repo_a)
        # Modify data
        mock_repo_a["baseurl"] = "new url"
        ar.update(mock_repo_a)
        # Test modification
        self.assertEqual(ar.repos822[0]["id"], "a")
        self.assertEqual(ar.repos822[0]["baseurl"], "new url")

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_fix_content_default(self, mock_file):
        # Setup mock and expected values
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        exp_params = {
            "arches": "none",
            "Types": "deb",
            "URIs": "https://example.site.org/",
            "Suites": "default",
            "Components": "all",
            "Trusted": "yes",
            "sslclientcert": "mypem.pem",
        }
        ar = self._helper_stub_repofile()
        repo_mock = self._helper_stub_repo(
            "mock",
            existing_values=[("baseurl", exp_params["URIs"]), ("sslclientcert", exp_params["sslclientcert"])],
        )
        # Modify data
        act_content = ar.fix_content(repo_mock)
        # Test modification by comparing with expected values
        for key in exp_params:
            self.assertIn(key, act_content)
            self.assertEqual(act_content[key], exp_params[key])

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_fix_content_arches(self, mock_file):
        # Setup mock and expected values
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        exp_params = {"arches": "none", "URIs": "https://example.site.org/", "sslclientcert": "mypem.pem"}
        ar = self._helper_stub_repofile()
        repo_mock = self._helper_stub_repo(
            "mock",
            existing_values=[
                ("baseurl", exp_params["URIs"]),
                ("sslclientcert", exp_params["sslclientcert"]),
                ("arches", ["ALL"]),
            ],
        )
        # Modify data
        act_content = ar.fix_content(repo_mock)
        # Test modification by comparing with expected values
        for key in exp_params:
            self.assertIn(key, act_content)
            self.assertEqual(act_content[key], exp_params[key])

    @patch("builtins.open", new_callable=mock_open, read_data="data")
    def test_fix_content_arches_multi(self, mock_file):
        # Setup mock and expected values
        assert open("/etc/apt/sources.list.d/rhsm.sources").read() == "data"
        mock_file.assert_called_with("/etc/apt/sources.list.d/rhsm.sources")
        exp_params = {
            "arches": "amd64 i386",
            "Architectures": "amd64 i386",
            "URIs": "https://example.site.org/",
            "sslclientcert": "mypem.pem",
        }
        ar = self._helper_stub_repofile()
        repo_mock = self._helper_stub_repo(
            "mock",
            existing_values=[
                ("baseurl", exp_params["URIs"]),
                ("sslclientcert", exp_params["sslclientcert"]),
                ("arches", ["amd64", "i386"]),
            ],
        )
        # Modify data
        act_content = ar.fix_content(repo_mock)
        # Test modification by comparing with expected values
        for key in exp_params:
            self.assertIn(key, act_content)
            self.assertEqual(act_content[key], exp_params[key])


class YumRepoFileTest(unittest.TestCase):
    @patch("subscription_manager.repofile.YumRepoFile.create")
    @patch("subscription_manager.repofile.TidyWriter")
    def test_configparsers_equal(self, tidy_writer, stub_create):
        rf = YumRepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section("test")
            parser.set("test", "key", "val")
        self.assertTrue(rf._configparsers_equal(other))

    @patch("subscription_manager.repofile.YumRepoFile.create")
    @patch("subscription_manager.repofile.TidyWriter")
    def test_configparsers_diff_sections(self, tidy_writer, stub_create):
        rf = YumRepoFile()
        rf.add_section("new_section")
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section("test")
            parser.set("test", "key", "val")
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repofile.YumRepoFile.create")
    @patch("subscription_manager.repofile.TidyWriter")
    def test_configparsers_diff_item_val(self, tidy_writer, stub_create):
        rf = YumRepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section("test")
            parser.set("test", "key", "val")
        rf.set("test", "key", "val2")
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repofile.YumRepoFile.create")
    @patch("subscription_manager.repofile.TidyWriter")
    def test_configparsers_diff_items(self, tidy_writer, stub_create):
        rf = YumRepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section("test")
            parser.set("test", "key", "val")
        rf.set("test", "somekey", "val")
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repofile.YumRepoFile.create")
    @patch("subscription_manager.repofile.TidyWriter")
    def test_configparsers_equal_int(self, tidy_writer, stub_create):
        rf = YumRepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section("test")
            parser.set("test", "key", "val")
        rf.set("test", "k", 1)
        other.set("test", "k", "1")
        self.assertTrue(rf._configparsers_equal(other))


# config file is root only, so just fill in a stringbuffer
unset_manage_repos_cfg_buf = """
[server]
hostname = server.example.conf
prefix = /candlepin
[rhsm]
manage_repos =

[rhsmcertd]
certCheckInterval = 240
"""

unset_config = """[server]
hostname = server.example.conf
"""

manage_repos_zero_config = """[rhsm]
manage_repos = 0
"""

manage_repos_bool_config = """[rhsm]
manage_repos = false
"""

manage_repos_not_an_int = """[rhsm]
manage_repos = thisisanint
"""

manage_repos_int_37 = """[rhsm]
manage_repos = 37
"""


class TestManageReposEnabled(fixture.SubManFixture):
    @patch.object(repofile, "conf", ConfigFromString(config_string=unset_config))
    def test(self):
        # default stub config, no manage_repo defined, uses default
        manage_repos_enabled = repofile.manage_repos_enabled()
        self.assertEqual(manage_repos_enabled, True)

    @patch.object(repofile, "conf", ConfigFromString(config_string=unset_manage_repos_cfg_buf))
    def test_empty_manage_repos(self):
        manage_repos_enabled = repofile.manage_repos_enabled()
        self.assertEqual(manage_repos_enabled, True)

    @patch.object(repofile, "conf", ConfigFromString(config_string=manage_repos_zero_config))
    def test_empty_manage_repos_zero(self):
        manage_repos_enabled = repofile.manage_repos_enabled()
        self.assertEqual(manage_repos_enabled, False)

    @patch.object(repofile, "config", ConfigFromString(config_string=manage_repos_bool_config))
    def test_empty_manage_repos_bool(self):
        manage_repos_enabled = repofile.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEqual(manage_repos_enabled, True)

    @patch.object(repofile, "config", ConfigFromString(config_string=manage_repos_not_an_int))
    def test_empty_manage_repos_not_an_int(self):
        manage_repos_enabled = repofile.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEqual(manage_repos_enabled, True)

    @patch.object(repofile, "conf", ConfigFromString(config_string=manage_repos_int_37))
    def test_empty_manage_repos_int_37(self):
        manage_repos_enabled = repofile.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEqual(manage_repos_enabled, True)


AUTO_ENABLE_PKG_PLUGINS_ENABLED = """
[rhsm]
auto_enable_yum_plugins = 1
"""

AUTO_ENABLE_PKG_PLUGINS_DISABLED = """
[rhsm]
auto_enable_yum_plugins = 0
"""

PKG_PLUGIN_CONF_FILE_ENABLED_INT = """
[main]
enabled = 1
"""

PKG_PLUGIN_CONF_FILE_ENABLED_BOOL = """
[main]
enabled = true
"""

PKG_PLUGIN_CONF_FILE_DISABLED_INT = """
[main]
enabled = 0
"""

PKG_PLUGIN_CONF_FILE_DISABLED_BOOL = """
[main]
enabled = false
"""

PKG_PLUGIN_CONF_FILE_WRONG_VALUE = """
[main]
enabled = 4
"""

PKG_PLUGIN_CONF_FILE_INVALID_VALUE = """
[main]
enabled = 1.0
"""

PKG_PLUGIN_CONF_MISSING_MAIN_SECTION = """
[test]
option = value
"""

PKG_PLUGIN_CONF_MISSING_ENABLED_OPTION = """
[main]
option = value
"""

PKG_PLUGIN_CONF_FILE_CORRUPTED = """
[main
enable =
"""


class TestYumPluginManager(unittest.TestCase):
    """
    This class is intended for testing YumPluginManager
    """

    ORIGINAL_DNF_PLUGIN_DIR = YumPluginManager.DNF_PLUGIN_DIR
    ORIGINAL_PLUGINS = YumPluginManager.PLUGINS

    def tearDown(self) -> None:
        YumPluginManager.DNF_PLUGIN_DIR = self.ORIGINAL_DNF_PLUGIN_DIR
        YumPluginManager.PLUGINS = self.ORIGINAL_PLUGINS

        self.tempdir = None
        self.file_01 = None
        self.file_02 = None

    def init_dnf_plugin_conf_files(self, conf_string: str):
        """
        Mock configuration files of plugins
        """
        self.tempdir = tempfile.TemporaryDirectory()
        self.file_01 = tempfile.mkstemp(suffix=".conf", dir=self.tempdir.name)
        self.file_02 = tempfile.mkstemp(suffix=".conf", dir=self.tempdir.name)
        os.write(self.file_01[0], conf_string.encode("utf-8"))
        os.write(self.file_02[0], conf_string.encode("utf-8"))
        os.close(self.file_01[0])
        os.close(self.file_02[0])

        YumPluginManager.DNF_PLUGIN_DIR = self.tempdir.name
        YumPluginManager.PLUGINS = [
            self.file_01[1].replace(self.tempdir.name + "/", "").replace(".conf", ""),
            self.file_02[1].replace(self.tempdir.name + "/", "").replace(".conf", ""),
        ]

    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "debian", []),
    )
    def test_enable_pkg_plugins_deb(self, mock_get_distribution):
        """
        Test not enabling of yum plugins on deb based systems (Test 1 of 2)
        """
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 0)

    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "", ["debian"]),
    )
    def test_enable_pkg_plugins_deb_like(self, mock_get_distribution):
        """
        Test not enabling of yum plugins on deb based systems (Test 2 of 2)
        """
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 0)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enable_pkg_plugins_yum(self, mock_get_distribution):
        """
        Test enabling of yum plugins on yum based systems
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_DISABLED_INT)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_disabled_dnf_plugin(self, mock_get_distribution):
        """
        Test automatic enabling of configuration files of disabled plugins
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_DISABLED_INT)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)
        for plugin_conf_file_name in YumPluginManager.PLUGINS:
            dnf_plugin_config = ConfigParser()
            result = dnf_plugin_config.read(
                YumPluginManager.DNF_PLUGIN_DIR + "/" + plugin_conf_file_name + ".conf"
            )
            self.assertGreater(len(result), 0)
            is_plugin_enabled = dnf_plugin_config.getint("main", "enabled")
            self.assertEqual(is_plugin_enabled, 1)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_enabled_dnf_plugin_int(self, mock_get_distribution):
        """
        Test automatic enabling of configuration files of already enabled plugins
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_ENABLED_INT)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 0)
        for plugin_conf_file_name in YumPluginManager.PLUGINS:
            yum_plugin_config = ConfigParser()
            result = yum_plugin_config.read(
                YumPluginManager.DNF_PLUGIN_DIR + "/" + plugin_conf_file_name + ".conf"
            )
            self.assertGreater(len(result), 0)
            is_plugin_enabled = yum_plugin_config.getint("main", "enabled")
            self.assertEqual(is_plugin_enabled, 1)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_enabled_dnf_plugin_bool(self, mock_get_distribution):
        """
        Test automatic enabling of configuration files of already enabled plugins
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_ENABLED_BOOL)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 0)
        for plugin_conf_file_name in YumPluginManager.PLUGINS:
            yum_plugin_config = ConfigParser()
            result = yum_plugin_config.read(
                YumPluginManager.DNF_PLUGIN_DIR + "/" + plugin_conf_file_name + ".conf"
            )
            self.assertGreater(len(result), 0)
            # The file was not modified. We have to read value with with getboolean()
            is_plugin_enabled = yum_plugin_config.getboolean("main", "enabled")
            self.assertEqual(is_plugin_enabled, True)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_dnf_plugin_with_invalid_values(self, mock_get_distribution):
        """
        Test automatic enabling of configuration files of already enabled plugins
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_INVALID_VALUE)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)
        for plugin_conf_file_name in YumPluginManager.PLUGINS:
            yum_plugin_config = ConfigParser()
            result = yum_plugin_config.read(
                YumPluginManager.DNF_PLUGIN_DIR + "/" + plugin_conf_file_name + ".conf"
            )
            self.assertGreater(len(result), 0)
            is_plugin_enabled = yum_plugin_config.getint("main", "enabled")
            self.assertEqual(is_plugin_enabled, 1)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_dnf_plugin_with_wrong_conf(self, mock_get_distribution):
        """
        Test automatic enabling of configuration files of already plugins with wrong values in conf file.
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_WRONG_VALUE)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)
        for plugin_conf_file_name in YumPluginManager.PLUGINS:
            yum_plugin_config = ConfigParser()
            result = yum_plugin_config.read(
                YumPluginManager.DNF_PLUGIN_DIR + "/" + plugin_conf_file_name + ".conf"
            )
            self.assertGreater(len(result), 0)
            is_plugin_enabled = yum_plugin_config.getint("main", "enabled")
            self.assertEqual(is_plugin_enabled, 1)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_dnf_plugin_with_corrupted_conf_file(self, mock_get_distribution):
        """
        This test only test YumPluginManager.enable_yum_plugins() can survive reading of corrupted
        dnf plugin configuration file
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_FILE_CORRUPTED)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 0)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_dnf_plugin_with_missing_main_section(self, mock_get_distribution):
        """
        This test only test YumPluginManager.enable_yum_plugins() can survive reading of corrupted
        dnf plugin configuration file (missing main section)
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_MISSING_MAIN_SECTION)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)

    @patch.object(repolib, "conf", ConfigFromString(config_string=AUTO_ENABLE_PKG_PLUGINS_ENABLED))
    @patch(
        "rhsmlib.facts.hwprobe.HardwareCollector.get_distribution",
        return_value=("", "", "", "", "rhel", []),
    )
    def test_enabling_dnf_plugin_with_missing_enabled_option(self, mock_get_distribution):
        """
        This test only test YumPluginManager.enable_yum_plugins() can survive reading of corrupted
        dnf plugin configuration file (missing option 'enabled')
        """
        self.init_dnf_plugin_conf_files(conf_string=PKG_PLUGIN_CONF_MISSING_ENABLED_OPTION)
        plugin_list = YumPluginManager.enable_pkg_plugins()
        self.assertEqual(len(plugin_list), 2)
