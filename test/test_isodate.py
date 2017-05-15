#
# Copyright (c) 2010-2013 Red Hat, Inc.
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
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import datetime
import time
from subscription_manager import isodate
from dateutil.tz import tzlocal


# two classes for this, one that sets up for dateutil, one for
# for pyxml
class TestParseDate(unittest.TestCase):

    def _test_local_tz(self):
        tz = tzlocal()
        dt_no_tz = datetime.datetime(year=2000, month=1, day=1, hour=12, minute=34)
        now_dt = datetime.datetime(year=2000, month=1, day=1, hour=12, minute=34, tzinfo=tz)
        isodate.parse_date(now_dt.isoformat())
        # last member is is_dst, which is -1, if there is no tzinfo, which
        # we expect for dt_no_tz
        #
        # see if we get the same times
        now_dt_tt = now_dt.timetuple()
        dt_no_tz_tt = dt_no_tz.timetuple()

        # tm_isdst (timpletuple()[8]) is 0 if a tz is set,
        # but the dst offset is 0
        # if it is -1, no timezone is set
        if now_dt_tt[8] == 1 and dt_no_tz_tt == -1:
            # we are applying DST to now time, but not no_tz time, so
            # they will be off by an hour. This is kind of weird
            self.assertEqual(now_dt_tt[:2], dt_no_tz_tt[:2])
            self.assertEqual(now_dt_tt[4:7], dt_no_tz_tt[4:7])

            # add an hour for comparisons
            dt_no_tz_dst = dt_no_tz
            dt_no_tz_dst = dt_no_tz + datetime.timedelta(hours=1)
            self.assertEqual(now_dt_tt[3], dt_no_tz_dst.timetuple()[3])
        else:
            self.assertEqual(now_dt_tt[:7], dt_no_tz_tt[:7])

    def test_local_tz_now(self):
        self._test_local_tz()

    def test_local_tz_not_dst(self):
        time.daylight = 0
        self._test_local_tz()

    def test_local_tz_dst(self):
        time.daylight = 1
        self._test_local_tz()

    def test_server_date_utc_timezone(self):
        # sample date from json response from server
        server_date = "2012-04-10T00:00:00.000+0000"
        dt = isodate.parse_date(server_date)
        # no dst
        self.assertEqual(datetime.timedelta(seconds=0), dt.tzinfo.dst(dt))
        # it's a utc date, no offset
        self.assertEqual(datetime.timedelta(seconds=0), dt.tzinfo.utcoffset(dt))

    def test_server_date_est_timezone(self):
        est_date = "2012-04-10T00:00:00.000-04:00"
        dt = isodate.parse_date(est_date)
        self.assertEqual(abs(datetime.timedelta(hours=-4)), abs(dt.tzinfo.utcoffset(dt)))

    # just past the 32bit unix epoch
    def test_2038_bug(self):
        parsed = isodate.parse_date("2038-11-24T00:00:00.000+0000")
        # this should be okay with either time parser, even on
        # 32bit platforms. maybe
        self.assertEqual(2038, parsed.year)
        self.assertEqual(11, parsed.month)
        self.assertEqual(24, parsed.day)

    def test_9999_bug(self):
        parsed = isodate.parse_date("9999-09-06T00:00:00.000+0000")
        # depending on what sys modules are available, the different
        # parser handle overflow slightly differently
        if isodate.parse_date_impl_name == 'dateutil':
            self._dateutil_overflow(parsed)
        else:
            self._pyxml_overflow(parsed)

    def test_10000_bug(self):
        # dateutil is okay up to 9999, so we just return
        # 9999-9-6 after that since that's what datetime/dateutil do
        # on RHEL5, y10k breaks pyxml with a value error
        parsed = isodate.parse_date("10000-09-06T00:00:00.000+0000")
        if isodate.parse_date_impl_name == 'dateutil':
            self._dateutil_overflow(parsed)
        else:
            self._pyxml_overflow(parsed)

    def _dateutil_overflow(self, parsed):
        self.assertEqual(9999, parsed.year)

    # Simulated a 32-bit date overflow, date should have been
    # replaced by one that does not overflow:
    def _pyxml_overflow(self, parsed):
        # the expected result here is different for 32bit or 64 bit
        # platforms, so except either
        if (parsed.year != 2038) and (parsed.year != 9999):
            self.fail("parsed year should be 2038 on 32bit, or 9999 on 64bit")
