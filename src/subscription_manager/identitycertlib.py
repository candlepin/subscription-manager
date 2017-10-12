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

import logging


from subscription_manager import certlib
from subscription_manager import injection as inj

log = logging.getLogger(__name__)


class IdentityCertActionInvoker(certlib.BaseActionInvoker):
    """
    An object to update the identity certificate in the event the server
    deems it is about to expire. This is done to prevent the identity
    certificate from expiring thus disallowing connection to the server
    for updates.
    """

    def _do_update(self):
        action = IdentityUpdateAction()
        return action.perform()


class IdentityUpdateAction(object):
    """UpdateAction for consumer identity certificates.

    Returns a certlib.ActionReport. report.status of
    1 indicates identity cert was updated."""
    def __init__(self):
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = self.cp_provider.get_consumer_auth_cp()

        # Use the default report
        self.report = certlib.ActionReport()

    def perform(self):
        identity = inj.require(inj.IDENTITY)

        if not identity.is_valid():
            # we could in theory try to update the id in the
            # case of it being bogus/corrupted, ala #844069,
            # but that seems unneeded
            # FIXME: more details
            self.report._status = 0
            return self.report

        return self._update_cert(identity)

    def _update_cert(self, identity):

        # to avoid circular imports
        # FIXME: move persist stuff here
        from subscription_manager import managerlib

        idcert = identity.consumer

        consumer = self._get_consumer(identity)

        # only write the cert if the serial has changed
        # FIXME: this would be a good place to have a Consumer/ConsumerCert
        # model.
        # FIXME: and this would be a ConsumerCert model '!='
        if idcert.getSerialNumber() != consumer['idCert']['serial']['serial']:
            log.debug('identity certificate changed, writing new one')

            # FIXME: should be in this module? managerlib is an odd place
            managerlib.persist_consumer_cert(consumer)

        # updated the cert, or at least checked
        self.report._status = 1
        return self.report

    def _get_consumer(self, identity):
        # FIXME: not much for error handling here
        consumer = self.uep.getConsumer(identity.uuid)
        return consumer
