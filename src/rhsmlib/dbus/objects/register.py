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
import json
import logging
import threading
import dbus.service

from rhsmlib.dbus import constants, exceptions, dbus_utils, base_object, server, util
from rhsmlib.services.register import RegisterService

from subscription_manager.i18n import Locale

log = logging.getLogger(__name__)


class RegisterDBusObject(base_object.BaseObject):
    default_dbus_path = constants.REGISTER_DBUS_PATH
    interface_name = constants.REGISTER_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(RegisterDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)
        self.started_event = threading.Event()
        self.stopped_event = threading.Event()
        self.server = None
        self.lock = threading.Lock()

    @util.dbus_service_method(
        constants.REGISTER_INTERFACE,
        in_signature='s',
        out_signature='s')
    @util.dbus_handle_exceptions
    def Start(self, locale, sender=None):
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)

        with self.lock:
            if self.server:
                return self.server.address

            log.debug('Attempting to create new domain socket server')
            self.server = server.DomainSocketServer(
                object_classes=[DomainSocketRegisterDBusObject],
            )
            address = self.server.run()
            log.debug('DomainSocketServer created and listening on "%s"', address)
            return address

    @util.dbus_service_method(
        constants.REGISTER_INTERFACE,
        in_signature='s',
        out_signature='b')
    @util.dbus_handle_exceptions
    def Stop(self, locale, sender=None):
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)
        Locale.set(locale)
        with self.lock:
            if self.server:
                self.server.shutdown()
                self.server = None
                log.debug("Stopped DomainSocketServer")
                return True
            else:
                raise exceptions.Failed("No domain socket server is running")


class DomainSocketRegisterDBusObject(base_object.BaseObject):
    interface_name = constants.PRIVATE_REGISTER_INTERFACE
    default_dbus_path = constants.PRIVATE_REGISTER_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None):
        # On our DomainSocket DBus server since a private connection is not a "bus", we have to treat
        # it slightly differently. In particular there are no names, no discovery and so on.
        super(DomainSocketRegisterDBusObject, self).__init__(
            conn=conn,
            object_path=object_path,
            bus_name=bus_name
        )

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sssa{sv}a{sv}s',
        out_signature='s'
    )
    @util.dbus_handle_exceptions
    def Register(self, org, username, password, options, connection_options, locale):
        """
        This method registers the system using basic auth
        (username and password for a given org).
        For any option that is required but not included the default will be
        used.

        Options is a dict of strings that modify the outcome of this method.

        Note this method is registration ONLY.  Auto-attach is a separate process.
        """
        if self.is_registered():
            raise dbus.DBusException("This system is already registered")

        org = dbus_utils.dbus_to_python(org, expected_type=str)
        connection_options = dbus_utils.dbus_to_python(connection_options, expected_type=dict)
        connection_options['username'] = dbus_utils.dbus_to_python(username, expected_type=str)
        connection_options['password'] = dbus_utils.dbus_to_python(password, expected_type=str)
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)
        cp = self.build_uep(connection_options)

        register_service = RegisterService(cp)
        consumer = register_service.register(org, **options)
        return json.dumps(consumer)

    @dbus.service.method(
        dbus_interface=constants.PRIVATE_REGISTER_INTERFACE,
        in_signature='sasa{sv}a{sv}s',
        out_signature='s')
    @util.dbus_handle_exceptions
    def RegisterWithActivationKeys(self, org, activation_keys, options, connection_options, locale):
        """
        Note this method is registration ONLY.  Auto-attach is a separate process.
        """
        connection_options = dbus_utils.dbus_to_python(connection_options, expected_type=dict)
        options = dbus_utils.dbus_to_python(options, expected_type=dict)
        options['activation_keys'] = dbus_utils.dbus_to_python(activation_keys, expected_type=list)
        org = dbus_utils.dbus_to_python(org, expected_type=str)
        locale = dbus_utils.dbus_to_python(locale, expected_type=str)

        Locale.set(locale)
        cp = self.build_uep(connection_options)

        register_service = RegisterService(cp)
        consumer = register_service.register(org, **options)
        return json.dumps(consumer)
