from __future__ import print_function, division, absolute_import

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
import six
import decorator
import dbus.service
import json

from rhsmlib.dbus import exceptions

log = logging.getLogger(__name__)

__all__ = [
    'dbus_handle_exceptions',
    'dbus_service_method',
    'dbus_service_signal'
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
    except Exception as err:
        log.exception(err)
        trace = sys.exc_info()[2]
        # Raise exception string as JSON string. Thus it can be parsed and printed properly.
        error_msg = json.dumps(
            {
                "exception": type(err).__name__,
                "message": str(err)
            }
        )
        six.reraise(exceptions.RHSM1DBusException, exceptions.RHSM1DBusException(error_msg), trace)


def dbus_service_method(*args, **kwargs):
    # Tell python-dbus that "sender" will be the keyword to use for the sender unless otherwise
    # defined.
    kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)


def dbus_service_signal(*args, **kwargs):
    """
    Decorator used for signal
    :param args:
    :param kwargs:
    :return:
    """
    return dbus.service.signal(*args, **kwargs)
