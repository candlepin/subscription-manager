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
#

import logging
import dbus.service

from rhsmlib.dbus import constants, exceptions

log = logging.getLogger(__name__)


class BaseObject(dbus.service.Object):
    # Name of the DBus interface provided by this object
    interface_name = constants.INTERFACE_BASE
    default_dbus_path = constants.ROOT_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None):
        if object_path is None:
            object_path = self.default_dbus_path
        super(BaseObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    def _check_interface(self, interface_name):
        if interface_name != self.interface_name:
            raise exceptions.UnknownInterface(interface_name)
