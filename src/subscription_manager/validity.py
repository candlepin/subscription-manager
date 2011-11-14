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
from subscription_manager.certdirectory import EntitlementDirectory, \
    ProductDirectory
from subscription_manager import cert_sorter
from subscription_manager.facts import Facts
from datetime import timedelta, datetime
from rhsm.certificate import GMT

log = logging.getLogger('rhsm-app.' + __name__)


def find_first_invalid_date(ent_dir=None, product_dir=None,
        facts_dict=None):
    """
    Find the first date when the system is invalid at midnight
    GMT.

    WARNING: This method does *not* return the exact first datetime when
    we're invalid. Due to it's uses in the GUI it needs to
    return a datetime into the first day of being completely invalid, so
    the subscription assistant can search for that time and find expired
    products.

    If there are no products installed, return None, as there technically
    is no first invalid date.
    """
    if not ent_dir:
        ent_dir = EntitlementDirectory()
    if not product_dir:
        product_dir = ProductDirectory()
    if facts_dict is None:
        facts_dict = Facts().get_facts()

    current_date = datetime.now(GMT())

    if not product_dir.list():
        # If there are no products installed, return None, there is no
        # invalid date:
        log.debug("Unable to determine first invalid date, no products "
                "installed.")
        return None

    # change _scan_entitlement_certs to take product lists,
    # run it for the future to figure this out
    # First check if we have anything installed but not entitled *today*:
    cs = cert_sorter.CertSorter(product_dir, ent_dir, facts_dict,
            on_date=current_date)
    if not cs.is_valid():
        log.debug("Found unentitled products or partial stacks.")
        return current_date

    # Sort all the ent certs by end date. (ascending)
    all_ent_certs = ent_dir.list()

    def get_date(ent_cert):
        return ent_cert.validRange().end()

    all_ent_certs.sort(key=get_date)

    # Loop through all current and future entitlement certs, check validity
    # status on their end date, and return the first date where we're not
    # valid.
    for ent_cert in all_ent_certs:
        # Adding a timedelta of one day here so we can be sure we get a date
        # the subscription assitant (which does not use time) can use to search
        # for.
        end_date = ent_cert.validRange().end() + timedelta(days=1)
        if end_date < current_date:
            # This cert is expired, ignore it:
            continue
        log.debug("Checking cert: %s, end date: %s" % (ent_cert.serialNumber(),
            end_date))

        # new cert_sort stuff, use _scan_for_entitled_products, since
        # we just need to know if stuff is expired
        cs = cert_sorter.CertSorter(product_dir, ent_dir, facts_dict,
                on_date=end_date)
        if not cs.is_valid():
            log.debug("Found non-valid status on %s" % end_date)
            return end_date
        else:
            log.debug("Valid status on %s" % end_date)

    # Should never hit this:
    raise Exception("Unable to determine first invalid date.")
