#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

import os, sys
sys.path.append('/usr/share/rhsm')
from yum import config
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE, PluginYumExit
from repolib import URL, RepoLib

requires_api_version = '2.3'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)


class SetVersionCommand:

    def getNames(self):
        return ["setversion", "set-version"]

    def getUsage(self):
        return "[repo][version]"

    def getSummary(self):
        return "Set the value for $version for the specified repo."

    def doCheck(self, base, basecmd, extcmds):
        if base.conf.uid:
            raise PluginYumExit, \
                'You need to be root to perform this command.'
        if len(extcmds) < 2:
            raise PluginYumExit, \
                'You need to specify a repo and version'

    def doCommand(self, base, basecmd, extcmds):
        print 'set version %s' % str(extcmds)
        # TODO: call repolib
        return (0, ('done',))


class ListVersionsCommand:

    def getNames(self):
        return ["listversions", "list-versions"]

    def getUsage(self):
        return "[repo]"

    def getSummary(self):
        return "List the available values for $version for the specified repo."

    def doCheck(self, base, basecmd, extcmds):
        if not len(extcmds):
            raise PluginYumExit, \
                'You need to specify a repo.'

    def doCommand(self, base, basecmd, extcmds):
        result = []
        # TODO: call repolib
        return (0, result)


def init_hook(conduit):
    for repo in conduit.getRepos().listEnabled():
        version = getattr(repo, URL.VERSION[1:])
        if version:
            repo.baseurl = URL.replaceVersions(repo.baseurl, version)
            continue
        if URL.needsVersion(repo.baseurl):
            repo.disable()


def config_hook(conduit):
    conduit.registerCommand(SetVersionCommand())
    conduit.registerCommand(ListVersionsCommand())
    setattr(config.RepoConf, URL.VERSION[1:], config.Option())
    return
    try:
        if os.getuid() != 0:
            conduit.info(2, 'Not root, Red Hat repository not updated')
            return
        rl = RepoLib()
        rl.update()
    except Exception, ex:
        conduit.error(2, str(ex))

