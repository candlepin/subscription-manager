from __future__ import print_function, division, absolute_import

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
from subscription_manager import injection as inj
from subscription_manager.repolib import RepoActionInvoker

import logging

log = logging.getLogger(__name__)

# Module for manipulating content overrides


class Overrides(object):
    def __init__(self):
        self.cp_provider = inj.require(inj.CP_PROVIDER)

        self.cache = inj.require(inj.OVERRIDE_STATUS_CACHE)
        self.repo_lib = RepoActionInvoker(cache_only=True)

    def get_overrides(self, consumer_uuid):
        return self._build_from_json(self.cache.load_status(self._getuep(), consumer_uuid))

    def add_overrides(self, consumer_uuid, overrides):
        return self._build_from_json(self._getuep().setContentOverrides(consumer_uuid,
                                                                 self._add(overrides)))

    def remove_overrides(self, consumer_uuid, overrides):
        return self._delete_overrides(consumer_uuid, self._remove(overrides))

    def remove_all_overrides(self, consumer_uuid, repos):
        return self._delete_overrides(consumer_uuid, self._remove_all(repos))

    def update(self, overrides):
        self.cache.server_status = [override.to_json() for override in overrides]
        self.cache.write_cache()
        self.repo_lib.update()

    def _delete_overrides(self, consumer_uuid, override_data):
        return self._build_from_json(self._getuep().deleteContentOverrides(consumer_uuid, override_data))

    def _add(self, overrides):
        return [override.to_json() for override in overrides]

    def _remove(self, overrides):
        return [{'contentLabel': override.repo_id, 'name': override.name} for override in overrides]

    def _remove_all(self, repos):
        if repos:
            return [{'contentLabel': repo} for repo in repos]
        else:
            return None

    def _build_from_json(self, override_json):
        return [Override.from_json(override_dict) for override_dict in override_json]

    def _getuep(self):
        return self.cp_provider.get_consumer_auth_cp()


class Override(object):
    def __init__(self, repo_id, name, value=None):
        self.repo_id = repo_id
        self.name = name
        self.value = value

    @classmethod
    def from_json(cls, json_obj):
        return cls(json_obj['contentLabel'], json_obj['name'], json_obj['value'])

    def to_json(self):
        return {'contentLabel': self.repo_id, 'name': self.name, 'value': self.value}
