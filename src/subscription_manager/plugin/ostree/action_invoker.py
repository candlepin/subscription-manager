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
import ConfigParser


from subscription_manager import api

from subscription_manager.plugin.ostree import repo_file
from subscription_manager.plugin.ostree import model

# plugins get
log = logging.getLogger('rhsm-app.' + __name__)


class OstreeContentActionInvoker(api.BaseActionInvoker):
    def _do_update(self):
        action = OstreeContentUpdateActionCommand()
        return action.perform()


class OstreeContentUpdateActionCommand(object):
    """UpdateActionCommand for ostree repos.

    Update the repo configuration for rpm-ostree when triggered.

    Return a OstreeContentUpdateReport.
    """
    def __init__(self):
        # starting state of ostree config
        self.ostree_config = model.OstreeConfig()

    def perform(self):
        # define... somewhere?
        OSTREE_CONTENT_TYPE = "ostree"
        self.load_config()

        # bleah, just do it
        ent_dir = api.inj.require(api.inj.ENT_DIR)

        content_set = set()
        # valid ent certs could be an iterator
        for ent_cert in ent_dir.list_valid():
            # ditto content
            for content in ent_cert.content:
                log.debug("content: %s" % content)

                if content.content_type == OSTREE_CONTENT_TYPE:
                    log.debug("adding %s to ostree content" % content)
                    content_set.add(content)

        # given current config, and the new contents, construct a list
        # of remotes to apply to our local config of remotes.
        updates_builder = model.OstreeConfigUpdatesBuilder(self.ostree_config,
            content_set=content_set)

        updates = updates_builder.build()

        # Get controller to update the model with the updates
        controller = model.OstreeConfigController(self.ostree_config)
        log.debug("Updates: %s" % updates)
        controller.update(updates)

    def load_config(self):
        try:
            self.ostree_config.load()
        except ConfigParser.Error:
            log.info("No ostree content repo config file found. Not loading ostree config.")


