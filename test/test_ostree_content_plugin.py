#
# -*- coding: utf-8 -*-
# import subman fixture
# override plugin manager with one that provides
#  the ostree content plugin

# test tree format
#
# test repo model
#

# test constructing from Content models
# ignores wrong content type
import ConfigParser

import mock

import fixture

from subscription_manager.plugin.ostree import config
from subscription_manager.plugin.ostree import model


class StubPluginManager(object):
        pass


class TestOstreeRemoteNameFromSection(fixture.SubManFixture):
    def test_normal(self):
        sn = r'remote "awesomeos-foo-container"'
        name = model.OstreeRemote.name_from_section(sn)
        self.assertTrue(name is not None)
        self.assertEquals(name, "awesomeos-foo-container")
        # no quotes in the name
        self.assertFalse('"' in name)

    def test_spaces(self):
        # We consider remote names to be content labels, so
        # shouldn't have space, but afaik ostree doesn't care
        sn = r'remote "awesome os container"'
        name = model.OstreeRemote.name_from_section(sn)
        self.assertTrue(name is not None)
        self.assertEquals(name, "awesome os container")
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
        self.assertEquals('true', ostree_remote.gpg_verify)
        self.assertEquals(self.example_url, ostree_remote.url)

    def test_other_items(self):
        items = {'url': self.example_url,
                 'a_new_key': 'a_new_value',
                 'gpg-verify': 'true',
                 'blip': 'baz'}
        ostree_remote = \
            model.OstreeRemote.from_config_section(self.section_name,
                                                   items)
        self.assert_remote(ostree_remote)
        # .url and data['url'] work
        self.assertEquals(self.example_url, ostree_remote.url)
        self.assertEquals(self.example_url, ostree_remote.data['url'])

        self.assertTrue('a_new_key' in ostree_remote)
        self.assertEquals('a_new_value', ostree_remote.data['a_new_key'])

        self.assertTrue('gpg_verify' in ostree_remote)
        self.assertTrue(hasattr(ostree_remote, 'gpg_verify'))
        self.assertEquals('true', ostree_remote.gpg_verify)
        self.assertFalse('gpg-verify' in ostree_remote)
        self.assertFalse(hasattr(ostree_remote, 'gpg-verify'))

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
        self.assertTrue(isinstance(repr_str, basestring))
        self.assertTrue('name' in repr_str)
        self.assertTrue('gpg_verify' in repr_str)
        self.assertTrue(self.example_url in repr_str)


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


# TODO: This class may not be needed, technically not doing anything
# since write_tempfile moved to subman fixture.
class BaseOstreeKeyFileTest(fixture.SubManFixture):
    """Setup env for testing ostree keyfiles ('config' and '.origin')."""
    cfgfile_data = ""

    def setUp(self):
        super(BaseOstreeKeyFileTest, self).setUp()


class TestOstreeConfig(BaseOstreeKeyFileTest):
    repo_cfg = """
[remote "test-remote"]
url=http://blip.example.com
"""

    def setUp(self):
        super(TestOstreeConfig, self).setUp()

        self.repo_cfg_path = self.write_tempfile(self.repo_cfg)
        self.repo_config = model.OstreeConfig(
            repo_file_path=self.repo_cfg_path.name)

    def test_save(self):
        self.repo_config.load()
        self.repo_config.save()

    def test_save_no_store(self):
        self.repo_config.save()


class TestOstreeConfigRepoFileWriter(BaseOstreeKeyFileTest):
    repo_cfg = """
[remote "test-remote"]
url=http://blip.example.com
"""

    def setUp(self):
        super(TestOstreeConfigRepoFileWriter, self).setUp()

        self.repo_cfg_path = self.write_tempfile(self.repo_cfg)
        self.repo_config = model.OstreeConfig(
            repo_file_path=self.repo_cfg_path.name)
        self.repo_config.load()

    def test_save(self):
        mock_repo_file = mock.Mock()
        rfw = model.OstreeConfigRepoFileWriter(mock_repo_file)

        rfw.save(self.repo_config)

        self.assertTrue(mock_repo_file.save.called)


class TestKeyFileConfigParser(BaseOstreeKeyFileTest):
    def test_defaults(self):
        fid = self.write_tempfile(self.cfgfile_data)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        # There are no defaults, make sure the rhsm ones are skipped
        self.assertFalse(kf_cfg.has_default('section', 'prop'))
        self.assertEquals(kf_cfg.defaults(), {})

    def test_items(self):
        fid = self.write_tempfile(self.cfgfile_data)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertEquals(kf_cfg.items('section'), [])


class TestKeyFileConfigParserSample(BaseOstreeKeyFileTest):
    cfgfile_data = """
[section_one]
akey = 1
foo = bar

[section_two]
last_key = blippy
"""

    def test_sections(self):
        fid = self.write_tempfile(self.cfgfile_data)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        self.assert_items_equals(kf_cfg.sections(), ['section_one', 'section_two'])
        self.assertEquals(len(kf_cfg.sections()), 2)

    def test_items(self):
        fid = self.write_tempfile(self.cfgfile_data)
        kf_cfg = config.KeyFileConfigParser(fid.name)
        section_one_items = kf_cfg.items('section_one')
        self.assertEquals(len(section_one_items), 2)


class TestReplaceRefspecRemote(fixture.SubManFixture):

    def test_successful_replace(self):
        refspec = 'awesomeos-controller:awesomeos-controller/awesomeos8/x86_64/controller/docker'
        expected = 'newremote:awesomeos-controller/awesomeos8/x86_64/controller/docker'
        self.assertEquals(expected, config.replace_refspec_remote(
            refspec, 'newremote'))

    def test_empty_remote(self):
        refspec = ':awesomeos-controller/awesomeos8/x86_64/controller/docker'
        expected = 'newremote:awesomeos-controller/awesomeos8/x86_64/controller/docker'
        self.assertEquals(expected, config.replace_refspec_remote(
            refspec, 'newremote'))

    def test_bad_refspec(self):
        refspec = 'ImNotARefSpec'
        self.assertRaises(Exception, config.replace_refspec_remote,
            refspec, 'newremote')


class TestOstreeOriginUpdater(BaseOstreeKeyFileTest):
    repo_cfg = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url=http://awesome.example.com.not.real/
branches=awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=false

[remote "another-awesome-ostree-controller"]
url=http://another-awesome.example.com.not.real/
branches=another-awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=false
"""

    origin_cfg = """
[origin]
refspec=origremote:awesome-ostree-controller/awesomeos8/x86_64/controller/docker
"""

    def setUp(self):
        super(TestOstreeOriginUpdater, self).setUp()
        fixture.SubManFixture.setUp(self)

        self.origin_cfg_path = self.write_tempfile(self.origin_cfg)
        self.repo_cfg_path = self.write_tempfile(self.repo_cfg)
        self.repo_config = model.OstreeConfig(
            repo_file_path=self.repo_cfg_path.name)
        self.repo_config.load()
        self.updater = model.OstreeOriginUpdater(self.repo_config)
        self.updater._get_deployed_origin = mock.MagicMock(
            return_value=self.origin_cfg_path.name)

    def test_simple_update(self):
        self.updater.run()
        #self.assertEquals(1, 2)
        # Reload the origin file and make sure it looks right:
        new_origin = config.KeyFileConfigParser(
            self.origin_cfg_path.name)
        print dir(new_origin)
        print new_origin.sections()
        self.assertTrue(new_origin.has_section('origin'))
        self.assertTrue('refspec' in new_origin.options('origin'))
        self.assertTrue("awesome-ostree-controller" in
            new_origin.get('origin', 'refspec'))
        self.assertFalse('origremote' in
            new_origin.get('origin', 'refspec'))


class BaseOstreeOriginFileTest(BaseOstreeKeyFileTest):
    """Base of tests for ostree *.origin config files."""
    def _of_cfg(self):
        fid = self.write_tempfile(self.cfgfile_data)
        self._of_cfg_instance = config.KeyFileConfigParser(
            fid.name)
        return self._of_cfg_instance


class TestOriginFileConfigParserEmpty(BaseOstreeOriginFileTest):
    """Test if a .origin file is empty."""
    cfgfile_data = ""

    def test_has_origin(self):
        of_cfg = self._of_cfg()
        self.assertFalse(of_cfg.has_section('origin'))
        self.assertEquals(of_cfg.sections(), [])


class TestOriginFileConfigParser(BaseOstreeOriginFileTest):
    """Test a normalish .origin file."""
    cfgfile_data = """
[origin]
refspec=awesomeos-controller:awesomeos-controller/awesomeos8/x86_64/controller/docker
"""

    def test_has_origin(self):
        of_cfg = self._of_cfg()
        self.assertTrue(of_cfg.has_section('origin'))
        self.assertEquals(len(of_cfg.sections()), 1)

    def test_has_refspec(self):
        of_cfg = self._of_cfg()
        self.assertTrue(of_cfg.get('origin', 'refspec'))
        self.assertTrue("awesomeos-controller" in of_cfg.get('origin', 'refspec'))


class TestOstreeConfigFile(BaseOstreeOriginFileTest):
    cfgfile_data = """
[origin]
refspec=awesomeos-controller:awesomeos-controller/awesomeos8/x86_64/controller/docker
"""

    def test_init(self):
        fid = self.write_tempfile(self.cfgfile_data)
        o_cfg = config.BaseOstreeConfigFile(fid.name)
        self.assertTrue(isinstance(o_cfg, config.BaseOstreeConfigFile))


class BaseOstreeRepoFileTest(BaseOstreeKeyFileTest):
    def _rf_cfg(self):
        self.fid = self.write_tempfile(self.cfgfile_data)
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
        self.assertTrue(rf_cfg.has_option(remote_section, 'branches'))
        self.assertTrue(rf_cfg.has_option(remote_section, 'gpg-verify'))


class TestSampleOstreeRepofileConfigParser(BaseOstreeRepoFileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url=http://awesome.example.com.not.real/
branches=awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=false
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


class TestOstreeRepofileConfigParserNotAValidFile(BaseOstreeRepoFileTest):
    cfgfile_data = """
id=inrozxa width=100% height=100%>
  <param name=movie value="welcom
ಇದು ಮಾನ್ಯ ಸಂರಚನಾ ಕಡತದ ಅಲ್ಲ. ನಾನು ಮಾಡಲು ಪ್ರಯತ್ನಿಸುತ್ತಿರುವ ಖಚಿತವಿಲ್ಲ, ಆದರೆ ನಾವು ಈ
ಪಾರ್ಸ್ ಹೇಗೆ ಕಲ್ಪನೆಯೂ ಇಲ್ಲ. ನೀವು ಡಾಕ್ಸ್ ಓದಲು ಬಯಸಬಹುದು.
"""

    def test_init(self):
        # just expect any config parser ish error atm,
        # rhsm.config can raise a variety of exceptions all
        # subclasses from ConfigParser.Error
        self.assertRaises(ConfigParser.Error, self._rf_cfg)


class TestOstreeRepoFileOneRemote(BaseOstreeRepoFileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url=http://awesome.example.com.not.real/
branches=awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=false
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


class TestOstreeRepoFileNoRemote(BaseOstreeRepoFileTest):
    cfgfile_data = """
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
        self.assertEquals(remotes, [])


class TestOstreeRepoFileMultipleRemotes(BaseOstreeRepoFileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
branches=awesomeos-7-controller/awesomeos7/x86_64/controller/docker;
gpg-verify=false


[remote "awesomeos-6-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos6/
branches=awesomeos-6-controller/awesomeos6/x86_64/controller/docker;
gpg-verify=false
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
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
branches=awesomeos-7-controller/awesomeos7/x86_64/controller/docker;
gpg-verify=false

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
branches=awesomeos-7-controller/awesomeos7/x86_64/controller/docker;
gpg-verify=false

"""

    @mock.patch('subscription_manager.plugin.ostree.config.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = config.RepoFile('')
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesomeos-7-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)


class TestOstreeRepofileAddSectionWrite(BaseOstreeRepoFileTest):
    cfgfile_data = ""

    def test_add_remote(self):
        fid = self.write_tempfile(self.cfgfile_data)
        rf_cfg = config.KeyFileConfigParser(fid.name)

        remote_name = 'remote "awesomeos-8-container"'
        url = "http://example.com.not.real/repo"
        branches = "branches;foo;bar"
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

        rf_cfg.set(remote_name, 'branches', branches)
        rf_cfg.save()

        new_contents = open(fid.name, 'r').read()
        self.assertTrue(branches in new_contents)

        rf_cfg.set(remote_name, 'gpg-verify', gpg_verify)
        rf_cfg.save()

        new_contents = open(fid.name, 'r').read()
        self.assertTrue('gpg-verify' in new_contents)
        self.assertTrue(gpg_verify in new_contents)

        new_rf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertTrue(new_rf_cfg.has_section(remote_name))
        self.assertEquals(new_rf_cfg.get(remote_name, 'url'), url)


class TestOstreeRepoFileRemoveSectionSave(BaseOstreeRepoFileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesomeos-7-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos7/
branches=awesomeos-7-controller/awesomeos7/x86_64/controller/docker;
gpg-verify=false

[remote "awesomeos-6-controller"]
url=http://awesome.example.com.not.real/repo/awesomeos6/
branches=awesomeos-6-controller/awesomeos6/x86_64/controller/docker;
gpg-verify=false
"""

    def test_remove_section(self):
        fid = self.write_tempfile(self.cfgfile_data)
        rf_cfg = config.KeyFileConfigParser(fid.name)
        remote_to_remove = 'remote "awesomeos-7-controller"'
        self.assertTrue(rf_cfg.has_section(remote_to_remove))

        rf_cfg.remove_section(remote_to_remove)
        self.assertFalse(rf_cfg.has_section(remote_to_remove))
        rf_cfg.save()
        self.assertFalse(rf_cfg.has_section(remote_to_remove))

        new_contents = open(fid.name, 'r').read()
        self.assertFalse(remote_to_remove in new_contents)

        new_rf_cfg = config.KeyFileConfigParser(fid.name)
        self.assertFalse(new_rf_cfg.has_section(remote_to_remove))
