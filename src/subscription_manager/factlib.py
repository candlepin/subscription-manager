#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Adrian Likins <alikins@redhat.com>
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

from certlib import ConsumerIdentity, DataLib, Action, ActionReport
from subscription_manager.facts import Facts

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


# Factlib has a Facts
#   Facts is a CacheManager
# Facts as a CacheManager seems to be doing alot
# of stuff, split actual facts gather code out?
class FactLib(DataLib):
    """
    Used by CertManager to update a system's facts with the server, used
    primarily by the cron job but in a couple other places as well.

    Makes use of the facts module as well.
    """
    def __init__(self, lock=None, uep=None, facts=None):
        DataLib.__init__(self, lock, uep)
        self.facts = facts
        if not self.facts:
            self.facts = Facts()

    def _do_update(self):
        action = FactAction(uep=self.uep, facts=self.facts)
        return action.perform()


class FactActionReport(ActionReport):
    def __init__(self):
        self.fact_updates = []

    def updates(self):
        """how many facts were updated"""
        return len(self.fact_updates)


class FactAction(Action):
    # FIXME: pretty sure Action doesn't need any of this
    def __init__(self, uep=None, entdir=None, product_dir=None,
                 facts=None):
        Action.__init__(self, uep, entdir=entdir)
        self.report = FactActionReport()
        self.facts = facts

    def perform(self):
        updates = 0

        # figure out the diff between latest facts and
        # report that as updates

        if self.facts.has_changed():
            fact_updates = self.facts.get_facts()
            self.report.fact_updates = fact_updates
            # FIXME: changed to injected
            if not ConsumerIdentity.exists():
                return self.report
            consumer = ConsumerIdentity.read()
            consumer_uuid = consumer.getConsumerId()

            # CacheManager.update_check calls self.has_changed,
            # is the self.facts.has_changed above redundant?
            self.facts.update_check(self.uep, consumer_uuid)
        else:
            log.info("Facts have not changed, skipping upload.")

        # FIXME: can populate this with more info later
        return self.report
