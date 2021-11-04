import unittest

import locale

from datetime import datetime
from dateutil.tz import tzutc, tzstr
from mock import patch

from subscription_manager import managerlib


class TestFormatTime(unittest.TestCase):
    def setUp(self):
        self.locale = locale.getlocale()
        locale.setlocale(locale.LC_ALL, 'en_US')

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self.locale)

    @patch('subscription_manager.managerlib.tzlocal')
    def test_system_dst(self, mock_tz):
        mock_tz.return_value = tzstr('EST5EDT')
        test = datetime(2014, 12, 21, 4, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 5, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 5, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 3, 49, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 4, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 4, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')

        test = datetime(2014, 5, 21, 4, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 5, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 5, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 3, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 4, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 4, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')

    @patch('subscription_manager.managerlib.tzlocal')
    def test_system_est(self, mock_tz):
        mock_tz.return_value = tzstr('EST5EDT')
        test = datetime(2014, 12, 21, 4, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 5, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 5, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 3, 49, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 4, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')
        test = datetime(2014, 12, 21, 4, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '12/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-12-21')

        test = datetime(2014, 5, 21, 4, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 5, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 5, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 3, 59, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/20/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 4, 0, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
        test = datetime(2014, 5, 21, 4, 1, 0, tzinfo=tzutc())
        self.assertEqual(managerlib.format_date(test), '05/21/2014')
        self.assertEqual(managerlib.format_iso8601_date(test), '2014-05-21')
