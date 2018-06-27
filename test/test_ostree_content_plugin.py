# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

# import subman fixture
# override plugin manager with one that provides
#  the ostree content plugin

# test tree format
#
# test repo model
#

# test constructing from Content models
# ignores wrong content type
from six.moves import configparser

import six
import mock
from . import fixture

from subscription_manager.model import EntitlementSource, Entitlement, \
    find_content
from subscription_manager.model.ent_cert import EntitlementCertContent
from subscription_manager.plugin.ostree import config
from subscription_manager.plugin.ostree import model
from subscription_manager.plugin.ostree import action_invoker

from rhsm import certificate2


class StubPluginManager(object):
        pass


class TestOstreeRemoteNameFromSection(fixture.SubManFixture):
    def test_normal(self):
        sn = r'remote "awesomeos-foo-container"'
        name = model.OstreeRemote.name_from_section(sn)
        self.assertTrue(name is not None)
        self.assertEqual(name, "awesomeos-foo-container")
        # no quotes in the name
        self.assertFalse('"' in name)

    def test_spaces(self):
        # We consider remote names to be content labels, so
        # shouldn't have space, but afaik ostree doesn't care
        sn = r'remote "awesome os container"'
        name = model.OstreeRemote.name_from_section(sn)
        self.assertTrue(name is not None)
        self.assertEqual(name, "awesome os container")
        self.assertFalse('"' in name)

    def test_no_remote_keyword(self):
        sn = r'"some-string-that-is-wrong"'
        self.assert_name_error(sn)

    def test_no_quoted(self):
        sn = r'remote not-a-real-name'
        self.assert_name_error(sn)

    def test_open_quote(self):
        sn = r'remote "strine-with-open-quote'
        self.assert_name_error(sn)

    def test_empty_quote(self):
        sn = r'remote ""'
        self.assert_name_error(sn)

    def assert_name_error(self, sn):
        self.assertRaises(model.RemoteSectionNameParseError,
                          model.OstreeRemote.name_from_section,
                          sn)


class TestOstreeRemote(fixture.SubManFixture):
    section_name = r'remote "awesomeos-content"'
    example_url = 'http://example.com.not.real/content'

    def assert_remote(self, remote):
        self.assertTrue(isinstance(remote, model.OstreeRemote))

    def test(self):
        items = {'url': self.example_url,
                 'gpg-verify': 'true'}
        ostree_remote = \
            model.OstreeRemote.from_config_section(self.section_name,
                                                   items)
        self.assert_remote(ostree_remote)
        self.assertEqual('true', ostree_remote.gpg_verify)
        self.assertEqual(self.example_url, ostree_remote.url)

    def test_other_items(self):
        items = {'url': self.example_url,
                 'a_new_key': 'a_new_value',
                 'tls-client-cert-path': '/etc/some/path',
                 'tls-client-key-path': '/etc/some/path-key',
                 'tls-ca-path': '/etc/rhsm/ca/redhat-uep.pem',
                 'gpg-verify': 'true',
                 'blip': 'baz'}
        ostree_remote = \
            model.OstreeRemote.from_config_section(self.section_name,
                                                   items)
        self.assert_remote(ostree_remote)
        # .url and data['url'] work
        self.assertEqual(self.example_url, ostree_remote.url)
        self.assertEqual(self.example_url, ostree_remote.data['url'])

        self.assertTrue('a_new_key' in ostree_remote)
        self.assertEqual('a_new_value', ostree_remote.data['a_new_key'])

        self.assertTrue('gpg_verify' in ostree_remote)
        self.assertTrue(hasattr(ostree_remote, 'gpg_verify'))
        self.assertEqual('true', ostree_remote.gpg_verify)
        self.assertFalse('gpg-verify' in ostree_remote)
        self.assertFalse(hasattr(ostree_remote, 'gpg-verify'))

        self.assertTrue(hasattr(ostree_remote, 'tls_ca_path'))
        self.assertEqual('/etc/rhsm/ca/redhat-uep.pem', ostree_remote.tls_ca_path)

    def test_repr(self):
        # we use the dict repr now though
        items = {'url': self.example_url,
                 'a_new_key': 'a_new_value',
                 'gpg-verify': 'true',
                 'blip': 'baz'}
        ostree_remote = \
            model.OstreeRemote.from_config_section(self.section_name,
                                                   items)
        repr_str = repr(ostree_remote)
        self.assertTrue(isinstance(repr_str, six.string_types))
        self.assertTrue('name' in repr_str)
        self.assertTrue('gpg_verify' in repr_str)
        self.assertTrue(self.example_url in repr_str)

    def test_map_gpg(self):
        content = mock.Mock()

        content.gpg = None
        self.assertTrue(model.OstreeRemote.map_gpg(content))

        # any file url is considered enabled
        content.gpg = "file:///path/to/key"
        self.assertTrue(model.OstreeRemote.map_gpg(content))

        # special case the null url of "http://"
        content.gpg = "http://"
        self.assertFalse(model.OstreeRemote.map_gpg(content))

        # regular urls are "enabled"
        content.gpg = "http://some.example.com/not/blip"
        self.assertTrue(model.OstreeRemote.map_gpg(content))


class TestOstreeRemoteFromEntCertContent(fixture.SubManFixture):
    def _content(self):
        content = certificate2.Content(content_type="ostree",
                                       name="content-name",
                                       label="content-test-label",
                                       vendor="Test Vendor",
                                       url="/test.url/test",
                                       gpg="file:///file/gpg/key")
        return content

    def _cert(self):
        cert = mock.Mock()
        cert.path = "/path"
        cert.key_path.return_value = "/key/path"
        return cert

    def test(self):
        remote = self._ent_content_remote('file://path/to/key')
        self.assertTrue(remote.gpg_verify)

    def test_gpg_http(self):
        remote = self._ent_content_remote('http://')
        self.assertFalse(remote.gpg_verify)

    def test_gpg_anything(self):
        remote = self._ent_content_remote('anything')
        self.assertTrue(remote.gpg_verify)

    def test_gpg_none(self):
        remote = self._ent_content_remote(None)
        self.assertTrue(remote.gpg_verify)

    def test_gpg_empty_string(self):
        remote = self._ent_content_remote("")
        self.assertTrue(remote.gpg_verify)

    def test_gpg_no_attr(self):
        content = self._content()
        cert = self._cert()
        ent_cert_content = EntitlementCertContent.from_cert_content(
            content, cert)
        del ent_cert_content.gpg
        remote = model.OstreeRemote.from_ent_cert_content(ent_cert_content)
        self.assertTrue(remote.gpg_verify)

    def _ent_content_remote(self, gpg):
        content = self._content()
        content.gpg = gpg
        cert = self._cert()
        ent_cert_content = EntitlementCertContent.from_cert_content(
            content, cert)
        remote = model.OstreeRemote.from_ent_cert_content(ent_cert_content)
        return remote


class TestOstreeRemotes(fixture.SubManFixture):
    def test(self):
        osr = model.OstreeRemotes()
        self.assertTrue(hasattr(osr, 'data'))

    def test_add_emtpty_ostree_remote(self):
        remote = model.OstreeRemote()
        remotes = model.OstreeRemotes()
        remotes.add(remote)

        self.assertTrue(remote in remotes)

    def test_add_ostree_remote(self):
        remote = model.OstreeRemote()
        remote.url = 'http://example.com/test'
        remote.name = 'awesomeos-remote'
        remote.gpg_verify = 'true'

        remotes = model.OstreeRemotes()
        remotes.add(remote)

        self.assertTrue(remote in remotes)


class BaseOstreeKeyFileTest(fixture.SubManFixture):
    repo_cfg = ""
    """Setup env for testing ostree keyfiles ('config')."""
    pass


class TestOstreeRepoConfig(BaseOstreeKeyFileTest):
    repo_cfg = """
[remote "test-remote"]
url = https://blip.example.com
"""

    def setUp(self):
        super(TestOstreeRepoConfig, self).setUp()

        self.repo_cfg_path = self.write_tempfile(self.repo_cfg)
        self.repo_config = model.OstreeRepoConfig(
            repo_file_path=self.repo_cfg_path.name)

    def test_save(self):
        self.repo_config.load()
        self.repo_config.save()

    def test_save_no_store(self):
        self.repo_config.save()


class TestOstreeConfigRepoFileWriter(BaseOstreeKeyFileTest):
    repo_cfg = """
[remote "test-remote"]
url = https://blip.example.com
"""

    def setUp(self):
        super(TestOstreeConfigRepoFileWriter, self).setUp()

        self.repo_cfg_path = self.write_tempfile(self.repo_cfg)
        self.repo_config = model.OstreeRepoConfig(
            repo_file_path=self.repo_cfg_path.name)
        self.repo_config.load()

    def test_save(self):
        mock_repo_file = mock.Mock()
        rfw = model.OstreeConfigFileWriter(mock_repo_file)

        rfw.save(self.repo_config)

        self.assertTrue(mock_repo_file.save.called)


class TestKeyFileConfigParser(BaseOstreeKeyFileTest):
    repo_cfg = ""

    def test_defaults(self):
        fid = self.write_tempfile(self.repo_cfg)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        # There are no defaults, make sure the rhsm ones are skipped
        self.assertFalse(kf_cfg.has_default('section', 'prop'))
        self.assertEqual(kf_cfg.defaults(), {})

    def test_items(self):
        fid = self.write_tempfile(self.repo_cfg)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertEqual(kf_cfg.items('section'), [])


class TestOstreeRepoConfigUpdates(BaseOstreeKeyFileTest):
    repo_cfg = """
[section_one]
akey = 1
foo = bar

[section_two]
last_key = blippy
"""

    def test_init(self):
        fid = self.write_tempfile(self.repo_cfg)
        ostree_config = model.OstreeRepoConfig(repo_file_path=fid.name)
        new_ostree_config = model.OstreeRepoConfig(repo_file_path=fid.name)

        updates = model.OstreeConfigUpdates(ostree_config, new_ostree_config)
        updates.apply()
        self.assertEqual(updates.orig, updates.new)

        updates.save()


class TestOstreeConfigUpdatesBuilder(BaseOstreeKeyFileTest):
    repo_cfg = """
[section_one]
akey = 1
foo = bar

[section_two]
last_key = blippy
"""

    def test_init(self):
        fid = self.write_tempfile(self.repo_cfg)
        content_set = set()

        ostree_config = model.OstreeConfig(repo_file_path=fid.name)

        mock_content = mock.Mock()
        mock_content.url = "/path/from/base/url"
        mock_content.name = "mock-content-example"
        mock_content.gpg = None

        mock_ent_cert = mock.Mock()
        mock_ent_cert.path = "/somewhere/etc/pki/entitlement/123123.pem"

        mock_content.cert = mock_ent_cert

        content_set.add(mock_content)

        updates_builder = model.OstreeConfigUpdatesBuilder(ostree_config, content_set)
        updates = updates_builder.build()

        self.assertTrue(len(updates.new.remotes))
        self.assertTrue(isinstance(updates.new.remotes[0], model.OstreeRemote))
        self.assertEqual(updates.new.remotes[0].url, mock_content.url)
        #self.assertEquals(updates.new.remotes[0].name, mock_content.name)
        self.assertEqual(updates.new.remotes[0].gpg_verify, True)


class TestKeyFileConfigParserSample(BaseOstreeKeyFileTest):
    repo_cfg = """
[section_one]
akey = 1
foo = bar

[section_two]
last_key = blippy
"""

    def test_sections(self):
        fid = self.write_tempfile(self.repo_cfg)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        self.assert_items_equals(kf_cfg.sections(), ['section_one', 'section_two'])
        self.assertEqual(len(kf_cfg.sections()), 2)

    def test_items(self):
        fid = self.write_tempfile(self.repo_cfg)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        section_one_items = kf_cfg.items('section_one')
        self.assertEqual(len(section_one_items), 2)


class BaseOstreeRepoFileTest(BaseOstreeKeyFileTest):
    repo_cfg = ""

    def _rf_cfg(self):
        self.fid = self.write_tempfile(self.repo_cfg)
        self._rf_cfg_instance = config.KeyFileConfigParser(self.fid.name)
        return self._rf_cfg_instance

    def test_init(self):
        rf_cfg = self._rf_cfg()
        self.assertTrue(isinstance(rf_cfg, config.KeyFileConfigParser))

    def _verify_core(self, rf_cfg):
        self.assertTrue(rf_cfg.has_section('core'))
        self.assertTrue('repo_version' in rf_cfg.options('core'))
        self.assertTrue('mode' in rf_cfg.options('core'))

    def _verify_remote(self, rf_cfg, remote_section):
        self.assertTrue(remote_section in rf_cfg.sections())
        options = rf_cfg.options(remote_section)
        self.assertFalse(options == [])

        self.assertTrue(rf_cfg.has_option(remote_section, 'url'))
        url = rf_cfg.get(remote_section, 'url')
        self.assertTrue(url is not None)
        self.assertTrue(isinstance(url, six.string_types))
        self.assertTrue(' ' not in url)

        self.assertTrue(rf_cfg.has_option(remote_section, 'gpg-verify'))
        gpg_verify = rf_cfg.get(remote_section, 'gpg-verify')
        self.assertTrue(gpg_verify is not None)
        self.assertTrue(gpg_verify in ('true', 'false'))

        self.assertTrue(rf_cfg.has_option(remote_section, 'tls-client-cert-path'))
        self.assertTrue(rf_cfg.has_option(remote_section, 'tls-client-key-path'))
        cert_path = rf_cfg.get(remote_section, 'tls-client-cert-path')
        key_path = rf_cfg.get(remote_section, 'tls-client-key-path')
        self.assertTrue(cert_path is not None)
        self.assertTrue(key_path is not None)
        # Could be, but not for now
        self.assertTrue(cert_path != key_path)
        self.assertTrue('/etc/pki/entitlement' in cert_path)
        self.assertTrue('/etc/pki/entitlement' in key_path)


class TestSampleOstreeRepofileConfigParser(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url = https://awesome.example.com.not.real/
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem
gpg-verify = true
"""

    def test_for_no_rhsm_defaults(self):
        """Verify that the rhsm defaults didn't sneak into the config, which is easy
           since we are subclass the rhsm config parser.
        """
        rf_cfg = self._rf_cfg()
        sections = rf_cfg.sections()
        self.assertFalse('rhsm' in sections)
        self.assertFalse('server' in sections)
        self.assertFalse('rhsmcertd' in sections)

    def test_core(self):
        rf_cfg = self._rf_cfg()
        self._verify_core(rf_cfg)

    def test_remote(self):
        rf_cfg = self._rf_cfg()
        self.assertEqual('true', rf_cfg.get('remote "awesome-ostree-controller"',
                                            'gpg-verify'))


class TestOstreeRepofileConfigParserNotAValidFile(BaseOstreeRepoFileTest):
    repo_cfg = """
id=inrozxa width=100% height=100%>
  <param name=movie value="welcom
ಇದು ಮಾನ್ಯ ಸಂರಚನಾ ಕಡತದ ಅಲ್ಲ. ನಾನು ಮಾಡಲು ಪ್ರಯತ್ನಿಸುತ್ತಿರುವ ಖಚಿತವಿಲ್ಲ, ಆದರೆ ನಾವು ಈ
ಪಾರ್ಸ್ ಹೇಗೆ ಕಲ್ಪನೆಯೂ ಇಲ್ಲ. ನೀವು ಡಾಕ್ಸ್ ಓದಲು ಬಯಸಬಹುದು.
"""

    def test_init(self):
        # just expect any config parser ish error atm,
        # rhsm.config can raise a variety of exceptions all
        # subclasses from configparser.Error
        self.assertRaises(configparser.Error, self._rf_cfg)


class TestOstreeRepoFileOneRemote(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url = http://awesome.example.com.not.real/
gpg-verify = false
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem
"""

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesome-ostree-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_section_is_remote(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')
        self.assertTrue(rf.section_is_remote('remote "awesome-ostree-controller"'))
        self.assertTrue(rf.section_is_remote('remote "rhsm-ostree"'))
        self.assertTrue(rf.section_is_remote('remote "localinstall"'))

        self.assertFalse(rf.section_is_remote('rhsm'))
        self.assertFalse(rf.section_is_remote('core'))
        # string from config file is "false", not boolean False yet
        self.assertEqual('false',
                          rf.config_parser.get('remote "awesome-ostree-controller"', 'gpg-verify'))

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_section_set_remote(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')

        remote = model.OstreeRemote()
        remote.url = "/some/path"
        remote.name = "awesomeos-remote"
        remote.gpg_verify = 'true'
        remote.tls_client_cert_path = "/etc/pki/entitlement/54321.pem"
        remote.tls_client_key_path = "/etc/pki/entitlement/54321-key.pem"

        rf.set_remote(remote)

        expected_proxy = "http://proxy_user:proxy_password@notaproxy.grimlock.usersys.redhat.com:4567"
        repo_proxy_uri = rf.config_parser.get('remote "awesomeos-remote"', 'proxy')
        self.assertEqual(expected_proxy, repo_proxy_uri)

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def section_set_remote(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')

        remote = model.OstreeRemote()
        remote.url = "/some/path"
        remote.name = "awesomeos-remote"
        remote.gpg_verify = 'true'
        remote.tls_client_cert_path = "/etc/pki/entitlement/54321.pem"
        remote.tls_client_key_path = "/etc/pki/entitlement/54321-key.pem"

        rf.set_remote(remote)


class TestOstreeRepoFileNoRemote(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare
"""

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile()
        remotes = rf.remote_sections()

        self.assertFalse('remote "awesmome-ostree-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)
        self.assertEqual(remotes, [])


class TestOstreeRepoFileMultipleRemotes(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url = https://awesome.example.com.not.real/repo/awesomeos7/
gpg-verify = false
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem

[remote "awesomeos-6-controller"]
url = https://awesome.example.com.not.real/repo/awesomeos6/
gpg-verify = false
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem
"""

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesomeos-7-controller"' in remotes)
        self.assertTrue('remote "awesomeos-6-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)

        for remote in remotes:
            self._verify_remote(self._rf_cfg_instance, remote)


# Unsure what we should do in this case, if we dont throw
# an error on read, we will likely squash the dupes to one
# remote on write. Which is ok?
class TestOstreeRepoFileNonUniqueRemotes(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
gpg-verify=false
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
gpg-verify=false
tls-client-cert-path = /etc/pki/entitlement/12345.pem
tls-client-key-path = /etc/pki/entitlement/12345-key.pem

"""

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesomeos-7-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)

        for remote in remotes:
            self._verify_remote(self._rf_cfg_instance, remote)


class TestOstreeRepofileAddSectionWrite(BaseOstreeRepoFileTest):
    repo_cfg = ""

    def test_add_remote(self):
        fid = self.write_tempfile(self.repo_cfg)
        rf_cfg = config.KeyFileConfigParser(fid.name)

        remote_name = 'remote "awesomeos-8-container"'
        url = "https://example.com.not.real/repo"
        gpg_verify = "true"

        rf_cfg.add_section(remote_name)
        self.assertTrue(rf_cfg.has_section(remote_name))
        rf_cfg.save()

        new_contents = open(fid.name, 'r').read()
        self.assertTrue('awesomeos-8' in new_contents)

        rf_cfg.set(remote_name, 'url', url)
        rf_cfg.save()

        new_contents = open(fid.name, 'r').read()
        self.assertTrue(url in new_contents)

        rf_cfg.set(remote_name, 'gpg-verify', gpg_verify)
        rf_cfg.save()

        new_contents = open(fid.name, 'r').read()
        self.assertTrue('gpg-verify' in new_contents)
        self.assertTrue(gpg_verify in new_contents)
        self.assertTrue('gpg-verify = true' in new_contents)

        new_rf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertTrue(new_rf_cfg.has_section(remote_name))
        self.assertEqual(new_rf_cfg.get(remote_name, 'url'), url)


class TestOstreeRepoFileRemoveSectionSave(BaseOstreeRepoFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url = https://awesome.example.com.not.real/repo/awesomeos7/
gpg-verify = false

[remote "awesomeos-6-controller"]
url = https://awesome.example.com.not.real/repo/awesomeos6/
gpg-verify = true
"""

    def test_remove_section(self):
        fid = self.write_tempfile(self.repo_cfg)
        rf_cfg = config.KeyFileConfigParser(fid.name)
        remote_to_remove = 'remote "awesomeos-7-controller"'
        self.assertTrue(rf_cfg.has_section(remote_to_remove))

        rf_cfg.remove_section(remote_to_remove)
        self.assertFalse(rf_cfg.has_section(remote_to_remove))
        rf_cfg.save()
        self.assertFalse(rf_cfg.has_section(remote_to_remove))

        new_contents = open(fid.name, 'r').read()
        self.assertFalse(remote_to_remove in new_contents)
        self.assertFalse('gpg-verify = false' in new_contents)

        new_rf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertFalse(new_rf_cfg.has_section(remote_to_remove))


class TestOsTreeContents(fixture.SubManFixture):

    def create_content(self, content_type, name):
        """ Create dummy entitled content object. """
        content = certificate2.Content(
            content_type=content_type,
            name="mock_content_%s" % name,
            label=name,
            enabled=True,
            required_tags=[],
            gpg="path/to/gpg",
            url="http://mock.example.com/%s/" % name)
        return EntitlementCertContent.from_cert_content(content)

    def test_ent_source(self):
        yc = self.create_content("yum", "yum_content")
        oc = self.create_content("ostree", "ostree_content")

        ent1 = Entitlement(contents=[yc])
        ent2 = Entitlement(contents=[oc])

        ent_src = EntitlementSource()
        ent_src._entitlements = [ent1, ent2]

        contents = find_content(ent_src,
            content_type=action_invoker.OSTREE_CONTENT_TYPE)
        self.assertEqual(len(contents), 1)

        for content in contents:
            self.assertEqual(content.content_type,
                action_invoker.OSTREE_CONTENT_TYPE)

    def test_ent_source_product_tags(self):
        yc = self.create_content("yum", "yum_content")
        oc = self.create_content("ostree", "ostree_content")

        ent1 = Entitlement(contents=[yc])
        ent2 = Entitlement(contents=[oc])

        ent_src = EntitlementSource()
        ent_src._entitlements = [ent1, ent2]

        # faux product_tags to hit find_content, but no content tags
        ent_src.product_tags = ['awesomeos-ostree-1', 'awesomeos-ostree-super']

        contents = find_content(ent_src,
            content_type=action_invoker.OSTREE_CONTENT_TYPE)
        self.assertEqual(len(contents), 1)

        for content in contents:
            self.assertEqual(content.content_type,
                action_invoker.OSTREE_CONTENT_TYPE)

    def test_ent_source_product_tags_and_content_tags(self):
        oc = self.create_content("ostree", "ostree_content")
        oc.tags = ['awesomeos-ostree-1']

        ent = Entitlement(contents=[oc])

        ent_src = EntitlementSource()
        ent_src._entitlements = [ent]

        # faux product_tags to hit find_content, but no content tags
        ent_src.product_tags = ['awesomeos-ostree-1', 'awesomeos-ostree-super']

        contents = find_content(ent_src,
            content_type=action_invoker.OSTREE_CONTENT_TYPE)
        print("contents", contents)
        self.assertEqual(len(contents), 1)

        for content in contents:
            self.assertEqual(content.content_type,
                action_invoker.OSTREE_CONTENT_TYPE)


class TestContentUpdateActionReport(fixture.SubManFixture):
    def test_empty(self):
        report = action_invoker.OstreeContentUpdateActionReport()
        self.assertEqual(report.remote_updates, [])

    def test_print_empty(self):
        report = action_invoker.OstreeContentUpdateActionReport()
        text = "%s" % report
        self.assertTrue(text != "")

    def test_updates_empty(self):
        report = action_invoker.OstreeContentUpdateActionReport()
        self.assertEqual(report.updates(), 0)

    def test_report(self):
        report = action_invoker.OstreeContentUpdateActionReport()
        remotes = model.OstreeRemotes()
        remote = model.OstreeRemote()
        remote.url = "http://example.com"
        remote.name = "example-remote"
        remote.gpg_verify = "true"

        remotes.add(remote)
        report.remote_updates = remotes

        text = "%s" % report
        # FIXME: validate format
        self.assertTrue(text != "")


class TestOstreeContentUpdateActionCommand(fixture.SubManFixture):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url=http://awesome.example.com.not.real/
branches=awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=true

[remote "another-awesome-ostree-controller"]
url=http://another-awesome.example.com.not.real/
branches=another-awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=true
"""

    @mock.patch("subscription_manager.plugin.ostree.model.OstreeConfigFileStore")
    def test_empty(self, mock_file_store):
        # FIXME: This does no validation
        mock_repo_file = mock.Mock()
        mock_repo_file.get_core.return_value = {}

        mock_file_store.load.return_value = mock_repo_file

        ent_src = EntitlementSource()
        action = action_invoker.OstreeContentUpdateActionCommand(
            ent_source=ent_src)
        action.update_origin_file = mock.Mock()
        action.perform()
