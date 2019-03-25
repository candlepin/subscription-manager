from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2017 Red Hat, Inc.
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

"""
This module includes class used for unregistering system from candlepin
server.
"""

import logging

from subscription_manager import injection as inj
from subscription_manager import managerlib
from rhsm import connection


log = logging.getLogger(__name__)


class UnregisterService(object):
    """
    Class providing functionality of unregistering the system from
    Candlepin server.
    """

    def __init__(self, uep):
        """
        Initialization of Unregister instance
        """
        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = uep

    def unregister(self):
        """
        Try to unregister the system from candlepin server
        :return: None
        """

        try:
            self.uep.unregisterConsumer(self.identity.uuid)
            log.info("Successfully un-registered.")
            managerlib.system_log("Unregistered machine with identity: %s" % self.identity.uuid)
            managerlib.clean_all_data(backup=False)
            self.cp_provider.clean()
        except connection.GoneException as ge:
            if ge.deleted_id == self.identity.uuid:
                log.debug(
                    "This consumer's profile has been deleted from the server. Local certificates and "
                    "cache will be cleaned now."
                )
                managerlib.clean_all_data(backup=False)
            else:
                raise ge
