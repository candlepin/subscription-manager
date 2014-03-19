#
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

import unittest

from mock import Mock, patch
from StringIO import StringIO

from rhsm.utils import UnsupportedOperationException

from fixture import SubManFixture
from stubs import StubCertificateDirectory, StubProductCertificate, \
        StubProduct, StubEntitlementCertificate, StubContent, \
        StubProductDirectory, StubUEP, StubConsumerIdentity
from subscription_manager.repolib import Repo, RepoUpdateAction, TidyWriter
from subscription_manager import injection as inj

from subscription_manager import repolib


class RepoTests(unittest.TestCase):
    """
    Tests for the repolib Repo class
    """

    def test_valid_label_for_id(self):
        repo_id = 'valid-label'
        repo = Repo(repo_id)
        self.assertEquals(repo_id, repo.id)

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


class RepoUpdateActionTests(SubManFixture):

    def setUp(self):
        super(RepoUpdateActionTests, self).setUp()
        stub_prod = StubProduct("fauxprod", provided_tags="TAG1,TAG2")
        stub_prod2 = StubProduct("fauxprovidedprod", provided_tags="TAG4")
        stub_prod_cert = StubProductCertificate(stub_prod, provided_products=[stub_prod2])
        stub_prod2 = StubProduct("fauxprod2", provided_tags="TAG5,TAG6")
        stub_prod2_cert = StubProductCertificate(stub_prod2)
        stub_prod_dir = StubProductDirectory([stub_prod_cert, stub_prod2_cert])

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
        stub_ent_dir = StubCertificateDirectory([self.stub_ent_cert])

        repolib.ConsumerIdentity = StubConsumerIdentity
        stub_uep = StubUEP()
        self.update_action = RepoUpdateAction(uep=stub_uep, prod_dir=stub_prod_dir,
                ent_dir=stub_ent_dir)

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

        RepoUpdateAction(mock_uep, prod_dir=StubProductDirectory(),
                     ent_dir=StubCertificateDirectory())

        # No cache calls should be made if overrides are not supported
        self.assertFalse(override_cache_mock.read_cache.called)
        self.assertFalse(override_cache_mock.load_status.called)

    def test_overrides_trump_ent_cert(self):
        self.update_action.overrides = [{
            'contentLabel': 'x',
            'name': 'gpgcheck',
            'value': 'blah'
        }]
        r = Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])
        self.assertEquals('original', r['gpgcheck'])
        self.update_action._set_override_info(r)
        self.assertEquals('blah', r['gpgcheck'])
        self.assertEquals('some_key', r['gpgkey'])

    @patch("subscription_manager.repolib.RepoFile")
    def test_update_when_new_repo(self, mock_file):
        mock_file = mock_file.return_value
        mock_file.section.return_value = None

        def stub_content():
            return [Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])]
        self.update_action.get_unique_content = stub_content
        update_report = self.update_action.perform()
        written_repo = mock_file.add.call_args[0][0]
        self.assertEquals('original', written_repo['gpgcheck'])
        self.assertEquals('some_key', written_repo['gpgkey'])
        self.assertEquals(1, update_report.updates())

    @patch("subscription_manager.repolib.RepoFile")
    def test_update_when_registered_and_existing_repo(self, mock_file):
        mock_file = mock_file.return_value
        mock_file.section.return_value = Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])

        def stub_content():
            return [Repo('x', [('gpgcheck', 'new'), ('gpgkey', 'new_key')])]
        self.update_action.get_unique_content = stub_content
        self.update_action.override_supported = True
        update_report = self.update_action.perform()
        written_repo = mock_file.update.call_args[0][0]
        self.assertEquals('new', written_repo['gpgcheck'])
        self.assertEquals('new_key', written_repo['gpgkey'])
        self.assertEquals(1, update_report.updates())

    @patch("subscription_manager.repolib.RepoFile")
    def test_update_when_not_registered_and_existing_repo(self, mock_file):
        self._inject_mock_invalid_consumer()
        mock_file = mock_file.return_value
        mock_file.section.return_value = Repo('x', [('gpgcheck', 'original'), ('gpgkey', 'some_key')])

        def stub_content():
            return [Repo('x', [('gpgcheck', 'new'), ('gpgkey', 'new_key')])]
        self.update_action.get_unique_content = stub_content
        self.update_action.perform()
        written_repo = mock_file.update.call_args[0][0]
        self.assertEquals('original', written_repo['gpgcheck'])
        self.assertEquals('new_key', written_repo['gpgkey'])

    def test_no_gpg_key(self):
        content = self.update_action.get_content(self.stub_ent_cert,
                "http://example.com", None)
        c1 = self._find_content(content, 'c1')
        self.assertEquals('', c1['gpgkey'])
        self.assertEquals('0', c1['gpgcheck'])

        c2 = self._find_content(content, 'c2')
        self.assertEquals('', c2['gpgkey'])
        self.assertEquals('0', c2['gpgcheck'])

    def test_gpg_key(self):
        content = self.update_action.get_content(self.stub_ent_cert,
                "http://example.com", None)
        c4 = self._find_content(content, 'c4')
        self.assertEquals('http://example.com/gpg.key', c4['gpgkey'])
        self.assertEquals('1', c4['gpgcheck'])

    def test_ui_repoid_vars(self):
        content = self.update_action.get_content(self.stub_ent_cert,
                "http://example.com", None)
        c4 = self._find_content(content, 'c4')
        self.assertEquals('some path', c4['ui_repoid_vars'])
        c2 = self._find_content(content, 'c2')
        self.assertEquals(None, c2['ui_repoid_vars'])

    def test_tags_found(self):
        content = self.update_action.get_unique_content()
        self.assertEquals(3, len(content))

    def test_join(self):
        base = "http://foo/bar"
        # File urls should be preserved
        self.assertEquals("file://this/is/a/file",
            self.update_action.join(base, "file://this/is/a/file"))
        # Http locations should be preserved
        self.assertEquals("http://this/is/a/url",
            self.update_action.join(base, "http://this/is/a/url"))
        # Blank should remain blank
        self.assertEquals("",
            self.update_action.join(base, ""))
        # Url Fragments should work
        self.assertEquals("http://foo/bar/baz",
            self.update_action.join(base, "baz"))
        self.assertEquals("http://foo/bar/baz",
            self.update_action.join(base, "/baz"))
        base = base + "/"
        self.assertEquals("http://foo/bar/baz",
            self.update_action.join(base, "baz"))
        self.assertEquals("http://foo/bar/baz",
            self.update_action.join(base, "/baz"))

    def test_only_allow_content_of_type_yum(self):
        content = self.update_action.get_content(self.stub_ent_cert,
                                                 "http://example.com", None)
        self.assertTrue(self._find_content(content, "c1") is not None)
        self.assertTrue(self._find_content(content, "c5") is None)
        self.assertTrue(self._find_content(content, "c6") is None)

    def test_mutable_property(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {'metadata_expire': 2000}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_gpgcheck_is_mutable(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['gpgcheck'] = "0"
        incoming_repo = {'gpgcheck': "1"}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("0", existing_repo['gpgcheck'])

    def test_mutable_property_in_repo_but_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = 1000
        incoming_repo = {}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(1000, existing_repo['metadata_expire'])

    def test_immutable_property(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['name'] = "meow"
        incoming_repo = {'name': "woof"}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # If the user removed a mutable property completely, or the property
    # is new in a new version of the entitlement certificate, the new value
    # should get written out.
    def test_unset_mutable_property(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        incoming_repo = {'metadata_expire': 2000}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual(2000, existing_repo['metadata_expire'])

    def test_unset_immutable_property(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        incoming_repo = {'name': "woof"}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertEqual("woof", existing_repo['name'])

    # Test repo on disk has an immutable property set which has since been
    # unset in the new repo definition. This property should be removed.
    def test_set_immutable_property_now_empty(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {}
        self.update_action.update_repo(existing_repo, incoming_repo)
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_mutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {'metadata_expire': ''}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_immutable_property_now_empty_value(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {'proxy_username': ''}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_mutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {'metadata_expire': None}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_mutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['metadata_expire'] = "blah"
        incoming_repo = {}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # re comments in repolib
        # Mutable properties should be added if not currently defined,
        # otherwise left alone.
        self.assertTrue("metadata_expire" in existing_repo.keys())

    def test_set_immutable_property_now_none(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {'proxy_username': None}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_set_immutable_property_now_not_in_cert(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {}
        self.update_action.update_repo(existing_repo, incoming_repo)
        # Immutable properties should be always be added/updated,
        # and removed if undefined in the new repo definition.
        self.assertFalse("proxy_username" in existing_repo.keys())

    def test_unknown_property_is_preserved(self):
        self._inject_mock_invalid_consumer()
        existing_repo = Repo('testrepo')
        existing_repo['fake_prop'] = 'fake'
        self.assertTrue(('fake_prop', 'fake') in existing_repo.items())

    def test_repo_update_forbidden_when_registered(self):
        existing_repo = Repo('testrepo')
        existing_repo['proxy_username'] = "blah"
        incoming_repo = {'proxy_username': 'foo'}
        self.update_action.override_supported = True
        self.assertRaises(UnsupportedOperationException, self.update_action.update_repo, existing_repo, incoming_repo)


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
