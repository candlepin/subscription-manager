from __future__ import print_function, division, absolute_import

#
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
#

"""
This module containst class of D-Bus object used for unregistering
system from Candlepin server.
"""

import dbus
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.unregister import UnregisterService

from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.utils import restart_virt_who
from subscription_manager.i18n import Locale

init_dep_injection()

log = logging.getLogger(__name__)


class UnregisterDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to unregister
    system form Candlepin server.
    """
    default_dbus_path = constants.UNREGISTER_DBUS_PATH
    interface_name = constants.UNREGISTER_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(UnregisterDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.UNREGISTER_INTERFACE,
        in_signature='a{sv}s',
        out_signature='')
    @util.dbus_handle_exceptions
    def Unregister(self, proxy_options, locale, sender=None):
        """
        Definition and implementation of D-Bus method
        :param proxy_options: Definition of proxy settings
        :param locale: String with locale (e.g. de_DE.UTF-8)
        :param sender: Not used argument
        """
        proxy_options = dbus_utils.dbus_to_python(proxy_options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)

        self.ensure_registered()

        uep = self.build_uep(proxy_options, proxy_only=True)

        try:
            UnregisterService(uep).unregister()
        except Exception as err:
            raise dbus.DBusException(str(err))

        # The system is unregistered now, restart virt-who to stop sending
        # host-to-guest mapping.
        restart_virt_who()
