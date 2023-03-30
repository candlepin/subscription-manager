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

from rhsmlib.dbus import constants, exceptions, util

from subscription_manager import utils
from subscription_manager import injection as inj
from subscription_manager.injectioninit import init_dep_injection

from rhsmlib.services import config
import rhsm.config

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

    def validate_only_proxy_options(self, proxy_options):
        error_msg = None
        for k in six.iterkeys(proxy_options):
            if k not in ['proxy_hostname', 'proxy_port', 'proxy_user', 'proxy_password', 'no_proxy']:
                error_msg = "Error: %s is not a valid proxy option" % k
                break

        if error_msg:
            raise exceptions.Failed(msg=error_msg)

        return proxy_options

    def is_registered(self):
        return inj.require(inj.IDENTITY).is_valid()

    def ensure_registered(self):
        if not self.is_registered():
            raise dbus.DBusException(
                "This object requires the consumer to be registered before it can be used."
            )

    def build_uep(self, options, proxy_only=False, basic_auth_method=False):
        conf = config.Config(rhsm.config.get_config_parser())
        # Some commands/services only allow manipulation of the proxy information for a connection
        cp_provider = inj.require(inj.CP_PROVIDER)
        if proxy_only:
            self.validate_only_proxy_options(options)

        connection_info = {}

        server_sec = conf['server']
        connection_info['host'] = options.get('host', server_sec['hostname'])
        connection_info['ssl_port'] = options.get('port', server_sec.get_int('port'))
        connection_info['handler'] = options.get('handler', server_sec['prefix'])

        connection_info['proxy_hostname_arg'] = options.get('proxy_hostname', server_sec['proxy_hostname'])
        connection_info['proxy_port_arg'] = options.get('proxy_port', server_sec.get_int('proxy_port'))
        connection_info['proxy_user_arg'] = options.get('proxy_user', server_sec['proxy_user'])
        connection_info['proxy_password_arg'] = options.get('proxy_password', server_sec['proxy_password'])
        connection_info['no_proxy_arg'] = options.get('no_proxy', server_sec['no_proxy'])

        cp_provider.set_connection_info(**connection_info)
        cp_provider.set_correlation_id(utils.generate_correlation_id())

        if self.is_registered() and basic_auth_method is False:
            return cp_provider.get_consumer_auth_cp()
        elif 'username' in options and 'password' in options:
            cp_provider.set_user_pass(options['username'], options['password'])
            return cp_provider.get_basic_auth_cp()
        else:
            return cp_provider.get_no_auth_cp()

    @util.dbus_service_method(
        constants.DBUS_PROPERTIES_INTERFACE,
        in_signature='s',
        out_signature='a{sv}')
    @util.dbus_handle_sender
    @util.dbus_handle_exceptions
    def GetAll(self, _, sender=None):

        return dbus.Dictionary({}, signature='sv')
