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
from typing import TYPE_CHECKING

import dbus
import json
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services import syspurpose
from syspurpose.files import SyspurposeStore

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import ungettext
from subscription_manager.i18n import Locale

if TYPE_CHECKING:
    from rhsm.connection import UEPConnection

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
                    existing_value=value,
                )
            )
        conflict_msg = ", ".join(conflicts)
        return ungettext(
            "Warning: The following field was recently set "
            "for this system by the entitlement server "
            "administrator: {conflict_msg}",
            "Warning: The following fields were recently set "
            "for this system by the entitlement server "
            "administrator: {conflict_msg}",
            len(conflicts),
        ).format(conflict_msg=conflict_msg)


class SyspurposeDBusImplementation(base_object.BaseImplementation):
    def get_system_purpose(self) -> dict:
        system_purpose_path: str = "/etc/rhsm/syspurpose/syspurpose.json"
        store = SyspurposeStore.read(system_purpose_path)

        try:
            contents: dict = store.contents
        except Exception as exc:
            raise dbus.DBusException(str(exc))

        return contents

    def get_system_purpose_status(self) -> str:
        uep: "UEPConnection" = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(uep)

        raw_status: str = system_purpose.get_syspurpose_status()["status"]
        status: str = system_purpose.get_overall_status(raw_status)

        return status

    def get_valid_fields(self) -> dict:
        uep: "UEPConnection" = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(uep)

        valid_fields: dict = system_purpose.get_owner_syspurpose_valid_fields()
        # FIXME The call never returns None, but it may return empty dictionary
        if valid_fields is None:
            if self.is_registered():
                raise dbus.DBusException("Unable to get valid system purpose fields.")
            else:
                raise dbus.DBusException(
                    "Unable to get valid system purpose fields. The system is not registered."
                )

        return valid_fields

    def set_system_purpose(self, values: dict) -> dict:
        uep: "UEPConnection" = self.build_uep({})
        system_purpose = syspurpose.Syspurpose(uep)

        new_values: dict = system_purpose.set_syspurpose_values(values)

        conflicts = {}
        for key, value in new_values.items():
            if key in values and values[key] != value:
                conflicts[key] = value
        if conflicts:
            raise ThreeWayMergeConflict(conflict_fields=conflicts)

        return new_values


class SyspurposeDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to get
    information about current system purpose.
    """

    default_dbus_path = constants.SYSPURPOSE_DBUS_PATH
    interface_name = constants.SYSPURPOSE_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(SyspurposeDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.impl = SyspurposeDBusImplementation()

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature="s",
        out_signature="s",
    )
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetSyspurpose(self, locale, sender=None):
        """
        D-Bus method for getting current system purpose
        :param locale: string with locale
        :param sender:
        :return: json representation of system purpose contents
        """
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        system_purpose: dict = self.impl.get_system_purpose()
        return json.dumps(system_purpose)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature="s",
        out_signature="s",
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

        status = self.impl.get_system_purpose_status()
        return status

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature="s",
        out_signature="s",
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

        valid_fields = self.impl.get_valid_fields()
        return json.dumps(valid_fields)

    @util.dbus_service_method(
        constants.SYSPURPOSE_INTERFACE,
        in_signature="a{sv}s",
        out_signature="s",
    )
    @util.dbus_handle_sender
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

        new_values = self.impl.set_system_purpose(syspurpose_values)
        return json.dumps(new_values)

    @util.dbus_service_signal(
        constants.SYSPURPOSE_INTERFACE,
        signature="",
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
