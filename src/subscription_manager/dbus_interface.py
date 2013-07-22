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


class DbusIface(object):

    def __init__(self):
        bus = dbus.SystemBus()
        validity_obj = bus.get_object('com.redhat.SubscriptionManager',
                '/EntitlementStatus')
        self.validity_iface = dbus.Interface(validity_obj,
                dbus_interface='com.redhat.SubscriptionManager.EntitlementStatus')

    def update(self):
        self.validity_iface.check_status(ignore_reply=True)
