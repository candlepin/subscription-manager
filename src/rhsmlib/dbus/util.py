# Copyright (c) 2016 Red Hat, Inc.
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
import logging
import sys
import decorator
import dbus.service

from rhsmlib.dbus import exceptions

log = logging.getLogger(__name__)

__all__ = [
    'dbus_handle_exceptions',
    'dbus_service_method',
]


@decorator.decorator
def dbus_handle_exceptions(func, *args, **kwargs):
    """Decorator to handle exceptions, log them, and wrap them if necessary"""
    try:
        ret = func(*args, **kwargs)
        return ret
    except dbus.DBusException as e:
        log.exception(e)
        raise
    except Exception as e:
        log.exception(e)
        trace = sys.exc_info()[2]
        raise exceptions.RHSM1DBusException("%s: %s" % (type(e).__name__, str(e))), None, trace


def dbus_service_method(*args, **kwargs):
    # Tell python-dbus that "sender" will be the keyword to use for the sender unless otherwise
    # defined.
    kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)
