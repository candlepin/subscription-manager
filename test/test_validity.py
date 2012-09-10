#
# Copyright (c) 2010 Red Hat, Inc.
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

import unittest
from datetime import timedelta, datetime

from stubs import StubEntitlementCertificate, StubProduct, StubProductCertificate, \
    StubCertificateDirectory, StubFacts, StubEntitlementDirectory
from subscription_manager.validity import find_first_invalid_date, \
    ValidProductDateRangeCalculator

from rhsm.certificate import GMT
from subscription_manager.cert_sorter import CertSorter, SUBSCRIBED, PARTIALLY_SUBSCRIBED


class FindFirstInvalidDateTests(unittest.TestCase):

    # No product certs installed, but we manually got entitlements:
    def test_just_entitlements(self):
        cert1 = StubEntitlementCertificate(
                    StubProduct('product1'), start_date=datetime(2010, 1, 1),
                    end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                    StubProduct('product2'),
                    start_date=datetime(2010, 1, 1),
                    end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])
        prod_dir = StubCertificateDirectory([])

        last_valid_date = find_first_invalid_date(ent_dir, prod_dir, {})
        self.assertTrue(last_valid_date is None)

    def test_currently_unentitled_products(self):
        cert = StubProductCertificate(StubProduct('unentitledProduct'))
        prod_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because we have an unentitled product, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir, prod_dir, {})
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)

    def test_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        prod_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1),
                end_date=datetime(2050, 1, 1))
        cert2 = StubEntitlementCertificate(
                StubProduct('product2'),
                start_date=datetime(2010, 1, 1),
                end_date=datetime(2060, 1, 1))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        last_valid_date = find_first_invalid_date(ent_dir, prod_dir, {})
        self.assertEqual(2050, last_valid_date.year)

    # Checking scenario when we have an entitlement to cover us now, and another
    # for when the first expires:
    def test_future_entitled_products(self):
        cert = StubProductCertificate(StubProduct('product1'))
        prod_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2010, 1, 1, tzinfo=GMT()),
                end_date=datetime(2050, 1, 1, tzinfo=GMT()))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2049, 1, 1, tzinfo=GMT()),
                end_date=datetime(2070, 1, 1, tzinfo=GMT()))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        last_valid_date = find_first_invalid_date(ent_dir, prod_dir, {})
        self.assertEqual(2070, last_valid_date.year)
        self.assertEqual(1, last_valid_date.month)
        self.assertEqual(2, last_valid_date.day)

    def test_all_expired_entitlements(self):
        cert = StubProductCertificate(StubProduct('product1'))
        prod_dir = StubCertificateDirectory([cert])

        cert1 = StubEntitlementCertificate(
                StubProduct('product1'), start_date=datetime(2000, 1, 1, tzinfo=GMT()),
                end_date=datetime(2001, 1, 1, tzinfo=GMT()))
        cert2 = StubEntitlementCertificate(
                StubProduct('product1'),
                start_date=datetime(2000, 12, 1, tzinfo=GMT()),
                end_date=datetime(2005, 1, 1, tzinfo=GMT()))
        ent_dir = StubCertificateDirectory([cert1, cert2])

        # Because all entitlements have expired, we should get back the current
        # date as the last date of valid entitlements:
        today = datetime.now(GMT())
        last_valid_date = find_first_invalid_date(ent_dir, prod_dir, {})
        self.assertEqual(today.year, last_valid_date.year)
        self.assertEqual(today.month, last_valid_date.month)
        self.assertEqual(today.day, last_valid_date.day)


class ValidProductDateRangeCalculatorTests(unittest.TestCase):
    INST_PID_1 = 'prod-1'
    INST_PID_2 = 'prod_2'
    STACK_1 = 'stack_1'

    NOW = datetime.now(tz=GMT())
    # Approximate month values
    TEN_DAYS = timedelta(days=10)
    ONE_MONTH = timedelta(days=31)
    THREE_MONTHS = timedelta(days=93)
    YEAR = timedelta(days=365)

    TEN_MINUTES = timedelta(minutes=10)
    THIRTY_MINUTES = timedelta(minutes=30)

    def test_single_entitlement(self):
        expected_begin_date = self.NOW - self.ONE_MONTH
        expected_end_date = self.NOW + self.ONE_MONTH

        installed = create_prod_cert(self.INST_PID_1)

        ent = self._create_entitlement(self.INST_PID_1, expected_begin_date, expected_end_date)

        sorter = create_cert_sorter([installed], [ent])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_begin_date.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end_date.replace(tzinfo=GMT()), prod_range.end())

    def test_single_entitlement_ignores_expired_with_no_overlap(self):
        expected_begin_date = self.NOW - self.ONE_MONTH
        expected_end_date = self.NOW + self.ONE_MONTH

        installed = create_prod_cert(self.INST_PID_1)

        expired = self._create_entitlement(self.INST_PID_1,
                                           expected_begin_date - self.THREE_MONTHS,
                                           expected_begin_date - self.ONE_MONTH)
        ent = self._create_entitlement(self.INST_PID_1, expected_begin_date, expected_end_date)

        sorter = create_cert_sorter([installed], [ent, expired])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_begin_date.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end_date.replace(tzinfo=GMT()), prod_range.end())

    def test_single_entitlement_ignores_future_with_no_overlap(self):
        expected_begin_date = self.NOW - self.ONE_MONTH
        expected_end_date = self.NOW + self.ONE_MONTH

        installed = create_prod_cert(self.INST_PID_1)

        ent = self._create_entitlement(self.INST_PID_1, expected_begin_date, expected_end_date)

        future_start = expected_begin_date + self.THREE_MONTHS
        future = self._create_entitlement(self.INST_PID_1, future_start, future_start + self.YEAR)

        sorter = create_cert_sorter([installed], [ent, future])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_begin_date.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end_date.replace(tzinfo=GMT()), prod_range.end())

    def test_multiple_entitlements_overlap(self):
        expected_start = self.NOW - self.ONE_MONTH
        expected_end = self.NOW + self.YEAR
        installed = create_prod_cert(self.INST_PID_1)

        ent1 = self._create_entitlement(self.INST_PID_1, expected_start,
                                        self.NOW + self.THREE_MONTHS)

        ent2 = self._create_entitlement(self.INST_PID_1, self.NOW + self.ONE_MONTH, expected_end)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_start.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end.replace(tzinfo=GMT()), prod_range.end())

    def test_multiple_entitlements_one_consumes_other(self):
        expected_start = self.NOW - self.THREE_MONTHS
        expected_end = self.NOW + self.YEAR
        installed = create_prod_cert(self.INST_PID_1)

        ent1 = self._create_entitlement(self.INST_PID_1, self.NOW - self.ONE_MONTH,
                                        self.NOW + self.THREE_MONTHS)

        ent2 = self._create_entitlement(self.INST_PID_1, expected_start, expected_end)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_start.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end.replace(tzinfo=GMT()), prod_range.end())

    def test_multiple_entitlements_future_overlap(self):
        expected_start = self.NOW - self.TEN_DAYS
        expected_end = self.NOW + self.YEAR
        installed = create_prod_cert(self.INST_PID_1)

        ent1 = self._create_entitlement(self.INST_PID_1, self.NOW + self.ONE_MONTH,
                                        expected_end)

        ent2 = self._create_entitlement(self.INST_PID_1, expected_start,
                                        self.NOW + self.THREE_MONTHS)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_start.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end.replace(tzinfo=GMT()), prod_range.end())

    def test_multiple_entitlements_expired_with_overlap(self):
        expected_start = self.NOW - self.YEAR
        expected_end = self.NOW + self.YEAR
        installed = create_prod_cert(self.INST_PID_1)

        ent1 = self._create_entitlement(self.INST_PID_1, self.NOW - self.THREE_MONTHS,
                                        expected_end)

        ent2 = self._create_entitlement(self.INST_PID_1, expected_start,
                                        self.NOW - self.ONE_MONTH)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(expected_start.replace(tzinfo=GMT()), prod_range.begin())
        self.assertEquals(expected_end.replace(tzinfo=GMT()), prod_range.end())

    def test_only_future_entitlement_returns_none(self):
        expected_begin_date = self.NOW + self.ONE_MONTH
        expected_end_date = self.NOW + self.THREE_MONTHS
        installed = create_prod_cert(self.INST_PID_1)
        ent = self._create_entitlement(self.INST_PID_1, expected_begin_date, expected_end_date)

        sorter = create_cert_sorter([installed], [ent])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(None, prod_range)

    def test_only_expired_entitlement_returns_none(self):
        expected_start = self.NOW - self.YEAR
        expected_end = self.NOW - self.ONE_MONTH
        installed = create_prod_cert(self.INST_PID_1)
        ent = self._create_entitlement(self.INST_PID_1, expected_start, expected_end)

        sorter = create_cert_sorter([installed], [ent])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(None, prod_range)

    # Start testing calculations when stacking is involved.
    def test_partial_has_no_date_range_calculated(self):
        installed = create_prod_cert(self.INST_PID_1)
        start = self.NOW
        end = self.NOW + self.YEAR

        partial_ent = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                         stack_id=self.STACK_1, sockets=2,
                                         start_date=start, end_date=end)
        sorter = create_cert_sorter([installed], [partial_ent])
        self.assertEqual(PARTIALLY_SUBSCRIBED, sorter.get_status(self.INST_PID_1))

        calculator = ValidProductDateRangeCalculator(sorter)
        valid_range = calculator.calculate(self.INST_PID_1)
        self.assertEquals(None, valid_range)

    def test_end_date_set_to_first_date_of_non_compliance_when_stacked(self):
        installed = create_prod_cert(self.INST_PID_1)
        start1 = self.NOW - self.THREE_MONTHS
        end1 = self.NOW + self.THREE_MONTHS

        start2 = self.NOW - self.ONE_MONTH
        end2 = self.NOW + self.YEAR

        start3 = start1 + self.ONE_MONTH
        end3 = self.NOW - self.TEN_DAYS

        start4 = end1
        end4 = end2 + self.ONE_MONTH

        partial_ent_1 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                         stack_id=self.STACK_1, sockets=2,
                                         start_date=start1, end_date=end1)
        partial_ent_2 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                         stack_id=self.STACK_1, sockets=2,
                                         start_date=start2, end_date=end2)
        partial_ent_3 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                         stack_id=self.STACK_1, sockets=2,
                                         start_date=start3, end_date=end3)
        partial_ent_4 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                         stack_id=self.STACK_1, sockets=2,
                                         start_date=start4, end_date=end4)
        ents = [partial_ent_1, partial_ent_2, partial_ent_3, partial_ent_4]

        sorter = create_cert_sorter([installed], ents, machine_sockets=4)
        self.assertEqual(SUBSCRIBED, sorter.get_status(self.INST_PID_1))

        calculator = ValidProductDateRangeCalculator(sorter)
        valid_range = calculator.calculate(self.INST_PID_1)
        self.assertNotEqual(None, valid_range)
        self.assertEquals(start3.replace(tzinfo=GMT()), valid_range.begin())
        self.assertEquals(end2.replace(tzinfo=GMT()), valid_range.end())

    def test_consider_invalid_gap_between_non_stacked_and_partial_entitlement(self):
        start1 = self.NOW - self.THREE_MONTHS
        end1 = start1 + self.ONE_MONTH

        start2 = end1 - self.TEN_DAYS
        end2 = start2 + self.THREE_MONTHS

        start3 = start2 + self.ONE_MONTH
        end3 = start3 + self.THREE_MONTHS

        installed = create_prod_cert(self.INST_PID_1)
        ent1 = self._create_entitlement(self.INST_PID_1, start1, end1)
        partial_ent_1 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                      stack_id=self.STACK_1, sockets=2,
                                      start_date=start2, end_date=end2)
        partial_ent_2 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                      stack_id=self.STACK_1, sockets=2,
                                      start_date=start3, end_date=end3)
        ents = [ent1, partial_ent_1, partial_ent_2]

        sorter = create_cert_sorter([installed], ents, machine_sockets=4)
        self.assertEqual(SUBSCRIBED, sorter.get_status(self.INST_PID_1))

        calculator = ValidProductDateRangeCalculator(sorter)
        valid_range = calculator.calculate(self.INST_PID_1)
        self.assertNotEqual(None, valid_range)
        self.assertEquals(start3.replace(tzinfo=GMT()), valid_range.begin())
        self.assertEquals(end2.replace(tzinfo=GMT()), valid_range.end())

    def test_consider_invalid_gap_between_non_stacked_entitlement(self):
        start1 = self.NOW - self.THREE_MONTHS
        end1 = start1 + self.ONE_MONTH

        start2 = end1 - self.TEN_DAYS
        end2 = start2 + self.THREE_MONTHS

        start3 = start2 + self.ONE_MONTH
        end3 = start3 + self.THREE_MONTHS

        installed = create_prod_cert(self.INST_PID_1)
        ent1 = self._create_entitlement(self.INST_PID_1, start1, end1)
        partial_ent_1 = stub_ent_cert(self.INST_PID_2, [self.INST_PID_1], quantity=1,
                                      stack_id=self.STACK_1, sockets=2,
                                      start_date=start2, end_date=end2)
        ent3 = self._create_entitlement(self.INST_PID_1, start3, end3)
        ents = [ent1, partial_ent_1, ent3]

        sorter = create_cert_sorter([installed], ents, machine_sockets=4)
        self.assertEqual(SUBSCRIBED, sorter.get_status(self.INST_PID_1))

        calculator = ValidProductDateRangeCalculator(sorter)
        valid_range = calculator.calculate(self.INST_PID_1)
        self.assertNotEqual(None, valid_range)
        self.assertEquals(start3.replace(tzinfo=GMT()), valid_range.begin())
        self.assertEquals(end3.replace(tzinfo=GMT()), valid_range.end())

    def test_compare_by_start_date(self):
        ent1 = self._create_entitlement(self.INST_PID_1, self.NOW, self.NOW + self.THREE_MONTHS)
        ent2 = self._create_entitlement(self.INST_PID_1, self.NOW + self.ONE_MONTH,
                                        self.NOW + self.THREE_MONTHS)
        installed = create_prod_cert(self.INST_PID_1)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        self.assertEquals(0, calculator._compare_by_start_date(ent1, ent1))
        self.assertTrue(calculator._compare_by_start_date(ent1, ent2) < 0)  # starts before
        self.assertTrue(calculator._compare_by_start_date(ent2, ent1) > 0)  # starts after

    def test_get_range_grouping_overlapping_today(self):

        start1 = self.NOW - (self.YEAR * 3)
        end1 = start1 + self.THREE_MONTHS

        # Gap b/w 1 and 2
        start2 = end1 + self.THREE_MONTHS
        end2 = start2 + self.ONE_MONTH

        start3 = start2
        end3 = end2

        # Gap b/w 3 and 4
        start4 = end3 + self.YEAR
        end4 = start4 + self.THREE_MONTHS

        start5 = end4 - self.ONE_MONTH
        end5 = start5 + self.THREE_MONTHS

        start6 = end5 - self.TEN_DAYS
        end6 = self.NOW + self.THREE_MONTHS

        # 6 will cover 7 completely
        start7 = start6 + self.TEN_DAYS
        end7 = start7 + self.TEN_DAYS

        # 8 is completely covered by 6, but creates a gap b/w 7.
        start8 = self.NOW + self.ONE_MONTH
        end8 = start8 + self.TEN_DAYS

        # Gap here.
        start9 = end8 + self.YEAR
        end9 = start9 + self.ONE_MONTH

        ent_dates = [
            (start1, end1),
            (start2, end2),
            (start3, end3),
            (start4, end4),
            (start5, end5),
            (start6, end6),
            (start7, end7),
            (start8, end8),
            (start9, end9)
        ]

        expected_dates = [
                            (start4.replace(tzinfo=GMT()), end4.replace(tzinfo=GMT())),
                            (start5.replace(tzinfo=GMT()), end5.replace(tzinfo=GMT())),
                            (start6.replace(tzinfo=GMT()), end6.replace(tzinfo=GMT())),
                            (start7.replace(tzinfo=GMT()), end7.replace(tzinfo=GMT())),
                            (start8.replace(tzinfo=GMT()), end8.replace(tzinfo=GMT()))
        ]
        installed = create_prod_cert(self.INST_PID_1)
        ents = [self._create_entitlement(self.INST_PID_1, start, end) \
                for start, end in ent_dates]
        sorter = create_cert_sorter([installed], ents)
        calculator = ValidProductDateRangeCalculator(sorter)
        group = calculator._get_entitlements_spanning_now(ents)
        self.assertTrue(group)
        self.assertEqual(len(expected_dates), len(group))

        for ent in group:
            ent_range = ent.valid_range
            check = (ent_range.begin(), ent_range.end())
            self.assertTrue(check in expected_dates)

    def test_gap_between(self):
        start1 = self.NOW
        end1 = start1 + self.THREE_MONTHS

        start2 = self.NOW - self.THREE_MONTHS
        end2 = start2 + self.ONE_MONTH

        start3 = start2
        end3 = start2 + self.TEN_DAYS

        installed = create_prod_cert(self.INST_PID_1)

        ent1 = self._create_entitlement(self.INST_PID_1, start1, end1)
        ent2 = self._create_entitlement(self.INST_PID_1, start2, end2)
        ent3 = self._create_entitlement(self.INST_PID_1, start3, end3)

        sorter = create_cert_sorter([installed], [ent1, ent2, ent3])
        calculator = ValidProductDateRangeCalculator(sorter)
        self.assertTrue(calculator._gap_exists_between(ent1, ent2))
        self.assertFalse(calculator._gap_exists_between(ent2, ent3))
        self.assertFalse(calculator._gap_exists_between(ent3, ent2))
        self.assertTrue(calculator._gap_exists_between(ent1, ent3))
        self.assertTrue(calculator._gap_exists_between(ent2, ent1))

    def _create_entitlement(self, prod_id, start, end, sockets=None,
            quantity=1):
        return stub_ent_cert(self.INST_PID_1, start_date=start, end_date=end,
                sockets=sockets, quantity=quantity)

    def test_non_stacking_entitlements(self):
        start1 = self.NOW - self.THREE_MONTHS
        end1 = self.NOW + self.THREE_MONTHS

        start2 = self.NOW - self.ONE_MONTH
        end2 = self.NOW + self.YEAR

        installed = create_prod_cert(self.INST_PID_1)
        ent1 = self._create_entitlement(self.INST_PID_1, start1, end1,
            sockets=4, quantity=2)
        ent2 = self._create_entitlement(self.INST_PID_1, start2, end2,
            sockets=4)

        sorter = create_cert_sorter([installed], [ent1, ent2])
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertTrue(prod_range is None)

    def test_entitlements_with_overlap(self):
        start1 = self.NOW - self.TEN_MINUTES
        end1 = self.NOW + self.THIRTY_MINUTES

        start2 = self.NOW - self.THIRTY_MINUTES
        end2 = self.NOW + self.TEN_MINUTES

        installed = create_prod_cert(self.INST_PID_1)
        ent1 = self._create_entitlement(self.INST_PID_1, start1, end1, sockets=1)
        ent2 = self._create_entitlement(self.INST_PID_1, start2, end2, sockets=1)

        sorter = create_cert_sorter([installed], [ent1, ent2], machine_sockets=1)
        calculator = ValidProductDateRangeCalculator(sorter)
        prod_range = calculator.calculate(self.INST_PID_1)
        self.assertFalse(prod_range is None)


def create_cert_sorter(product_certs, entitlement_certs, machine_sockets=8):
    stub_facts = StubFacts(fact_dict={"cpu.cpu_socket(s)": machine_sockets})
    return CertSorter(StubCertificateDirectory(product_certs),
                      StubEntitlementDirectory(entitlement_certs),
                      stub_facts.get_facts())


def create_prod_cert(pid):
    return StubProductCertificate(StubProduct(pid))


def stub_ent_cert(parent_pid, provided_pids=[], quantity=1,
        stack_id=None, sockets=1, start_date=None, end_date=None):
    provided_prods = []
    for provided_pid in provided_pids:
        provided_prods.append(StubProduct(provided_pid))

    parent_prod = StubProduct(parent_pid)

    return StubEntitlementCertificate(parent_prod,
            provided_products=provided_prods, quantity=quantity,
            stacking_id=stack_id, sockets=sockets, start_date=start_date,
            end_date=end_date)
