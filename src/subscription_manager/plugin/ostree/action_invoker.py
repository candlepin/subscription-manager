from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2014 Red Hat, Inc.
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
import logging

# rhsm.conf->iniparse->configParser can raise ConfigParser exceptions
from six.moves import configparser

from subscription_manager import certlib
from subscription_manager.model import find_content

from subscription_manager.plugin.ostree import model

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

OSTREE_CONTENT_TYPE = "ostree"


class OstreeContentUpdateActionCommand(object):
    """UpdateActionCommand for ostree repos.

    Update the repo configuration for rpm-ostree when triggered.

    Return a OstreeContentUpdateReport.
    """
    def __init__(self, ent_source):
        self.ent_source = ent_source

    def migrate_core_config(self):
        # starting state of ostree config
        ostree_core_config = model.OstreeCoreConfig()

        self.load_config(ostree_core_config)

        # if it has remotes, we want to update to remove them
        if not ostree_core_config.remotes:
            return ostree_core_config

        # empty the remote list
        self.update_config(ostree_core_config,
                           contents=[])

        return ostree_core_config

    def perform(self):

        # see if it has remotes, if so, migrate it

        self.migrate_core_config()

        return self.update_repo_config()

    def update_repo_config(self):
        ostree_repo_config = model.OstreeRepoConfig()

        # populate config, handle exceptions
        self.load_config(ostree_repo_config)

        # return the composed set of EntitledContents
        entitled_contents = find_content(self.ent_source,
                                         content_type=OSTREE_CONTENT_TYPE)

        # update repo configs
        report = self.update_config(ostree_repo_config,
                                     contents=entitled_contents)

        # reload the new config, so we have fresh remotes, etc
        self.load_config(ostree_repo_config)

        log.debug("Ostree update report: %s" % report)
        return report

    def update_config(self, ostree_config, contents):
        """Update the remotes configured in a OstreeConfig."""

        report = OstreeContentUpdateActionReport()

        updates_builder = \
            model.OstreeConfigUpdatesBuilder(ostree_config,
                                             contents=contents)
        updates = updates_builder.build()

        for remote in updates.orig.remotes:
            if remote in updates.new.remotes:
                report.remote_updates.append(remote)
            else:
                report.remote_deleted.append(remote)

        for remote in updates.new.remotes:
            if remote not in updates.orig.remotes:
                report.remote_added.append(remote)

        updates.apply()
        updates.save()

        return report

    def load_config(self, ostree_config):
        try:
            ostree_config.load()
        except configparser.Error:
            log.warn("No ostree content config file found at: %s. Not loading ostree config.",
                     ostree_config.repo_file_path)


class OstreeContentUpdateActionReport(certlib.ActionReport):
    """Track ostree repo config changes."""
    name = "Ostree repo updates report"

    def __init__(self):
        super(OstreeContentUpdateActionReport, self).__init__()
        self.orig_remotes = []
        self.remote_updates = []
        self.remote_added = []
        self.remote_deleted = []
        self.content_to_remote = {}

    def updates(self):
        """Number of updates. Approximately."""
        return len(self.remote_updates)

    def _format_remotes(self, remotes):
        s = []
        for remote in remotes:
            s.append(remote.report())
        return '\n'.join(s)

    def __str__(self):
        s = ["Ostree repo updates\n"]
        s.append(_("Updates:"))
        s.append(self._format_remotes(self.remote_updates))
        s.append(_("Added:"))
        s.append(self._format_remotes(self.remote_added))
        s.append(_("Deleted:"))
        s.append(self._format_remotes(self.remote_deleted))
        return '\n'.join(s)
