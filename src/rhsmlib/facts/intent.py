from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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

from intentctl.intentfiles import IntentStore, USER_INTENT

from rhsmlib.facts.collector import FactsCollector


class IntentCollector(FactsCollector):

    def __init__(self, prefix=None, testing=None, collected_hw_info=None):
        super(IntentCollector, self).__init__(
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

    def get_all(self):
        intent_store = IntentStore.read(USER_INTENT)
        intent_contents = {}
        for key,value in intent_store.contents.items():
            new_key = 'intent.' + key
            intent_contents[new_key] = value
        return intent_contents
