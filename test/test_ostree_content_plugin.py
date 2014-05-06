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


class BaseOstreeKeyFileTest(fixture.SubManFixture):
    """Setup env for testing ostree keyfiles ('config' and '.origin')."""
    cfgfile_data = ""

    def setUp(self):
        super(BaseOstreeKeyFileTest, self).setUp()

        # sigh, config classes (ours included) are terrible
        # create a temp file for use as a config file. This should get cleaned
        # up magically at the end of the run.
        self.fid = tempfile.NamedTemporaryFile(mode='w+b', suffix='.tmp')
        self.fid.write(self.cfgfile_data)
        self.fid.seek(0)


class BaseOstreeOriginFileTest(BaseOstreeKeyFileTest):
    """Base of tests for ostree *.origin config files."""
    def _of_cfg(self):
        self._of_cfg_instance = repo_file.OriginFileConfigParser(self.fid.name)
        return self._of_cfg_instance

    def test_init(self):
        of_cfg = self._of_cfg()
        self.assertTrue(isinstance(of_cfg, repo_file.OriginFileConfigParser))


class TestKeyFileConfigParser(BaseOstreeKeyFileTest):
    def test_defaults(self):
        kf_cfg = repo_file.KeyFileConfigParser(self.fid.name)
        # There are no defaults, make sure the rhsm ones are skipped
        self.assertFalse(kf_cfg.has_default('section', 'prop'))
        self.assertEquals(kf_cfg.defaults(), {})

    def test_items(self):
        kf_cfg = repo_file.KeyFileConfigParser(self.fid.name)
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
        kf_cfg = repo_file.KeyFileConfigParser(self.fid.name)
        self.assert_items_equals(kf_cfg.sections(), ['section_one', 'section_two'])
        self.assertEquals(len(kf_cfg.sections()), 2)

    def test_items(self):
        kf_cfg = repo_file.KeyFileConfigParser(self.fid.name)
        section_one_items = kf_cfg.items('section_one')
        self.assertEquals(len(section_one_items), 2)


class TestOstreeOriginFileConfigParserEmpty(BaseOstreeOriginFileTest):
    """Test if a .origin file is empty."""
    cfgfile_data = ""

    def test_has_origin(self):
        of_cfg = self._of_cfg()
        self.assertFalse(of_cfg.has_section('origin'))
        self.assertEquals(of_cfg.sections(), [])


class TestOstreeOriginFileConfigParser(BaseOstreeOriginFileTest):
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
        o_cfg = repo_file.OstreeConfigFile(self.fid.name)
        self.assertTrue(isinstance(o_cfg, repo_file.OstreeConfigFile))


class BaseOstreeRepoFileTest(BaseOstreeKeyFileTest):
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


class TestOstreeRepoFileNoRemote(BaseOstreeRepoFileTest):
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

    @mock.patch('content_plugins.ostree.repo_file.RepoFile._get_config_parser')
    def test_remote_sections(self, mock_get_config_parser):
        mock_get_config_parser.return_value = self._rf_cfg()
        rf = repo_file.RepoFile(self.fid.name)
        remotes = rf.remote_sections()
        self.assertTrue('remote "awesomeos-7-controller"' in remotes)
        self.assertFalse('core' in remotes)
        self.assertFalse('rhsm' in remotes)


class TestOstreeRepofileAddSectionWrite(BaseOstreeRepoFileTest):
    cfgfile_data = ""

    def test_add_remote(self):
        rf_cfg = self._rf_cfg()

        remote_name = 'remote "awesomeos-8-container"'
        url = "http://example.com.not.real/repo"
        branches = "branches;foo;bar"
        gpg_verify = "true"

        rf_cfg.add_section(remote_name)
        self.assertTrue(rf_cfg.has_section(remote_name))
        rf_cfg.save()

        new_contents = open(self.fid.name, 'r').read()
        self.assertTrue('awesomeos-8' in new_contents)

        rf_cfg.set(remote_name, 'url', url)
        rf_cfg.save()

        new_contents = open(self.fid.name, 'r').read()
        self.assertTrue(url in new_contents)

        rf_cfg.set(remote_name, 'branches', branches)
        rf_cfg.save()

        new_contents = open(self.fid.name, 'r').read()
        self.assertTrue(branches in new_contents)

        rf_cfg.set(remote_name, 'gpg-verify', gpg_verify)
        rf_cfg.save()

        new_contents = open(self.fid.name, 'r').read()
        self.assertTrue('gpg-verify' in new_contents)
        self.assertTrue(gpg_verify in new_contents)

        new_rf_cfg = self._rf_cfg()
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
        rf_cfg = self._rf_cfg()
        remote_to_remove = 'remote "awesomeos-7-controller"'
        self.assertTrue(rf_cfg.has_section(remote_to_remove))

        rf_cfg.remove_section(remote_to_remove)
        self.assertFalse(rf_cfg.has_section(remote_to_remove))
        rf_cfg.save()
        self.assertFalse(rf_cfg.has_section(remote_to_remove))

        new_contents = open(self.fid.name, 'r').read()
        self.assertFalse(remote_to_remove in new_contents)

        new_rf_cfg = self._rf_cfg()
        self.assertFalse(new_rf_cfg.has_section(remote_to_remove))
