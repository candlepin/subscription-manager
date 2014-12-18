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
import gobject
import logging
import subscription_manager.injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class DbusIface(object):

    service_name = 'com.redhat.SubscriptionManager'

    def __init__(self):
        try:
            self.bus = dbus.SystemBus()
            validity_obj = self.bus.get_object(self.service_name,
                    '/EntitlementStatus',
                    follow_name_owner_changes=dbus.get_default_main_loop())
            self.validity_iface = dbus.Interface(validity_obj,
                    dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus')

            # Activate methods now that we're connected
            # Avoids some messy exception handling if dbus isn't installed
            self.update = self._update
        except dbus.DBusException, e:
            # we can't connect to dbus. it's not running, likely from a minimal
            # install. we can't do anything here, so just ignore it.
            log.debug("Unable to connect to dbus")
            log.exception(e)

    def update(self):
        pass

    def update_status(self):
        self.validity_iface.update_status(
                inj.require(inj.CERT_SORTER).get_status_for_icon(),
                ignore_reply=dbus.get_default_main_loop)

    def emit_status(self):
        self.validity_iface.emit_status()

    def _update(self):
        try:
            gobject.idle_add(self.update_status)
            gobject.idle_add(self.emit_status)
        except dbus.DBusException, e:
            # Should be unreachable in the gui
            log.debug("Failed to update rhsmd")
            log.exception(e)
