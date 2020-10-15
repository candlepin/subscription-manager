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
This module contains implementation of D-Bus object representing consumer.
It uses interface: com.redhat.RHSM1.Consumer and path:
/com/redhat/RHSM1/Consumer
"""

import dbus
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.consumer import Consumer

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import Locale

init_dep_injection()

log = logging.getLogger(__name__)


class ConsumerDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to get
    information about current consumer.
    """
    default_dbus_path = constants.CONSUMER_DBUS_PATH
    interface_name = constants.CONSUMER_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(ConsumerDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.CONSUMER_INTERFACE,
        in_signature='s',
        out_signature='s')
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetUuid(self, locale, sender=None):
        """
        D-Bus method for getting current consumer UUID
        :param locale: string with locale
        :param sender:
        :return: string with UUID
        """

        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        consumer = Consumer()
        try:
            uuid = consumer.get_consumer_uuid()
        except Exception as err:
            raise dbus.DBusException(str(err))

        return str(uuid)

    @util.dbus_service_signal(
        constants.CONSUMER_INTERFACE,
        signature=''
    )
    @util.dbus_handle_exceptions
    def ConsumerChanged(self):
        """
        Signal fired, when consumer is created/deleted/changed
        :return: None
        """
        log.debug("D-Bus signal %s emitted" % constants.CONSUMER_INTERFACE)
        return None
