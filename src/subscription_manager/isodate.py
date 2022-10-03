# find a reasonable iso8601 date parser
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

import datetime
import dateutil.parser
import logging

log = logging.getLogger(__name__)


def _parse_date_dateutil(date: str) -> datetime.datetime:
    try:
        dt: datetime.datetime = dateutil.parser.parse(date)
        # the datetime.datetime objects returned by dateutil use the own
        # dateutil.tz.tzutc object for UTC, rather than the datetime own;
        # switch the tzinfo object of UTC dates to datetime.timezone.utc:
        # this is done because classes in the standard Python library
        # explicitly check for that object for UTC checks
        if dt.tzinfo.tzname(dt) == "UTC":
            dt = dt.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        log.warning("Date overflow: %s, using 9999-09-06 instead." % date)
        return dateutil.parser.parse("9999-09-06T00:00:00.000+0000")

    return dt


parse_date = _parse_date_dateutil
parse_date_impl_name = "dateutil"
