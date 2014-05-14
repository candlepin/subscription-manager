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
import gettext
import logging

# rhsm.conf->iniparse->configParser can raise ConfigParser exceptions
import ConfigParser

from subscription_manager import api
from subscription_manager import certlib

from subscription_manager.plugin.ostree import model

# plugins get
log = logging.getLogger('rhsm-app.' + __name__)

_ = gettext.gettext


OSTREE_CONTENT_TYPE = "ostree"


class OstreeContentUpdateActionCommand(object):
    """UpdateActionCommand for ostree repos.

    Update the repo configuration for rpm-ostree when triggered.

    Return a OstreeContentUpdateReport.
    """
    def perform(self):
        # starting state of ostree config
        ostree_config = model.OstreeConfig()

        # populate config, handle exceptions
        self.load_config(ostree_config)

        report = OstreeContentUpdateActionReport()

        entitled_content = OstreeContents()
        entitled_content.load()

        # CALCULATE UPDATES
        # given current config, and the new contents, construct a list
        # of remotes to apply to our local config of remotes.
        updates_builder = \
            model.OstreeConfigUpdatesBuilder(ostree_config,
                                             content_set=entitled_content.content_set)
        updates = updates_builder.build()

        log.debug("Updates orig: %s" % updates.orig)
        log.debug("Updates new: %s" % updates.new)
        log.debug("Updates.new.remote_set: %s" % updates.new.remotes)

        # persist the new stuff
        updates.apply()
        updates.save()

        # TODO: Populate with origin info
        report.origin = "FIXME"
        report.refspec = "FIXME"
        report.orig_remotes = list(updates.orig.remotes)
        report.remote_updates = list(updates.new.remotes)

        log.debug("Ostree update report: %s" % report)
        return report

    def load_config(self, ostree_config):
        try:
            ostree_config.load()
        except ConfigParser.Error:
            log.info("No ostree content repo config file found. Not loading ostree config.")


class OstreeContents(object):
    """Find the ostree content provided by our current entitlements."""
    content_type = OSTREE_CONTENT_TYPE

    def __init__(self):
        self.content_set = set()

    def load(self):
        ent_dir = api.inj.require(api.inj.ENT_DIR)

        # valid ent certs could be an iterator
        for ent_cert in ent_dir.list_valid():
            # ditto content
            for content in ent_cert.content:
                log.debug("content: %s" % content)

                if content.content_type == self.content_type:
                    log.debug("adding %s to ostree content" % content)
                    self.content_set.add(content)


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
        self.origin = None
        self.refspec = None

    def updates(self):
        """number of updates. Approximately."""
        return len(self.remote_updates)

    def _format_remotes(self, remotes):
        s = []
        for remote in remotes:
            s.append(remote.report())
        return '\n'.join(s)

    def __str__(self):
        # FIXME: Super ugly at the moment
        s = ["Ostree repo updates\n"]
        s.append("%s: %s" % (_("Origin:"), self.origin))
        s.append("%s: %s" % (_("Refspec:"), self.refspec))
        s.append(_("Updates:"))
        s.append(self._format_remotes(self.remote_updates))
        s.append(_("Added:"))
        s.append(self._format_remotes(self.remote_updates))
        s.append(_("Deleted:"))
        s.append(self._format_remotes(self.orig_remotes))
        return '\n'.join(s)
