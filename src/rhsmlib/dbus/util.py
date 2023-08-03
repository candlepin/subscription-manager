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
import dbus
import dbus.service
import json
import re

from rhsmlib.dbus import exceptions
from rhsmlib.client_info import DBusSender
from rhsmlib.dbus.dbus_utils import pid_of_sender, dbus_to_python

log = logging.getLogger(__name__)

__all__ = [
    "dbus_admin_auth_policy",
    "dbus_domain_admin_auth_policy",
    "dbus_handle_exceptions",
    "dbus_handle_sender",
    "dbus_service_method",
    "dbus_service_signal",
]


def _check_polkit_policy(sender, func, *args, **kwargs):
    """
    Check if given sender is authorized to call given function
    """
    bus = dbus.SystemBus()
    try:
        pid = pid_of_sender(bus, sender)
    except Exception as err:
        raise exceptions.RHSM1DBusException(f"Unable to get PID of sender: {sender}: {err}")
    dbus_obj = bus.get_object("org.freedesktop.PolicyKit1", "/org/freedesktop/PolicyKit1/Authority")
    dbus_iface = dbus.Interface(dbus_obj, "org.freedesktop.PolicyKit1.Authority")
    subject = (
        "unix-process",
        {"pid": dbus.UInt32(pid), "start-time": dbus.UInt64(0)}
    )
    # TODO: Modify code to be able to use at least two IDs (one for "register" and another
    #       for "unregister")
    action_id = "com.redhat.RHSM1.default"
    details = {}
    flags = 1
    cancellation_id = ""

    try:
        is_authorized, is_challenge, details = dbus_iface.CheckAuthorization(
            subject, action_id, details, flags, cancellation_id)
    except Exception as err:
        raise exceptions.RHSM1DBusException(f"Unable to check authorization of {sender}: {err}")
    else:
        is_authorized = dbus_to_python(is_authorized, expected_type=bool)
        if is_authorized is True:
            return func(*args, **kwargs)
        else:
            details = dbus_to_python(details, expected_type=dict)
            raise exceptions.RHSM1DBusException(f"{sender} is not authorized to call {func}: {details}")


@decorator.decorator
def dbus_admin_auth_policy(func, *args, **kwargs):
    """
    When this decorator is used, then it is required that sender process
    is admin authenticated. This is workaround for some applications using
    our D-Bus API.
    """

    sender = None
    # Get sender from arguments
    if "sender" in kwargs:
        sender = kwargs["sender"]
    elif len(args) > 0:
        sender = args[-1]

    if sender is not None:
        return _check_polkit_policy(sender, func, *args, **kwargs)
    else:
        raise exceptions.RHSM1DBusException(f"No sender specified, unable to check authorization for calling {func}")


@decorator.decorator
def dbus_domain_admin_auth_policy(func, *args, **kwargs):
    """
    This modified version of decorator dbus_admin_auth_policy(), but this could be
    used in the case, when unix socket is used for registration
    """
    # TODO: This does not work as expected and it is not used ATM.
    #       The pid_of_sender() in _check_polkit_policy() is not able to
    #       find process for some reason, but process communicating over
    #       unix socket should be authorized by polkit.
    with DBusSender() as dbus_sender:
        sender = dbus_sender.sender
        if sender is not None:
            return _check_polkit_policy(sender, func, *args, **kwargs)
        else:
            raise exceptions.RHSM1DBusException(
                f"No sender specified, unable to check authorization for calling {func}"
            )


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
    if "sender" in kwargs:
        sender = kwargs["sender"]
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
        pattern = "^HTTP error \x28.*\x29: "
        err_msg = re.sub(pattern, "", str(err))
        # Modify severity of some exception here
        if "Ignoring request to auto-attach. It is disabled for org" in err_msg:
            severity = "warning"
        if hasattr(err, "severity"):
            severity = err.severity
        # Raise exception string as JSON string. Thus it can be parsed and printed properly.
        error_msg = json.dumps(
            {
                "exception": type(err).__name__,
                "severity": severity,
                "message": err_msg,
            }
        )
        raise exceptions.RHSM1DBusException(error_msg).with_traceback(trace)


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
