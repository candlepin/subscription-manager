from __future__ import print_function, division, absolute_import

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
import logging

from .certlib import Locker, ActionReport
from subscription_manager import injection as inj

log = logging.getLogger(__name__)


# FactsActionInvoker has a Facts
#   Facts is a CacheManager
class FactsActionInvoker(object):
    """Used by CertActionClient to update a system's facts with the server, used
    primarily by the cron job but in a couple other places as well.

    Makes use of the facts module as well.
    """
    def __init__(self):
        self.locker = Locker()

    def update(self):
        return self.locker.run(self._do_update)

    def _do_update(self):
        action = FactsActionCommand()
        return action.perform()


class FactsActionReport(ActionReport):
    """ActionReport for FactsActionInvoker.

    fact_updates: list of updated facts.
    updates: Number of updated facts.
    """

    name = "Fact updates"

    def __init__(self):
        self.fact_updates = []
        self._exceptions = []
        self._updates = []
        self._status = None

    def updates(self):
        """How many facts were updated."""
        return len(self.fact_updates)


class FactsActionCommand(object):
    """UpdateAction for facts.

    Update facts if calculated local facts are different than
    the cached results of RHSM API known facts.

    If we know facts are now different from out last known
    cache of RHSM API's idea of this consumers facts, update
    the server with the latest version.

    Returns a FactsActionReport.
    """
    def __init__(self):
        cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = cp_provider.get_consumer_auth_cp()
        self.report = FactsActionReport()
        self.facts = inj.require(inj.FACTS)
        self.facts_client = inj.require(inj.FACTS)

    def perform(self):
        # figure out the diff between latest facts and
        # report that as updates

        if self.facts.has_changed():
            fact_updates = self.facts.get_facts()
            self.report.fact_updates = fact_updates

            consumer_identity = inj.require(inj.IDENTITY)
            if not consumer_identity.is_valid():
                return self.report

            # CacheManager.update_check calls self.has_changed,
            # is the self.facts.has_changed above redundant?
            self.facts.update_check(self.uep, consumer_identity.uuid)
            log.info("Facts have been updated.")
        else:
            log.debug("Facts have not changed, skipping upload.")
        return self.report
