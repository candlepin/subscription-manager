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

from certlib import  ActionLock, Disconnected, ConsumerIdentity
from facts import Facts

log = logging.getLogger('rhsm-app.' + __name__)


class FactLib:

    def __init__(self, lock=ActionLock(), uep=None):
        self.lock = lock
        self.uep = uep

    def update(self):
        lock = self.lock
        lock.acquire()
        try:
            action = UpdateAction(uep=self.uep)
            return action.perform()
        finally:
            lock.release()


class Action:

    def __init__(self, uep=None):
        self.factdir = "somewhere"
        self.uep = uep


class UpdateAction(Action):

    def perform(self):
        updates = 0
        facts = Facts()
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


def main():
    print _('Updating facts')
    factlib = FactLib()
    updates = factlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
