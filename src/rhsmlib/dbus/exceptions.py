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
import dbus
from rhsmlib.dbus import constants

__all__ = [
    'RHSM1DBusException',
    'UnknownProperty',
    'UnknownInterface',
    'InvalidArguments',
    'AccessDenied',
    'PropertyMissing',
    'Failed',
]


class RHSM1DBusException(dbus.DBusException):
    """Base exceptions."""
    include_traceback = False
    _dbus_error_name = "%s.Error" % constants.INTERFACE_BASE


class UnknownProperty(dbus.DBusException):
    include_traceback = True

    def __init__(self, property_name):
        super(UnknownProperty, self).__init__(
            "Property '%s' does not exist" % property_name,
            name="org.freedesktop.DBus.Error.UnknownProperty"
        )


class UnknownInterface(dbus.DBusException):
    include_traceback = True

    def __init__(self, interface_name):
        super(UnknownInterface, self).__init__(
            "Interface '%s' is unknown" % interface_name,
            name="org.freedesktop.DBus.Error.UnknownInterface"
        )


class InvalidArguments(dbus.DBusException):
    include_traceback = True

    def __init__(self, argument):
        super(InvalidArguments, self).__init__(
            "Argument '%s' is invalid" % argument,
            name="org.freedesktop.DBus.Error.InvalidArgs"
        )


class AccessDenied(dbus.DBusException):
    include_traceback = True

    def __init__(self, prop, interface):
        super(AccessDenied, self).__init__(
            "Property '%s' isn't exported (or does not exist) on interface: %s" % (prop, interface),
            name="org.freedesktop.DBus.Error.AccessDenied"
        )


class PropertyMissing(dbus.DBusException):
    include_traceback = True

    def __init__(self, prop, interface):
        super(PropertyMissing, self).__init__(
            "Property '%s' does not exist on interface: %s" % (prop, interface),
            name="org.freedesktop.DBus.Error.AccessDenied"
        )


class Failed(dbus.DBusException):
    include_traceback = True

    def __init__(self, msg=None):
        super(Failed, self).__init__(
            msg or "Operation failed",
            name="org.freedesktop.DBus.Error.Failed"
        )
