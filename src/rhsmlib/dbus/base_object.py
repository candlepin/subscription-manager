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

from rhsmlib.dbus import base_properties

log = logging.getLogger(__name__)
common.init_root_logger()


class BaseObject(dbus.service.Object):
    # Name of the DBus interface provided by this object
    interface_name = common.INTERFACE_BASE
    service_name = common.BUS_NAME
    default_dbus_path = common.ROOT_DBUS_PATH

    def __init__(self, conn=None, object_path=None, bus_name=None,
                 base_object_path=None, service_name=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        if object_path is None or object_path == "":
            self.log.debug("object_path not set, creating default")
            base_object_path = base_object_path or self.__class__.default_dbus_path
            service_name = service_name or self.__class__.service_name
            object_path = base_object_path + \
                ("/" + service_name) if service_name else ""
            self.log.debug("Generated default object_path of"
                           " '%s' based on class attributes", object_path)
        self.log.debug("conn=%s", conn)
        self.log.debug("object_path=%s", object_path)
        self.log.debug("bus_name=%s", bus_name)
        self.log.debug("self._interface_name=%s", self._interface_name)
        self.log.debug("self.default_dbus_path=%s", self.default_dbus_path)

        super(BaseObject, self).__init__(conn=conn,
                                          object_path=object_path,
                                          bus_name=bus_name)
        self.object_path = object_path

        self._props = self._create_props()
        self.persistent = True

    def _create_props(self):
        properties = base_properties.BaseProperties.from_string_to_string_dict(
            self._interface_name,
            {'default_sample_prop': 'default_sample_value'},
            self.PropertiesChanged)
        return properties

    @property
    def props(self):
        # self.log.debug("accessing props @property")
        return self._props

    @dbus.service.signal(
        dbus_interface=common.INTERFACE_BASE,
        signature='')
    @common.dbus_handle_exceptions
    def ServiceStarted(self):
        self.log.debug("serviceStarted emit")

    # FIXME: more of a 'server' than 'service', so move it when we split
    def stop(self):
        """If there were shutdown tasks to do, do it here."""
        self.log.debug("shutting down")

    #
    # org.freedesktop.DBus.Properties interface
    #
    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        self.log.debug("Properties Changed emitted.")

    @common.dbus_service_method(
        dbus.PROPERTIES_IFACE,
        in_signature='s',
        out_signature='a{sv}')
    @common.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        self.log.debug("GetAll() interface_name=%s", interface_name)
        self.log.debug("sender=%s", sender)
        dr = dbus.Dictionary(self.props.get_all(interface_name=interface_name), signature='sv')
        self.log.debug('dr=%s', dr)
        return dr

    @common.dbus_service_method(
        dbus.PROPERTIES_IFACE,
        in_signature='ss',
        out_signature='v')
    @common.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        self.log.debug("Get() interface_name=%s property_name=%s", interface_name, property_name)
        self.log.debug("Get Property iface=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface_name=interface_name, property_name=property_name)

    @common.dbus_service_method(dbus.PROPERTIES_IFACE, in_signature='ssv')
    @common.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
        """Set a DBus property on this object.

        This is the base service class, and defaults to DBus properties
        being read-only. Attempts to Set a property will raise a
        DBusException of type org.freedesktop.DBus.Error.AccessDenied.

        Subclasses that need settable properties should override this."""

        log.debug("Set() interface_name=%s property_name=%s", interface_name, property_name)
        log.debug("Set() PPPPPPPPPPPPP self.props=%s %s", self.props, type(self.props))

        self.props.set(interface_name=interface_name, property_name=property_name, new_value=new_value)

    # Kluges

    # override the rhel7 slip version with a newer version that
    # includes upstream ea81f96a7746a4872e923b31dae646d1afa0043b
    # ie, don't listen to all NameOwnerChanged signals
    # TODO: This is likely optional on RHEL7, and should be removed
    #       especially if python-slip gets updated for RHEL7.
    def sender_seen(self, sender):
        if (sender, self.connection) not in BaseObject.senders:
            BaseObject.senders.add((sender, self.connection))
            if self.connection not in BaseObject.connections_senders:
                BaseObject.connections_senders[self.connection] = set()
                BaseObject.connections_smobjs[self.connection] = \
                    self.connection.add_signal_receiver(
                        handler_function=self._name_owner_changed,
                        signal_name='NameOwnerChanged',
                        dbus_interface='org.freedesktop.DBus',
                        arg1=sender)
            BaseObject.connections_senders[self.connection].add(sender)
