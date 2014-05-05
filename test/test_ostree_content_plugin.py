
# import subman fixture
# override plugin manager with one that provides
#  the ostree content plugin

# test tree format
#
# test repo model
#

# test constructing from Content models
# ignores wrong content type

import fixture

from content_plugins import ostree
from content_plugins.ostree import action_invoker
from content_plugins.ostree import repo_file


class StubPluginManager(object):
    def run(self, hook, *args, **kwargs):
        pass


class TestOstreePlugin(fixture.SubManFixture):

    def setUp(self):
        super(TestOstreePlugin, self).setUp()

        # need to provide at least one the content_plugin_search

    def test_invoker(self):
        invoker = action_invoker.OstreeContentActionInvoker()
        invoker.update()


sample_repo_config = """
[core]
repo_version=1
mode=bare

[remote "rh-atomic-controller"]
url=http://rcm-img06.build.bos.redhat.com/repo
branches=rh-atomic-controller/el7/x86_64/buildmaster/controller/docker;
gpg-verify=false
"""


class TestOstreePluginRepoFile(fixture.SubManFixture):
    def test_empty(self):
        rf = repo_file.RepoFile()

