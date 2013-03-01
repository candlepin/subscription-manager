#
# Copyright (c) 2011 Red Hat, Inc.
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
from subscription_manager.injection import FEATURES, IDENTITY
from subscription_manager import cert_sorter
from subscription_manager.utils import parseDate
from datetime import timedelta, datetime
from rhsm.certificate import GMT, DateRange

log = logging.getLogger('rhsm-app.' + __name__)


class ValidProductDateRangeCalculator(object):

    def __init__(self, uep):
        self.uep = uep
        self.identity = FEATURES.require(IDENTITY)

    def calculate(self, product_hash):
        """
        Calculate the valid date range for the specified product based on
        today's date.

        Partially entitled products are considered when determining the
        valid range.

        NOTE:
        The returned date range will be in GMT, so keep this in mind when
        presenting these dates to the user.
        """

        # If we're not registered, don't return a valid range:
        if not self.identity.is_valid():
            return None

        consumer_data = self.uep.getConsumer(self.identity.uuid)

        if 'installedProducts' not in consumer_data:
            log.warn("Server does not support product date ranges.")
            return None

        installed_products = consumer_data['installedProducts']
        for prod in installed_products:
            if product_hash != prod['productId']:
                continue

            # Found the product ID requested:
            if 'startDate' in prod and 'endDate' in prod:

                # Unentitled product:
                if prod['startDate'] is None or prod['endDate'] is None:
                    return None

                return DateRange(parseDate(prod['startDate']),
                    parseDate(prod['endDate']))
            else:
                # If startDate / endDate not supported
                log.warn("Server does not support product date ranges.")
                return None

        # At this point, we haven't found the installed product that was
        # asked for, which could indicate the server somehow doesn't know
        # about it yet. This is extremely weird and should be unlikely,
        # but we will log and handle gracefully:
        log.error("Requested status for installed product server does not "
                "know about: %s" % product_hash)
        return None

