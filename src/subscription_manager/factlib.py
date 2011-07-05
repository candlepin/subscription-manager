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
import gettext
_ = gettext.gettext

from certlib import  ActionLock, ConsumerIdentity, DataLib
from subscription_manager.facts import Facts

log = logging.getLogger('rhsm-app.' + __name__)


class FactLib(DataLib):

    def __init__(self, lock=ActionLock(), uep=None):
        DataLib.__init__(self, lock, uep)
        self.action = UpdateAction(uep=self.uep)

    def _do_update(self):
        return self.action.perform()


class Action:

    def __init__(self, uep=None):
        self.factdir = "somewhere"
        self.uep = uep


class UpdateAction(Action):

    def perform(self):
        updates = 0
        facts = self._get_facts()
        if facts.delta():
            updates = self.updateFacts(facts.get_facts())
        log.info("facts updated: %s" % updates)
        return updates

    def updateFacts(self, facts):
        updates = len(facts)
        # figure out the diff between latest facts and
        # report that as updates
        # TODO: don't update if there is nothing to update

        if not ConsumerIdentity.exists():
            return updates
        consumer = ConsumerIdentity.read()
        consumer_uuid = consumer.getConsumerId()

        self.uep.updateConsumerFacts(consumer_uuid, facts)
        return updates

    def _get_facts(self):
        return Facts()


def main():
    print _('Updating facts')
    factlib = FactLib()
    updates = factlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
