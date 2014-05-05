
# import subman fixture
# override plugin manager with one that provides
#  the ostree content plugin

# test tree format
#
# test repo model
#

# test constructing from Content models
# ignores wrong content type
import StringIO

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


class TestOstreePluginRepoFileConfigParser(fixture.SubManFixture):
    sample_repo_config = """
[core]
repo_version=1
mode=bare

[remote "rh-atomic-controller"]
url=http://rcm-img06.build.bos.redhat.com/repo
branches=rh-atomic-controller/el7/x86_64/buildmaster/controller/docker;
gpg-verify=false
"""

    def _get_fo(self, buf):
        return StringIO.StringIO(buf)

    def test_empty(self):
        repo_file.RepoFile()

    def _read_sample(self):
        rf = repo_file.RepoFileConfigParser()
        rf.readfp(self._get_fo(self.sample_repo_config))
        return rf

    def test_sample_core(self):
        rf = self._read_sample()
        self.assertTrue(rf.has_section('core'))
