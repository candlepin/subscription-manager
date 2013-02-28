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
from subscription_manager import cert_sorter
from datetime import timedelta, datetime
from rhsm.certificate import GMT, DateRange

log = logging.getLogger('rhsm-app.' + __name__)


class ValidProductDateRangeCalculator(object):

    def __init__(self, certsorter):
        self.sorter = certsorter

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
        # Only calculate a range if the status of the product is SUBSCRIBED.
        if not cert_sorter.SUBSCRIBED == self.sorter.get_status(product_hash):
            return None

        all_entitlements = self.sorter.get_entitlements_for_product(product_hash)

        # Determine which entitlements will potentially create a span
        # across today's date. Stacking is not considered here.
        possible_ents = self._get_entitlements_spanning_now(all_entitlements)

        # Since at this point we know that we are valid, we should always
        # get possible ents. Check here just to be sure.
        if not possible_ents:
            return None

        # Now that we have all entitlements that could potentially be
        # our valid span, figure out the start/end dates considering
        # stacking and overlapped entitlements. Entitlements are sorted
        # by start date so that we can process each from left to right
        # (relative to time). For example, while iterating the entitlements
        # we can assume that the start_date is next in line considering the
        # last processed.
        start_date = None
        end_date = None
        last_processed_ent = None
        for i, ent in enumerate(self._sort_past_to_future(possible_ents)):
            is_last = i == len(possible_ents) - 1
            ent_range = ent.valid_range
            ent_start = ent_range.begin()
            ent_end = ent_range.end()
            ent_valid_on_start = self._entitlement_valid_on_date(ent, possible_ents,
                                                                 ent_start)
            ent_valid_on_end = self._entitlement_valid_on_date(ent, possible_ents, ent_end)

            # Determine if after the last processed entitlement's end date,
            # the product is still valid. If we are not valid after the last,
            # and there are other entitlements to process, this can not be
            # the start date since there is a gap in validity from the last
            # processed entitlement's end date to the start of another entitlement.
            valid_after_last = True
            if last_processed_ent and not is_last:
                last_processed_end = last_processed_ent.valid_range.end()
                valid_after_last = self._entitlement_valid_on_date(last_processed_ent,
                                                                   possible_ents,
                                                                   last_processed_end +
                                                                   timedelta(seconds=1))
                if not valid_after_last:
                    start_date = None

            if ent_valid_on_start and valid_after_last:
                if not start_date or start_date > ent_start:
                    start_date = ent_start

            if ent_valid_on_end:
                if not end_date or end_date < ent_end:
                    end_date = ent_end

            last_processed_ent = ent

        # If we couldn't determine a start/end date, report
        # that there is no valid range for the product.
        if not start_date or not end_date:
            return None
        return DateRange(start_date, end_date)

    def _sort_past_to_future(self, entitlements):
        """
        Sorts the specified entitlements by start date from
        past to future.
        """
        return sorted(entitlements, cmp=self._compare_by_start_date)

    def _compare_by_start_date(self, ent1, ent2):
        """
        Compare entitlements by start dates.
        """
        e1_start = ent1.valid_range.begin()
        e2_start = ent2.valid_range.begin()

        if e1_start == e2_start:
            return 0

        if e1_start < e2_start:
            return -1

        return 1

    def _get_entitlements_spanning_now(self, entitlements):
        """
        From the specified entitlements, find the ones that make
        up a complete continuous span across today. Entitlements
        completely in the past/future will be included only if
        entitlements exist who's start or end dates overlap and
        a joined span reaches today.
        """
        sorted_ents = self._sort_past_to_future(entitlements)

        groups = []
        ent_group = None
        for ent in sorted_ents:
            if ent_group and not self._is_entitlement_covered_by_group(ent, ent_group):
                ent_group = [ent]
                groups.append(ent_group)
            else:
                if not ent_group:
                    ent_group = []
                    groups.append(ent_group)
                ent_group.append(ent)

        # Check each group to find the group that spans today.
        for group in groups:
            for ent in group:
                # DateRange is in GMT so convert now to GMT before compare
                if ent.valid_range.has_date(datetime.now(tz=GMT())):
                    return group
        return []

    def _is_entitlement_covered_by_group(self, to_check, group):
        """
        Given a group of entitlements, check if the specified entitlement
        is completely covered by another entitlement, with no gaps.
        """
        for ent in group:
            if not self._gap_exists_between(ent, to_check):
                return True
        return False

    def _gap_exists_between(self, ent1, ent2):
        """
        Determines id there is a gap in time between two entitlements.
        """
        ent1_range = ent1.valid_range
        ent2_range = ent2.valid_range

        if ent1_range.has_date(ent2_range.begin()) or ent1_range.has_date(ent2_range.end()):
            return False

        if ent2_range.has_date(ent1_range.begin()) or ent2_range.has_date(ent1_range.end()):
            return False

        return True

    def _entitlement_valid_on_date(self, entitlement, entitlements_to_check, date):
        """
        Given a list of entitlements, check if the specified entitlement is
        valid on the specified date.

        NOTE: If an entitlement is not stackable, it is considered valid if its
        range contains the specified date. If the entitlement is stackable,
        it is considered valid if its stack is valid, or there is a
        non-stackable entitlement who's span includes the specified date.
        """
        stack_id = entitlement.order.stacking_id
        if stack_id:
            if self.sorter.stack_id_valid(stack_id, entitlements_to_check, on_date=date):
                return True

            for ent in entitlements_to_check:
                if not ent.order.stacking_id:
                    return ent.valid_range.has_date(date) \
                        and entitlement.valid_range.has_date(date)

            return False

        # If the socket count on a non stacked entitlement doesn't cover
        # the system, we're not valid, dates are irrelevant:
        elif not self.sorter.ent_cert_sockets_valid(entitlement):
            return False

        return entitlement.valid_range.has_date(date)
