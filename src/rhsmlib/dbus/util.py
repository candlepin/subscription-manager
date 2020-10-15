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
import re

from rhsmlib.dbus import exceptions
from rhsmlib.client_info import DBusSender

log = logging.getLogger(__name__)

__all__ = [
    'dbus_handle_exceptions',
    'dbus_handle_sender',
    'dbus_service_method',
    'dbus_service_signal'
]


@decorator.decorator
def dbus_handle_sender(func, *args, **kwargs):
    """
    Decorator to handle sender argument
    :param func: method with implementation of own logic of D-Bus method
    :param args: arguments of D-Bus method
    :param kwargs: keyed arguments of D-Bus method
    :return: result of D-Bus method
    """

    sender = None
    # Get sender from arguments
    if 'sender' in kwargs:
        sender = kwargs['sender']
    elif len(args) > 0:
        sender = args[-1]

    with DBusSender() as dbus_sender:
        if sender is not None:
            dbus_sender.set_cmd_line(sender)

        try:
            return func(*args, **kwargs)
        finally:
            if sender is not None:
                # When sender was specified, then reset it
                dbus_sender.reset_cmd_line()


@decorator.decorator
def dbus_handle_exceptions(func, *args, **kwargs):
    """
    Decorator to handle exceptions, log them, and wrap them if necessary.
    """

    try:
        return func(*args, **kwargs)
    except Exception as err:
        log.exception(err)
        trace = sys.exc_info()[2]

        severity = "error"
        # Remove "HTTP error (...): " string from the messages:
        pattern = '^HTTP error \x28.*\x29: '
        err_msg = re.sub(pattern, '', str(err))
        # Modify severity of some exception here
        if "Ignoring request to auto-attach. It is disabled for org" in err_msg:
            severity = "warning"
        if hasattr(err, 'severity'):
            severity = err.severity
        # Raise exception string as JSON string. Thus it can be parsed and printed properly.
        error_msg = json.dumps(
            {
                "exception": type(err).__name__,
                "severity": severity,
                "message": err_msg
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
