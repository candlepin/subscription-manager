from __future__ import print_function, division, absolute_import

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
import six
import dbus.service

from rhsmlib.dbus import constants, exceptions, dbus_utils

from subscription_manager import injection as inj
from subscription_manager.injectioninit import init_dep_injection

init_dep_injection()

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

    def validate_proxy_options(self, proxy_options):
        error_msg = None
        for k in six.iterkeys(proxy_options):
            if k not in ['proxy_hostname', 'proxy_port', 'proxy_user', 'proxy_password', 'no_proxy']:
                error_msg = "Error: %s is not a valid proxy option" % k
                break

        if error_msg:
            raise exceptions.Failed(msg=error_msg)

        return proxy_options

    def is_registered(self):
        identity = inj.require(inj.IDENTITY)
        return identity.is_valid()

    def ensure_registered(self):
        if not self.is_registered():
            raise dbus.DBusException(
                "This object requires the consumer to be registered before it can be used."
            )

    def build_proxy_information(self, proxy_options):
        proxy_options = dbus_utils.dbus_to_python(proxy_options, dict)
        proxy_options = self.validate_proxy_options(proxy_options)

        connection_info = {}
        for arg in ['proxy_hostname', 'proxy_port', 'proxy_user', 'proxy_password', 'no_proxy']:
            # Not sure why CPProvider takes all the proxy stuff as `whatever_arg` instead of just
            # `whatever`.
            if arg in proxy_options:
                connection_info['%s_arg' % arg] = proxy_options[arg]

        return connection_info
