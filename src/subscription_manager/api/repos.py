from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2015 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import fnmatch

import subscription_manager.injection as inj

from subscription_manager.api import request_injection
from subscription_manager.repolib import RepoActionInvoker, YumRepoFile


@request_injection
def _set_enable_for_yum_repositories(setting, *repo_ids):
    invoker = RepoActionInvoker()
    repos = invoker.get_repos()
    repos_to_change = []

    for r in repo_ids:
        matches = set([repo for repo in repos if fnmatch.fnmatch(repo.id, r)])
        repos_to_change.extend(matches)

    if len(repos_to_change) == 0:
        return 0

    # The cache should be primed at this point by the invoker.get_repos()
    cache = inj.require(inj.OVERRIDE_STATUS_CACHE)
    identity = inj.require(inj.IDENTITY)
    cp_provider = inj.require(inj.CP_PROVIDER)

    if identity.is_valid() and cp_provider.get_consumer_auth_cp().supports_resource('content_overrides'):
        overrides = [{'contentLabel': repo.id, 'name': 'enabled', 'value': setting} for repo in repos_to_change]
        cp = cp_provider.get_consumer_auth_cp()
        results = cp.setContentOverrides(identity.uuid, overrides)

        cache = inj.require(inj.OVERRIDE_STATUS_CACHE)

        # Update the cache with the returned JSON
        cache.server_status = results
        cache.write_cache()

        invoker.update()
    else:
        for repo in repos_to_change:
            repo['enabled'] = setting

        repo_file = YumRepoFile()
        repo_file.read()
        for repo in repos_to_change:
            repo_file.update(repo)
        repo_file.write()

    return len(repos_to_change)


def enable_yum_repositories(*repo_ids):
    """Enable a Yum repo by repoid.  Wildcards are honored.  Any matching repos are
    enabled *even if they are already enabled*."""
    return _set_enable_for_yum_repositories('1', *repo_ids)


def disable_yum_repositories(*repo_ids):
    """Disable a Yum repo by repoid.  Wildcards are honored.  Any matching repos are
    disabled *even if they are already enabled*."""
    return _set_enable_for_yum_repositories('0', *repo_ids)
