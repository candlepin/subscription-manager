#!/usr/bin/python -Es
# ^ is to prevent selinux denials trying to load modules from unintended
#   paths. See https://bugzilla.redhat.com/show_bug.cgi?id=1136163
#
# Copyright (c) 2012 Red Hat, Inc.
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

import sys
import logging

from subscription_manager import logutil

from rhsm import connection

from subscription_manager import ga_loader
ga_loader.init_ga()

from subscription_manager.injectioninit import init_dep_injection
init_dep_injection()

from subscription_manager import action_client
from subscription_manager import managerlib
from subscription_manager.identity import ConsumerIdentity
from subscription_manager.i18n_optparse import OptionParser, \
    WrappedIndentedHelpFormatter, USAGE

import gettext
_ = gettext.gettext


def main(options, log):
    if not ConsumerIdentity.existsAndValid():
        log.error('Either the consumer is not registered or the certificates' +
                  ' are corrupted. Certificate update using daemon failed.')
        sys.exit(-1)
    print _('Updating entitlement certificates & repositories')

    try:
        if options.autoheal:
            actionclient = action_client.HealingActionClient()
        else:
            actionclient = action_client.ActionClient()

        actionclient.update(options.autoheal)

        for update_report in actionclient.update_reports:
            # FIXME: make sure we don't get None reports
            if update_report:
                print update_report

    except connection.ExpiredIdentityCertException, e:
        log.critical(_("Your identity certificate has expired"))
        raise e
    except connection.GoneException, ge:
        uuid = ConsumerIdentity.read().getConsumerId()

        # This code is to prevent an errant 410 response causing consumer cert deletion.
        #
        # If a server responds with a 410, we want to very that it's not just a 410 http status, but
        # also that the response is from candlepin, and include the right info about the consumer.
        #
        # A connection to the entitlement server could get an unintentional 410 response. A common
        # cause for that kind of error would be a bug or crash or misconfiguration of a reverse proxy
        # in front of candlepin. Most error codes we treat as temporary and transient, and they don't
        # cause any action to be taken (aside from error handling). But since consumer deletion is tied
        # to the 410 status code, and that is difficult to recover from, we try to be a little bit
        # more paranoid about that case.
        #
        # So we look for both the 410 status, and the expected response body. If we get those
        # then python-rhsm will create a GoneException that includes the deleted_id. If we get
        # A GoneException and the deleted_id matches, then we actually delete the consumer.
        #
        # However... If we get a GoneException and it's deleted_id does not match the current
        # consumer uuid, we do not delete the consumer. That would require using a valid consumer
        # cert, but making a request for a different consumer uuid, so unlikely. Could register
        # with --consumerid get there?
        if ge.deleted_id == uuid:
            log.critical("Consumer profile \"%s\" has been deleted from the server. Its local certificates will now be archived", uuid)
            managerlib.clean_all_data()
            log.critical("Certificates archived to '/etc/pki/consumer.old'. Contact your system administrator if you need more information.")

        raise ge


if __name__ == '__main__':

    logutil.init_logger()
    log = logging.getLogger('rhsm-app.' + __name__)

    parser = OptionParser(usage=USAGE,
                          formatter=WrappedIndentedHelpFormatter())
    parser.add_option("--autoheal", dest="autoheal", action="store_true",
            default=False, help="perform an autoheal check")
    (options, args) = parser.parse_args()
    try:
        main(options, log)
    except SystemExit, se:
        # sys.exit triggers an exception in older Python versions, which
        # in this case  we can safely ignore as we do not want to log the
        # stack trace. We need to check the code, since we want to signal
        # exit with failure to the caller. Otherwise, we will exit with 0
        if se.code:
            sys.exit(-1)
    except Exception, e:
        log.error("Error while updating certificates using daemon")
        print _('Unable to update entitlement certificates and repositories')
        log.exception(e)
        sys.exit(-1)
