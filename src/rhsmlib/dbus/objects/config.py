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
import rhsmlib.dbus as common

log = logging.getLogger(__name__)


class Config(dbus.service.Object):
    default_dbus_path = common.CONFIG_DBUS_PATH

    """ Represents the system config """
    @common.dbus_service_method(
        dbus_interface=common.CONFIG_INTERFACE,
        in_signature='',
        out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"
