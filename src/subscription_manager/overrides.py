#
# Copyright (c) 2013 Red Hat, Inc.
#
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
from subscription_manager import injection
from subscription_manager.repolib import RepoLib


# Module for manipulating content overrides

class OverrideLib(object):
    def __init__(self, cp):
        self.cp = cp;
        self.cache = injection.require(injection.OVERRIDE_STATUS_CACHE)
        self.repo_lib = RepoLib(uep=self.cp, cache_only=True)

    def get_overrides(self, consumer_uuid):
        return self.cache.load_status(self.cp, consumer_uuid)

    def add_overrides(self, consumer_uuid, repos, override_map):
        # override_map is a map of override_name:override_value that will
        # get applied to each repo.
        overrides = self._add(repos, override_map)
        return self.cp.setContentOverrides(consumer_uuid, overrides)

    def remove_overrides(self, consumer_uuid, repos, override_names):
        overrides = self._remove(repos, override_names)
        return self._delete_overrides(consumer_uuid, overrides)

    def remove_all_overrides(self, consumer_uuid, repos):
        overrides = self._remove_all(repos)
        return self._delete_overrides(consumer_uuid, overrides)

    def update(self, overrides):
        self.cache.server_status = overrides
        self.cache.write_cache()
        self.repo_lib.update()

    def _delete_overrides(self, consumer_uuid, overrides):
        return self.cp.deleteContentOverrides(consumer_uuid, overrides)

    def _add(self, repos, additions):
        return [{'contentLabel': repo, 'name': k, 'value': v} for repo in repos for k, v in additions.items()]

    def _remove(self, repos, removals):
        return [{'contentLabel': repo, 'name': item} for repo in repos for item in removals]

    def _remove_all(self, repos):
        if repos:
            return [{'contentLabel': repo} for repo in repos]
        else:
            return None
