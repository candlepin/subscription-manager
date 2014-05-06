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
import tempfile

import mock

import fixture

from content_plugins.ostree import action_invoker
from content_plugins.ostree import repo_file


class StubPluginManager(object):
        pass


class TestOstreeActionInvoker(fixture.SubManFixture):

    def setUp(self):
        super(TestOstreeActionInvoker, self).setUp()

        # need to provide at least one the content_plugin_search

    def test_invoker(self):
        invoker = action_invoker.OstreeContentActionInvoker()
        invoker.update()


class TestOstreeUpdateActionCommand(fixture.SubManFixture):
    def test_command_init(self):
        action_command = action_invoker.OstreeContentUpdateActionCommand()
        self.assertTrue(hasattr(action_command, 'report'))


class TestOstreeUpdateActionReport(fixture.SubManFixture):
    def test_init(self):
        action_invoker.OstreeContentUpdateActionReport()


class MockConfigFile(object):
    empty = ""
    no_core = """
[remote "foo-bar"]
url=http://example.notreal
gpg-verify=false
"""

    def __init__(self, buf=None):
        self.buf = buf

    def open(self):
        return mock.mock_open(read_data=self.buf)

    def open_empty(self):
        return mock.mock_open(read_data=self.empty)

    def open_no_core(self):
        return mock.mock_open(read_data=self.no_core)


mock_config_file = MockConfigFile()

class BaseOstreeRepofileTest(fixture.SubManFixture):
    cfgfile_data = ""
    def setUp(self):
        super(BaseOstreeRepofileTest, self).setUp()

        # sigh, config classes (ours included) are terrible
        # create a temp file for use as a config file. This should get cleaned
        # up magically at the end of the run.
        self.fid = tempfile.NamedTemporaryFile(mode='w+b', suffix='.tmp')
        self.fid.write(self.cfgfile_data)
        self.fid.seek(0)

        #self.cfgParser = RhsmConfigParser(self.fid.name)

    def _rf_cfg(self):
        self._rf_cfg_instance = repo_file.RepoFileConfigParser(self.fid.name)
        return self._rf_cfg_instance

    def test_init(self):
        rf_cfg = self._rf_cfg()
        self.assertTrue(isinstance(rf_cfg, repo_file.RepoFileConfigParser))

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


class TestSampleOstreeRepofileConfigParser(BaseOstreeRepofileTest):
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


class TestOstreeRepofileConfigParserNotAValidFile(BaseOstreeRepofileTest):
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

class TestOstreeRepoFileOneRemote(BaseOstreeRepofileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare

[remote "awesome-ostree-controller"]
url=http://awesome.example.com.not.real/
branches=awesome-ostree-controller/awesome7/x86_64/controller/docker;
gpg-verify=false
"""

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesome-ostree-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_section_is_remote(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
        self.assertTrue(rf.section_is_remote('remote "awesome-ostree-controller"'))
        self.assertTrue(rf.section_is_remote('remote "rhsm-ostree"'))
        self.assertTrue(rf.section_is_remote('remote "localinstall"'))

        self.assertFalse(rf.section_is_remote('rhsm'))
        self.assertFalse(rf.section_is_remote('core'))


class TestOstreeRepoFileNoRemote(BaseOstreeRepofileTest):
    cfgfile_data = """
[core]
repo_version=1
mode=bare
"""

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
        remotes = rf.remote_sections()

        self.assertFalse('remote "awesmome-ostree-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)
        self.assertEquals(remotes, [])


class TestOstreeRepoFileMultipleRemotes(BaseOstreeRepofileTest):
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

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
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
class TestOstreeRepoFileNonUniqueRemotes(BaseOstreeRepofileTest):
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

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesomeos-7-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)
