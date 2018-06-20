from __future__ import print_function, division, absolute_import

# Copyright (C) 2015  Red Hat, Inc.
#
# Authors: Valentina Mukhamedzhanova <vmukhame@redhat.com>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.

import logging
import fnmatch

from subscription_manager import api

from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE
from yum.constants import TS_INSTALL_STATES
from yum import Errors

requires_api_version = '2.7'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)

PLUGIN_CONF_PATH = '/etc/yum/pluginconf.d/search-disabled-repos.conf'
DEFAULT_IGNORED_REPOS = ('*debug-rpms', '*source-rpms', '*beta-rpms', '*htb-rpms')

attempted = False
old_enabled_repos = []


def postresolve_hook(conduit):
    if not conduit.missing_requires:
        return

    repo_storage = conduit.getRepos()
    ignored_repos = conduit.confList('main', 'ignored_repos', default=DEFAULT_IGNORED_REPOS)
    disabled_repos = set((repo for repo in list(repo_storage.repos.values())
                                        if not repo.enabled and is_repo_important(repo, ignored_repos)))
    if not disabled_repos:
        return

    notify_only = conduit.confBool('main', 'notify_only', default=True)
    if notify_only:
        suggest_enabling(conduit)
        return

    if prompt_temporarily_enable_repos(conduit):
        conduit.info(logging.DEBUG, 'Depsolving failed due to missing dependencies, temporarily enabling repos...')
        global attempted
        attempted = True
        global old_enabled_repos
        old_enabled_repos = set((repo.id for repo in repo_storage.listEnabled()))
        for repo in disabled_repos:
            repo.enable()
            try:
                repo_storage.populateSack(which=repo.id)
                conduit.info(logging.DEBUG, 'Repo temporarily enabled: %s' % repo.id)
            except Errors.RepoError:
                repo.disable()
                conduit.info(logging.DEBUG, 'Failed to temporarily enable repo: %s' % repo.id)
        conduit.getTsInfo().changed = True


def postverifytrans_hook(conduit):
    if not attempted:
        return

    used_repos = set(p.repoid for p in conduit.getTsInfo().getMembersWithState(output_states=TS_INSTALL_STATES))
    helpful_new_repos = used_repos - old_enabled_repos

    if prompt_permanently_enable_repos(conduit, helpful_new_repos):
        for repo in helpful_new_repos:
            try:
                enabled = api.enable_yum_repositories(repo)
            except Exception:
                enabled = 0

            if enabled:
                conduit.info(logging.DEBUG, 'Repo permanently enabled: %s' % repo)
            else:
                conduit.info(logging.DEBUG, 'Failed to permanently enable repo: %s' % repo)


def is_repo_important(repo, ignored_repos):
    if repo.repofile != '/etc/yum.repos.d/redhat.repo':
        return False

    return not any(fnmatch.fnmatch(repo.id, pattern) for pattern in ignored_repos)


def suggest_enabling(conduit):
    msg = conduit.pretty_output_restring() + """\n**********************************************************************
yum can be configured to try to resolve such errors by temporarily enabling
disabled repos and searching for missing dependencies.
To enable this functionality please set 'notify_only=0' in %s
**********************************************************************\n""" % PLUGIN_CONF_PATH
    conduit.info(1, msg)  # yum's debuglevel 1


def prompt_temporarily_enable_repos(conduit):
    msg = conduit.pretty_output_restring() + """\n**********************************************************************
Dependency resolving failed due to missing dependencies.
Some repositories on your system are disabled, but yum can enable them
and search for missing dependencies. This will require downloading
metadata for disabled repositories and may take some time and traffic.
**********************************************************************\n"""
    prompt = 'Enable all repositories and try again? [y/N]: '
    return conduit.promptYN(msg, prompt=prompt)


def prompt_permanently_enable_repos(conduit, repos):
    repos_str = '\n'.join(repo for repo in repos)
    msg = """*******************************************************************
Dependency resolving was successful thanks to enabling these repositories:
%s
*******************************************************************\n""" % repos_str
    prompt = "Would you like to permanently enable these repositories? [y/N]: "
    return conduit.promptYN(msg, prompt=prompt)
