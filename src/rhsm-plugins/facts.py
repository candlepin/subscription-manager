#
# Copyright (c) 2013 Red Hat, Inc.
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

from subscription_manager.base_plugin import SubManPlugin
requires_api_version = "1.0"

import subprocess
import simplejson as json


class FactsPlugin(SubManPlugin):
    """Plugin for adding additional facts to subscription-manager facts"""
    name = "facts"

    def post_facts_collection_hook(self, conduit):
        """'post_facts_collection' hook to add facter facts

        Args:
            conduit: A FactsConduit()
        """
        conduit.log.info("post_facts_collection called")
        facts = conduit.getFacts()

        # FIXME: remove this
        # TODO: ditto
        # add some facts
        # for test, let's collect puppet/facter facts
        # that is sort of useful

        process = subprocess.Popen(['/usr/bin/facter', '--json'], stdout=subprocess.PIPE)
        facter = process.communicate()[0]
        facter_dict = json.loads(facter)

        # append 'facter' to the names
        # terrible list comprehension, dont do this in real code
        # len(str(x[1])) is terrible if x[1] is say, a float with long string repr, then
        # again, we don't support that, so...
        new_facter_facts = dict([('facter.' + x[0], x[1]) for x in facter_dict.items() if len(str(x[1])) < 256])
        facts.update(new_facter_facts)
