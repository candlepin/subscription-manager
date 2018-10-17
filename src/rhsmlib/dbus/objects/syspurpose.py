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
from subscription_manager import injection as inj

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import Locale

init_dep_injection()

log = logging.getLogger(__name__)


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
        in_signature='',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def GetSyspurposeStatus(self, sender=None):
        cp = inj.require(inj.CP_PROVIDER).get_consumer_auth_cp()
        systempurpose = syspurpose.Syspurpose(cp)
        syspurpose_status = systempurpose.get_syspurpose_status()['status']
        return systempurpose.get_overall_status(syspurpose_status)

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
