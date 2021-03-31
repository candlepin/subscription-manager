from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

"""
This module contains implementation of D-Bus object representing system purpose.
It uses interface: com.redhat.RHSM1.Syspurpose and path:
/com/redhat/RHSM1/Syspurpose
"""

import dbus
import json
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services import syspurpose
from syspurpose.files import SyspurposeStore

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import ungettext
from subscription_manager.i18n import Locale

init_dep_injection()

log = logging.getLogger(__name__)


class ThreeWayMergeConflict(dbus.DBusException):
    """
    Raise this exception, when client application tries to
    """
    _dbus_error_name = "%s.Error" % constants.SYSPURPOSE_INTERFACE
    include_traceback = False
    severity = "warn"

    def __init__(self, conflict_fields):
        """
        Initialize this exception
        :param conflict_fields: dictionary with conflicted attributes.
            The key is attribute and value is current value set on server.
        """
        self.conflict_fields = conflict_fields

    def __str__(self):
        """
        Text representation of exception
        :return: string of exception
        """
        conflicts = []
        for key, value in self.conflict_fields.items():
            conflicts.append(
                '{conflict_attr} of "{existing_value}"'.format(
                    conflict_attr=key,
                    existing_value=value
                )
            )
        conflict_msg = ", ".join(conflicts)
        return ungettext('Warning: A {conflict_msg} was recently set '
                         'for this system by the entitlement server administrator.',
                         'Warning: A {conflict_msg} were recently set '
                         'for this system by the entitlement server administrator.',
                         len(conflicts)).format(conflict_msg=conflict_msg)


class SyspurposeDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to get
    information about current system purpose.
    """
    default_dbus_path = constants.SYSPURPOSE_DBUS_PATH
    interface_name = constants.SYSPURPOSE_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(SyspurposeDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature='s',
        out_signature='s')
    @util.dbus_handle_exceptions
    def GetSyspurpose(self, locale, sender=None):
        """
        D-Bus method for getting current system purpose
        :param locale: string with locale
        :param sender:
        :return: json representation of system purpose contents
        """
        syspurpose_path = '/etc/rhsm/syspurpose/syspurpose.json'

        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        syspurpose_store = SyspurposeStore.read(syspurpose_path)

        try:
            contents = syspurpose_store.contents
        except Exception as err:
            raise dbus.DBusException(str(err))

        return json.dumps(contents)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature='s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetSyspurposeStatus(self, locale, sender=None):
        """
        D-Bus method for getting system purpose status
        :param locale: string representing locale
        :param sender: object representing application which called this method
        :return:
        """
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)
        cp = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(cp)
        syspurpose_status = system_purpose.get_syspurpose_status()['status']
        return system_purpose.get_overall_status(syspurpose_status)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature='s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetValidFields(self, locale, sender=None):
        """
        Method for getting valid syspurpose attributes and values
        :param locale: string with locale
        :param sender: object representing application which called this method
        :return: string representing dictionary with valid fields
        """
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)
        cp = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(cp)
        valid_fields = system_purpose.get_owner_syspurpose_valid_fields()
        if valid_fields is None:
            # When it is not possible to get valid fields, then raise exception
            if self.is_registered() is False:
                raise dbus.DBusException(
                    "Unable to get system purpose valid fields. System is not registered.",
                )
            else:
                raise dbus.DBusException(
                    "Unable to get system purpose valid fields.",
                )
        else:
            return json.dumps(valid_fields)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature='a{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def SetSyspurpose(self, syspurpose_values, locale, sender):
        """
        Set syspurpose values
        :param syspurpose_values: Dictionary with all syspurpose values
        :param locale: String with locale
        :param sender: Object representing client application that called this method
        :return: String with successfully set syspurpose values
        """
        syspurpose_values = dbus_utils.dbus_to_python(syspurpose_values, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        cp = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(cp)
        new_syspurpose_values = system_purpose.set_syspurpose_values(syspurpose_values)

        # Check if there was any conflict during three-way merge
        conflicts = {}
        for key, value in new_syspurpose_values.items():
            if key in syspurpose_values and syspurpose_values[key] != value:
                conflicts[key] = value
        if len(conflicts) > 0:
            raise ThreeWayMergeConflict(conflict_fields=conflicts)

        return json.dumps(new_syspurpose_values)

    @util.dbus_service_signal(
        constants.SYSPURPOSE_INTERFACE,
        signature=''
    )
    @util.dbus_handle_exceptions
    def SyspurposeChanged(self):
        """
        Signal fired, when system purpose is created/deleted/changed
        :param sender:
        :return: None
        """
        log.debug("D-Bus signal %s emitted" % constants.SYSPURPOSE_INTERFACE)
        return None
