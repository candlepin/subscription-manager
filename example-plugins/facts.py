from __future__ import print_function, division, absolute_import

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
import json


class FactsPlugin(SubManPlugin):
    """Plugin for adding additional facts to subscription-manager facts"""
    name = "facts"

    def post_facts_collection_hook(self, conduit):
        """'post_facts_collection' hook to add facter facts

        Args:
            conduit: A FactsConduit()
        """
        conduit.log.debug("post_facts_collection called")
        facts = conduit.facts

        # FIXME: remove this
        # TODO: ditto
        # add some facts
        # for test, let's collect puppet/facter facts
        # that is sort of useful

        facter_cmd = "/usr/bin/facter"
        facter_args = ["--json"]
        facter_cli = [facter_cmd] + facter_args

        facter_out = None

        return_code = None
        try:
            process = subprocess.Popen(facter_cli,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            facter_out, facter_err = process.communicate()
            return_code = process.returncode
        except EnvironmentError as e:
            conduit.log.error(e)
            conduit.log.error("Could not run command:  \"%s\"" % " ".join(facter_cli))
            return

        if return_code != 0:
            conduit.log.error("\"%s\" exit status indicated an error: %s" % (" ".join(facter_cli),
                                                                           facter_err))
            return

        if facter_out is None:
            return

        facter_dict = json.loads(facter_out)

        # append 'facter' to the names
        # terrible list comprehension, dont do this in real code
        # len(str(x[1])) is terrible if x[1] is say, a float with long string repr, then
        # again, we don't support that, so...
        new_facter_facts = dict([('facter.' + x[0], x[1]) for x in list(facter_dict.items()) if len(str(x[1])) < 256])
        facts.update(new_facter_facts)
