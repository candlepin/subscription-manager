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

from certlib import  ActionLock, UEP, Disconnected
from logutil import getLogger
from facts import Facts

log = getLogger(__name__)


class FactLib:

    def __init__(self, lock=ActionLock()):
        self.lock = lock

    def update(self):
        lock = self.lock
        lock.acquire()
        print "gh FactLib.update"
        try:
            action = UpdateAction()
            return action.perform()
        finally:
            lock.release()


class Action:

    def __init__(self):
        self.factdir = "somewhere"


class UpdateAction(Action):

    def perform(self):
        try:
            uep = UEP()
        except Disconnected:
            log.info('Disconnected, facts not updated')
            return 0

        updates = 0
        facts = Facts()
        if facts.delta():
            updates = self.updateFacts(uep, facts.get_facts())
        return updates

    def updateFacts(self, uep, facts):
        updates = len(facts)
        # figure out the diff between latest facts and
        # report that as updates
        # TODO: don't update if there is nothing to update
        uep.updateConsumerFacts(uep.uuid, facts)
        return updates


def main():
    print _('Updating facts')
    factlib = FactLib()
    updates = factlib.update()
    print _('%d updates required') % updates
    print _('done')

if __name__ == '__main__':
    main()
