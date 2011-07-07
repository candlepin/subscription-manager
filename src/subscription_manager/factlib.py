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
    """
    Used by CertManager to update a system's facts with the server, used 
    primarily by the cron job but in a couple other places as well.

    Makes use of the facts module as well.
    """

    def _do_update(self):
        updates = 0

        # figure out the diff between latest facts and
        # report that as updates

        facts = self._get_facts()
        if facts.delta():
            updates = len(facts.get_facts())
            if not ConsumerIdentity.exists():
                return updates
            consumer = ConsumerIdentity.read()
            consumer_uuid = consumer.getConsumerId()

            facts.update_check(self.uep, consumer_uuid)
        else:
            log.info("Facts have not changed, skipping upload.")
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
