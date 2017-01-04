#
# -*- coding: utf-8 -*-#
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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import re
import fixture

from iniparse import RawConfigParser, SafeConfigParser
from mock import Mock, patch
from StringIO import StringIO

from stubs import StubCertificateDirectory, StubProductCertificate, \
        StubProduct, StubEntitlementCertificate, StubContent, \
        StubProductDirectory, StubConsumerIdentity, StubEntitlementDirectory
from subscription_manager.repolib import Repo, RepoActionInvoker, \
        RepoUpdateActionCommand, TidyWriter, RepoFile, YumReleaseverSource
from subscription_manager import injection as inj
from rhsm.config import RhsmConfigParser
from rhsmlib.services import config

from subscription_manager import repolib


class TestRepoActionInvoker(fixture.SubManFixture):
    def _stub_content(self):
        stub_prod = StubProduct('stub_product',
                                provided_tags="stub-product")

        stub_content = StubContent("a_test_repo",
                                   required_tags="stub-product")

        stub_ent_cert = StubEntitlementCertificate(stub_prod,
                                                   content=[stub_content])
        stub_prod_cert = StubProductCertificate(stub_prod)

        stub_ent_dir = StubEntitlementDirectory([stub_ent_cert])
        stub_prod_dir = StubProductDirectory([stub_prod_cert])

        inj.provide(inj.ENT_DIR, stub_ent_dir)
        inj.provide(inj.PROD_DIR, stub_prod_dir)

    def test_is_managed(self):
        self._stub_content()
        repo_action_invoker = RepoActionInvoker()
        repo_label = 'a_test_repo'

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
        self._stub_content()
        repo_action_invoker = RepoActionInvoker()
        repos = repo_action_invoker.get_repos()
        if len(repos) == 0:
            self.fail("get_repos() should have a set of Repo's, but the set is empty.")


class RepoTests(unittest.TestCase):
    """
    Tests for the repolib Repo class
    """

    def test_valid_label_for_id(self):
        repo_id = 'valid-label'
        repo = Repo(repo_id)
        self.assertEquals(repo_id, repo.id)

    def test_valid_unicode_just_ascii_label_for_id(self):
        repo_id = u'valid-label'
        repo = Repo(repo_id)
        self.assertEquals(repo_id, repo.id)

    def test_invalid_unicode_label_for_id(self):
        repo_id = u'valid-不明-label'
        repo = Repo(repo_id)
        expected = 'valid----label'
        self.assertEquals(expected, repo.id)

    def test_invalid_label_with_spaces(self):
        repo_id = 'label with spaces'
        repo = Repo(repo_id)
        self.assertEquals('label-with-spaces', repo.id)

    def test_existing_order_is_preserved(self):
        config = (('key 1', 'value 1'), ('key b', 'value b'),
                ('key 3', 'value 3'))
        repo = Repo('testrepo', config)
        self.assertEquals(config, repo.items()[:3])

    def test_empty_strings_not_set_in_file(self):
        r = Repo('testrepo', (('proxy', ""),))
        r['proxy'] = ""
        self.assertFalse(("proxy", "") in r.items())

    def test_unknown_property_is_preserved(self):
        existing_repo = Repo('testrepo')
        existing_repo['fake_prop'] = 'fake'
        self.assertTrue(('fake_prop', 'fake') in existing_repo.items())


class RepoActionReportTests(fixture.SubManFixture):
    def test(self):
        report = repolib.RepoActionReport()
        repo = self._repo(u'a-unicode-content-label', u'A unicode repo name')
        report.repo_updates.append(repo)
        report.repo_added.append(repo)
        deleted_section = u'einige-repo-name'
        deleted_section_2 = u'一些回購名稱'
        report.repo_deleted = [deleted_section, deleted_section_2]

        # okay as long as no UnicodeErrors
        str(report)

        with fixture.locale_context('de_DE.utf8'):
            str(report)

    def _repo(self, id, name):
        repo = repolib.Repo(repo_id=id)
        repo['name'] = name
        return repo

    def test_empty(self):
        report = repolib.RepoActionReport()
        self.assertEquals(report.updates(), 0)
        '%s' % report
        str(report)

    def test_format(self):
        report = repolib.RepoActionReport()
        repo = self._repo('a-repo-label', 'A Repo Name')
        report.repo_updates.append(repo)
        res = str(report)
        # needs tests run in eng locale, coupled to report format since
        # I managed to typo them
        report_label_regexes = ['^Repo updates$', '^Total repo updates:',
                                '^Updated$', '^Added \(new\)$', '^Deleted$']
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
                StubContent("c1", required_tags="", gpg=None),   # no required tags
                StubContent("c2", required_tags="TAG1", gpg=""),
                StubContent("c3", required_tags="TAG1,TAG2,TAG3"),  # should get skipped
                StubContent("c4", required_tags="TAG1,TAG2,TAG4,TAG5,TAG6",
                    gpg="/gpg.key", url="/$some/$path"),
                StubContent("c5", content_type="file", required_tags="", gpg=None),
                StubContent("c6", content_type="file", required_tags="", gpg=None),
        ]
        self.stub_ent_cert = StubEntitlementCertificate(stub_prod, content=stub_content)
        ent_dir = StubCertificateDirectory([self.stub_ent_cert])
        inj.provide(inj.ENT_DIR, ent_dir)

        repolib.ConsumerIdentity = StubConsumerIdentity

    def _find_content(self, content_list, name):
        """
        Scan list of content for one with name.
        """
        for content in content_list:
            if content['name'] == name:
                return content
        return None

    def test_override_cache_update_skipped_when_overrides_not_supported_on_server(self):
        inj.provide(inj.OVERRIDE_STATUS_CACHE, Mock())
        override_cache_mock = inj.require(inj.OVERRIDE_STATUS_CACHE)

        mock_uep = Mock()
        mock_uep.supports_resource = Mock(return_value=False)
        mock_uep.getCertificates = Mock(return_value=[])
        mock_uep.getCertificateSerials = Mock(return_value=[])
        mock_uep.getRelease = Mock(return_value={'releaseVer': "dummyrelease"})

        self.set_consumer_auth_cp(mock_uep)

        RepoUpdateActionCommand()

        # No cache calls should be made if overrides are not supported
        self.assertFalse(override_cache_mock.read_cache.called)
        self.assertFalse(override_cache_mock.load_status.called)

    def test_overrides_trump_ent_cert(self):
        update_action = RepoUpdateActionCommand()
        update_action.overrides = {'x': {'gpgcheck': 'blah'}}
        r = Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])
        self.assertEquals('original', r['gpgcheck'])
        update_action._set_override_info(r)
        self.assertEquals('blah', r['gpgcheck'])
        self.assertEquals('some_key', r['gpgkey'])

    def test_overrides_trump_existing(self):
        update_action = RepoUpdateActionCommand()
        update_action.overrides = {'x': {'gpgcheck': 'blah'}}
        values = [('gpgcheck', 'original'), ('gpgkey', 'some_key')]
        old_repo = Repo('x', values)
        new_repo = Repo(old_repo.id, values)
        update_action._set_override_info(new_repo)
        self.assertEquals('original', old_repo['gpgcheck'])
        update_action.update_repo(old_repo, new_repo)
        self.assertEquals('blah', old_repo['gpgcheck'])
        self.assertEquals('some_key', old_repo['gpgkey'])

    @patch("subscription_manager.repolib.RepoFile")
    def test_update_when_new_repo(self, mock_file):
        mock_file = mock_file.return_value
        mock_file.section.return_value = None

        def stub_content():
            return [Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])]

        update_action = RepoUpdateActionCommand()
        update_action.get_unique_content = stub_content
        update_report = update_action.perform()
        written_repo = mock_file.add.call_args[0][0]
        self.assertEquals('original', written_repo['gpgcheck'])
        self.assertEquals('some_key', written_repo['gpgkey'])
        self.assertEquals(1, update_report.updates())

    @patch("subscription_manager.repolib.RepoFile")
    def test_update_when_not_registered_and_existing_repo(self, mock_file):
        self._inject_mock_invalid_consumer()
        mock_file = mock_file.return_value
        mock_file.section.return_value = Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])

        def stub_content():
            return [Repo('x', [('gpgcheck', 'new'), ('gpgkey', 'new_key'), ('name', 'test')])]

        update_action = RepoUpdateActionCommand()
        update_action.get_unique_content = stub_content
        update_action.perform()

        written_repo = mock_file.update.call_args[0][0]
        self.assertEquals('original', written_repo['gpgcheck'])
        self.assertEquals('new_key', written_repo['gpgkey'])

    def test_no_gpg_key(self):

        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com",
                                                ca_cert=None)
        c1 = self._find_content(content, 'c1')
        self.assertEquals('', c1['gpgkey'])
        self.assertEquals('0', c1['gpgcheck'])

        c2 = self._find_content(content, 'c2')
        self.assertEquals('', c2['gpgkey'])
        self.assertEquals('0', c2['gpgcheck'])

    def test_gpg_key(self):

        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com",
                                                ca_cert=None)
        c4 = self._find_content(content, 'c4')
        self.assertEquals('http://example.com/gpg.key', c4['gpgkey'])
        self.assertEquals('1', c4['gpgcheck'])

    def test_ui_repoid_vars(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com",
                                            ca_cert=None)
        c4 = self._find_content(content, 'c4')
        self.assertEquals('some path', c4['ui_repoid_vars'])
        c2 = self._find_content(content, 'c2')
        self.assertEquals(None, c2['ui_repoid_vars'])

    def test_tags_found(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_unique_content()
        self.assertEquals(3, len(content))

    def test_only_allow_content_of_type_yum(self):
        update_action = RepoUpdateActionCommand()
        content = update_action.get_all_content(baseurl="http://example.com",
                                                ca_cert=None)
        self.assertTrue(self._find_content(content, "c1") is not None)
        self.assertTrue(self._find_content(content, "c5") is None)
        self.assertTrue(self._find_content(content, "c6") is None)

    def test_mutable_property(self):
        update_action = RepoUpdateActionCommand()
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {'metadata_expire': 2000}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_gpgcheck_is_mutable(self):
        update_action = RepoUpdateActionCommand()
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['gpgcheck'] = "0"
        incoming_repo = {'gpgcheck': "1"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("0", existing_repo['gpgcheck'])

    def test_mutable_property_in_repo_but_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_immutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['name'] = "meow"
        incoming_repo = {'name': "woof"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # If the user removed a mutable property completely, or the property
    # is new in a new version of the entitlement certificate, the new value
    # should get written out.
    def test_unset_mutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        incoming_repo = {'metadata_expire': 2000}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(2000, existing_repo['metadata_expire'])

    def test_unset_immutable_property(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        incoming_repo = {'name': "woof"}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # Test repo on disk has an immutable property set which has since been
    # unset in the new repo definition. This property should be removed.
    def test_set_immutable_property_now_empty(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_mutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {'metadata_expire': ''}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_immutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {'proxy_username': ''}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_mutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {'metadata_expire': None}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_mutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_immutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {'proxy_username': None}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_immutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        update_action = RepoUpdateActionCommand()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {}
        update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_overrides_removed_revert_to_default(self):
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {'x': {'gpgcheck': 'blah'}}
        update_action.overrides = {}
        old_repo = Repo('x', [('gpgcheck', 'blah'), ('gpgkey', 'some_key')])
        new_repo = Repo(old_repo.id, [('gpgcheck', 'original'), ('gpgkey', 'some_key')])
        update_action._set_override_info(new_repo)
        # The value from the current repo file (with the old override) should exist pre-update
        self.assertEquals('blah', old_repo['gpgcheck'])
        update_action.update_repo(old_repo, new_repo)
        # Because the override has been removed, the value is reset to the default
        self.assertEquals('original', old_repo['gpgcheck'])
        self.assertEquals('some_key', old_repo['gpgkey'])

    def test_overrides_removed_and_edited(self):
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {'x': {'gpgcheck': 'override_value'}}
        update_action.overrides = {}
        old_repo = Repo('x', [('gpgcheck', 'hand_edit'), ('gpgkey', 'some_key')])
        new_repo = Repo(old_repo.id, [('gpgcheck', 'original'), ('gpgkey', 'some_key')])
        update_action._set_override_info(new_repo)
        # The value from the current repo file (with the old hand edit) should exist pre-update
        self.assertEquals('hand_edit', old_repo['gpgcheck'])
        update_action.update_repo(old_repo, new_repo)
        # Because the current value doesn't match the override, we don't modify it
        self.assertEquals('hand_edit', old_repo['gpgcheck'])
        self.assertEquals('some_key', old_repo['gpgkey'])

    def test_non_default_overrides_added_to_existing(self):
        '''
        Test that overrides for values that aren't found in Repo.PROPERTIES are written
        to existing repos
        '''
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {}
        update_action.overrides = {'x': {'somekey': 'someval'}}
        old_repo = Repo('x', [])
        new_repo = Repo(old_repo.id, [])
        update_action._set_override_info(new_repo)
        update_action.update_repo(old_repo, new_repo)
        self.assertEquals('someval', old_repo['somekey'])

    def test_non_default_override_removed_deleted(self):
        '''
        Test that overrides for values that aren't found in Repo.PROPERTIES are
        removed from redhat.repo once the override is removed
        '''
        update_action = RepoUpdateActionCommand()
        update_action.written_overrides.overrides = {'x': {'somekey': 'someval'}}
        update_action.overrides = {}
        old_repo = Repo('x', [('somekey', 'someval')])
        new_repo = Repo(old_repo.id, [])
        update_action._set_override_info(new_repo)
        update_action.update_repo(old_repo, new_repo)
        self.assertFalse('somekey' in old_repo)


class TidyWriterTests(unittest.TestCase):

    def test_just_newlines_compressed_to_one(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("\n\n\n\n")
        tidy_writer.close()

        self.assertEquals("\n", output.getvalue())

    def test_newline_added_to_eof(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("a line\n")
        tidy_writer.write("another line")
        tidy_writer.close()

        self.assertEquals("a line\nanother line\n", output.getvalue())

    def test_newline_preserved_on_eof(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("a line\n")
        tidy_writer.write("another line\n")
        tidy_writer.close()

        self.assertEquals("a line\nanother line\n", output.getvalue())

    def test_compression_preserves_a_single_blank_line(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\ntest\n")
        tidy_writer.close()

        self.assertEquals("test stuff\n\ntest\n", output.getvalue())

    def test_newlines_compressed_in_single_write(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\n\ntest\n")
        tidy_writer.close()

        self.assertEquals("test stuff\n\ntest\n", output.getvalue())

    def test_newlines_compressed_across_writes(self):
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n\n")
        tidy_writer.write("\ntest\n")
        tidy_writer.close()

        self.assertEquals("test stuff\n\ntest\n", output.getvalue())

        # now try the other split
        output = StringIO()
        tidy_writer = TidyWriter(output)

        tidy_writer.write("test stuff\n")
        tidy_writer.write("\n\ntest\n")
        tidy_writer.close()

        self.assertEquals("test stuff\n\ntest\n", output.getvalue())


class YumReleaseverSourceTest(fixture.SubManFixture):
    def test_init(self):
        #inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        #override_cache_mock = inj.require(inj.OVERRIDE_STATUS_CACHE)

        release_source = YumReleaseverSource()
        self.assertEquals(release_source._expansion, None)
        self.assertEquals(release_source.marker, "$releasever")
        self.assertEquals(release_source.marker, release_source.default)

    def test_default(self):
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()
        self.assertEquals(exp, "$releasever")

    def test_mem_cache_works(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = "MockServer"
        mock_release = {'releaseVer': release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()
        self.assertEquals(exp, release)
        self.assertEquals(release_source._expansion, release)

        exp = release_source.get_expansion()
        self.assertEquals(exp, release)

    def test_mem_cache_pre_cached(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = "MockServer"
        mock_release = {'releaseVer': release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        cached_release = "CachedMockServer"
        release_source._expansion = cached_release
        exp = release_source.get_expansion()
        self.assertEquals(exp, cached_release)
        self.assertEquals(release_source._expansion, cached_release)

    def test_read_status_not_set(self):
        inj.provide(inj.RELEASE_STATUS_CACHE, Mock())
        release_mock = inj.require(inj.RELEASE_STATUS_CACHE)

        release = ""
        mock_release = {'releaseVer': release}
        release_mock.read_status = Mock(return_value=mock_release)
        release_source = YumReleaseverSource()

        exp = release_source.get_expansion()

        # we were unset, should return the default
        self.assertEquals(exp, YumReleaseverSource.default)
        # and cache it
        self.assertEquals(release_source._expansion, YumReleaseverSource.default)


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
        self.assertFalse(YumReleaseverSource.is_set({'not_release_ver': 'blippy'}))

    def test_not_a_dict(self):
        self.assertFalse(YumReleaseverSource.is_set(['some string']))

    def test_releasever_zero(self):
        self.assertFalse(YumReleaseverSource.is_set({'releaseVer': 0}))

    def test_releasever_none(self):
        self.assertFalse(YumReleaseverSource.is_set({'releaseVer': None}))

    def test_releasever_7server(self):
        self.assertTrue(YumReleaseverSource.is_set({'releaseVer': '7Server'}))

    def test_releasever_the_string_none(self):
        # you laugh, but someone thinks that would be an awesome product name.
        self.assertTrue(YumReleaseverSource.is_set({'releaseVer': 'None'}))


class RepoFileTest(unittest.TestCase):

    @patch("subscription_manager.repolib.RepoFile.create")
    @patch("subscription_manager.repolib.TidyWriter")
    def test_configparsers_equal(self, tidy_writer, stub_create):
        rf = RepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section('test')
            parser.set('test', 'key', 'val')
        self.assertTrue(rf._configparsers_equal(other))

    @patch("subscription_manager.repolib.RepoFile.create")
    @patch("subscription_manager.repolib.TidyWriter")
    def test_configparsers_diff_sections(self, tidy_writer, stub_create):
        rf = RepoFile()
        rf.add_section('new_section')
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section('test')
            parser.set('test', 'key', 'val')
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repolib.RepoFile.create")
    @patch("subscription_manager.repolib.TidyWriter")
    def test_configparsers_diff_item_val(self, tidy_writer, stub_create):
        rf = RepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section('test')
            parser.set('test', 'key', 'val')
        rf.set('test', 'key', 'val2')
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repolib.RepoFile.create")
    @patch("subscription_manager.repolib.TidyWriter")
    def test_configparsers_diff_items(self, tidy_writer, stub_create):
        rf = RepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section('test')
            parser.set('test', 'key', 'val')
        rf.set('test', 'somekey', 'val')
        self.assertFalse(rf._configparsers_equal(other))

    @patch("subscription_manager.repolib.RepoFile.create")
    @patch("subscription_manager.repolib.TidyWriter")
    def test_configparsers_equal_int(self, tidy_writer, stub_create):
        rf = RepoFile()
        other = RawConfigParser()
        for parser in [rf, other]:
            parser.add_section('test')
            parser.set('test', 'key', 'val')
        rf.set('test', 'k', 1)
        other.set('test', 'k', '1')
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


class ConfigFromString(config.Config):
    def __init__(self, config_string):
        parser = RhsmConfigParserFromString(config_string)
        super(ConfigFromString, self).__init__(parser)


class RhsmConfigParserFromString(RhsmConfigParser):
    def __init__(self, config_string):
        SafeConfigParser.__init__(self)
        self.stringio = StringIO(config_string)
        self.readfp(self.stringio)


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
    @patch.object(repolib, 'conf', ConfigFromString(config_string=unset_config))
    def test(self):
        # default stub config, no manage_repo defined, uses default
        manage_repos_enabled = repolib.manage_repos_enabled()
        self.assertEquals(manage_repos_enabled, True)

    @patch.object(repolib, 'conf', ConfigFromString(config_string=unset_manage_repos_cfg_buf))
    def test_empty_manage_repos(self):
        manage_repos_enabled = repolib.manage_repos_enabled()
        self.assertEquals(manage_repos_enabled, True)

    @patch.object(repolib, 'conf', ConfigFromString(config_string=manage_repos_zero_config))
    def test_empty_manage_repos_zero(self):
        manage_repos_enabled = repolib.manage_repos_enabled()
        self.assertEquals(manage_repos_enabled, False)

    @patch.object(repolib, 'config', ConfigFromString(config_string=manage_repos_bool_config))
    def test_empty_manage_repos_bool(self):
        manage_repos_enabled = repolib.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEquals(manage_repos_enabled, True)

    @patch.object(repolib, 'config', ConfigFromString(config_string=manage_repos_not_an_int))
    def test_empty_manage_repos_not_an_int(self):
        manage_repos_enabled = repolib.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEquals(manage_repos_enabled, True)

    @patch.object(repolib, 'conf', ConfigFromString(config_string=manage_repos_int_37))
    def test_empty_manage_repos_int_37(self):
        manage_repos_enabled = repolib.manage_repos_enabled()
        # Should fail, and return default of 1
        self.assertEquals(manage_repos_enabled, True)
