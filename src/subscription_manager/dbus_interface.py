from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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

import dbus
import dbus.mainloop
import dbus.mainloop.glib

import inspect
import traceback
import sys
import logging
import subscription_manager.injection as inj

log = logging.getLogger(__name__)


class DbusIface(object):

    service_name = 'com.redhat.SubscriptionManager'

    def __init__(self):
        try:
            # Only follow names if there is a default main loop
            self.has_main_loop = self._get_main_loop() is not None
            log.debug("self.has_main_loop=%s", self.has_main_loop)
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

            self.bus = dbus.SystemBus()
            validity_obj = self._get_validity_object(self.service_name,
                    '/EntitlementStatus',
                    follow_name_owner_changes=self.has_main_loop)
            self.validity_iface = dbus.Interface(validity_obj,
                    dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus')

            # Activate methods now that we're connected
            # Avoids some messy exception handling if dbus isn't installed
            self.update = self._update
        except dbus.DBusException:
            # we can't connect to dbus. it's not running, likely from a minimal
            # install. we can't do anything here, so just ignore it.
            log.debug("Unable to connect to dbus")
            # BZ 1600694 We should print the dbus traceback at the debug level
            log.debug(''.join(traceback.format_tb(sys.exc_info()[2])))

    def update(self):
        pass

    def _update(self):
        try:
            self.validity_iface.update_status(
                    inj.require(inj.CERT_SORTER).get_status_for_icon(),
                    ignore_reply=self.has_main_loop)
        except dbus.DBusException as e:
            # Should be unreachable in the gui
            log.debug("Failed to update rhsmd")
            log.exception(e)

    # RHEL5 doesn't support 'follow_name_owner_changes'
    def _get_validity_object(self, *args, **kwargs):
        iface_args = inspect.getargspec(self.bus.get_object)[0]
        if 'follow_name_owner_changes' not in iface_args and \
                'follow_name_owner_changes' in kwargs:
            log.debug("installed python-dbus doesn't support 'follow_name_owner_changes'")
            del kwargs['follow_name_owner_changes']
        return self.bus.get_object(*args, **kwargs)

    # RHEL5 doesn't support 'get_default_main_loop'
    def _get_main_loop(self):
        if not hasattr(dbus, "get_default_main_loop"):
            log.debug("installed python-dbus doesn't support 'get_default_main_loop'")
            return None
        return dbus.get_default_main_loop()
