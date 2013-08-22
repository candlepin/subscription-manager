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

import logging


from subscription_manager import certlib
from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class IdentityCertLib(DataLib):
    """
    An object to update the identity certificate in the event the server
    deems it is about to expire. This is done to prevent the identity
    certificate from expiring thus disallowing connection to the server
    for updates.
    """

    def _do_update(self):
        report = ActionReport()
        if not ConsumerIdentity.existsAndValid():
            # we could in theory try to update the id in the
            # case of it being bogus/corrupted, ala #844069,
            # but that seems unneeded
            # FIXME: more details
            report._status = 0
            return report

        from subscription_manager import managerlib

        idcert = ConsumerIdentity.read()
        uuid = idcert.getConsumerId()
        consumer = self.uep.getConsumer(uuid)
        # only write the cert if the serial has changed
        if idcert.getSerialNumber() != consumer['idCert']['serial']['serial']:
            log.debug('identity certificate changed, writing new one')
            managerlib.persist_consumer_cert(consumer)
        report._status = 1
        return report

