#
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
#


# try to find a reasonable iso8601 date format parser

import datetime
import logging

log = logging.getLogger('rhsm-app.' + __name__)

# 2038-01-01, used as the default when we hit an date overflow on
# 32-bit systems:
OVERFLOW_DATE = 2145916800.0


class ServerTz(datetime.tzinfo):
    """
    tzinfo object for the tz offset of the entitlement server
    """

    def __init__(self, offset):
        self.__offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self.__offset

    def dst(self, dt):
        return datetime.timedelta(seconds=0)


# we want parse_date to just work. Assume we have dateutil,
# if we can't  import that, try PyXML. RHEL6+ have dateutil,
# RHEL5 has pyxml (and pyxml is likely going away for rhel6+,
# at least in base install)
def _parse_date_pyxml(date):
    # so this get's a little ugly. We want to know the
    # tz/utc offset of the time, so we can make the datetime
    # object be not "naive". In theory, we will always get
    # these timestamps in UTC, but if we can figure it out,
    # might as well
    matches = xml.utils.iso8601.__datetime_rx.match(date)

    # parse out the timezone offset
    offset = xml.utils.iso8601.__extract_tzd(matches)

    # create a new tzinfo using that offset
    server_tz = ServerTz(offset)

    # create a new datetime this time using the timezone
    # so we aren't "naive"
    try:
        posix_time = xml.utils.iso8601.parse(date)
    except OverflowError:
        # Handle dates above 2038 on 32-bit systems by swapping it out with
        # 2038-01-01. (which should be ok) Such a system is quite clearly
        # in big trouble come that date, we just want to make sure they
        # can still list such subscription now.
        log.warning("Date overflow: %s, using Jan 1 2038 instead." % date)
        posix_time = OVERFLOW_DATE

    dt = datetime.datetime.fromtimestamp(posix_time, tz=server_tz)
    return dt


def _parse_date_dateutil(date):
    # see comment for _parse_date_pyxml
    try:
        dt = dateutil.parser.parse(date)
    except ValueError:
        log.warning("Date overflow: %s, using 9999-09-06 instead." % date)
        return dateutil.parser.parse("9999-09-06T00:00:00.000+0000")

    return dt

try:
    import dateutil.parser
    parse_date = _parse_date_dateutil
    parse_date_impl_name = 'dateutil'
except ImportError:
    # now try pyxml
    try:
        import xml.utils.iso8601
        parse_date = _parse_date_pyxml
        parse_date_impl_name = 'pyxml'
    # if we can't import either,
    # we have broken package deps...
    except ImportError:
        # if we found neither raise an ImportError communicating that
        # we needed one ot the other and found neither
        raise ImportError("No suitable date parsing module found ('dateutil', nor 'xml.utils.iso8601')")
