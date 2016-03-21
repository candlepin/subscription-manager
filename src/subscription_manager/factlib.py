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

from certlib import Locker, ActionReport
from subscription_manager import injection as inj

from rhsmlib.dbus.clients.facts import client as facts_client
from rhsmlib.candlepin import api as candlepin_api

_ = gettext.gettext

log = logging.getLogger('rhsm-app.' + __name__)


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
        self.report = FactsActionReport()
        self.facts_client = facts_client.FactsHostClient()

    def _on_facts_changed(self, changed_properties, invalidated_properties):
        if 'facts' in changed_properties:
            self.report.fact_updates = changed_properties['facts']

            # CacheManager.update_check calls self.has_changed,
            # is the self.facts.has_changed above redundant?

            # We have a signal that will tell us facts changed, and which
            # facts changed and how, but currently the server expects the full
            # list on change, so get it via properties.
            # FIXME:
            # Eventually, the dbus signal handler for facts changed should be
            # another dbus service that knows how to update to candlepin.
            fact_data = self.facts_client.Get('facts')
            self.sync_facts_to_server(fact_data)
            log.info("Facts have been updated.")
        else:
            log.debug("Facts have not changed, skipping upload.")

    def collect_facts(self):
        return self.facts_client.GetFacts()

    def sync_facts_to_server(self, fact_updates):
        consumer_identity = inj.require(inj.IDENTITY)
        if not consumer_identity.is_valid():
            # FIXME: more info
            return self.report

        cp_provider = inj.require(inj.CP_PROVIDER)
        uep = cp_provider.get_consumer_auth_cp()

        consumer_api = candlepin_api.CandlepinConsumer(uep, consumer_identity.uuid)
        # rest_api = rhsmlib.candlepin_api.consumer.Consumer(uep,uuid, success_callback, error_callback)
        # CandlepinConsumer is a CandlepinObject
        # CandlepinObject
        # CandlepinConsumer.get, .put, .update, .?
        res = consumer_api.call(uep.updateConsumer, fact_updates)
        log.debug("sync_facts_to_server candlepin api res=%s", res)

    def perform(self):

        # figure out the diff between latest facts and
        # report that as updates
        self.update()
        return self.report

    # The normal case will assume the facts prop changed signal will trigger a
    # facts update if it's needed.
    def update(self):
        log.debug('factslib.update does not do anything yet')
        pass

    def update_force(self):
        """This will collect the facts from the dbus service and push them to the server.

        But it will also trigger a PropertiesChanged dbus signal if they are different.
        NOTE: This doesn't force a collection of new facts, that is up to the facts
        service to decide. This will always upload whatever the service provides however,
        even if it's version cached by the facts service."""
        collected_facts = self.collect_facts()

        self.sync_facts_to_server(collected_facts)
