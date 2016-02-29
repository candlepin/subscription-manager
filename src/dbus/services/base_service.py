#!/usr/bin/python

import logging

log = logging.getLogger(__name__)

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service
import slip.dbus.introspection

from rhsm.dbus.common import decorators
from rhsm.dbus.common import constants
from rhsm.dbus.services import base_properties
#from rhsm.dbus.common import dbus_utils


class BaseService(slip.dbus.service.Object):

    persistent = True
    # Name of the DBus interface provided by this object
    _interface_name = constants.DBUS_INTERFACE
    default_polkit_auth_required = constants.PK_ACTION_DEFAULT
    default_dbus_path = constants.ROOT_DBUS_PATH
    default_polkit_auth_required = None

    def __init__(self, conn=None, object_path=None, bus_name=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.log.debug("conn=%s", conn)
        self.log.debug("object_path=%s", object_path)
        self.log.debug("bus_name=%s", bus_name)
        self.log.debug("self._interface_name=%s", self._interface_name)
        self.log.debug("self.default_dbus_path=%s", self.default_dbus_path)

        super(BaseService, self).__init__(conn=conn,
                                          object_path=self.default_dbus_path,
                                          bus_name=bus_name)

        self._props = self._create_props()
        self.persistent = True

    def _create_props(self):
        properties = base_properties.BaseProperties.from_string_to_string_dict(self._interface_name,
                                                                               {'default_sample_prop':
                                                                                'default_sample_value'},
                                                                               self.PropertiesChanged)
        return properties

    @property
    def props(self):
        self.log.debug("accessing props @property")
        return self._props

    @dbus.service.signal(dbus_interface=constants.DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        self.log.debug("serviceStarted emit")

    # FIXME: more of a 'server' than 'service', so move it when we split
    def stop(self):
        """If there were shutdown tasks to do, do it here."""
        self.log.debug("shutting down")

    @dbus.service.method(dbus.INTROSPECTABLE_IFACE, in_signature='', out_signature='s',
                        path_keyword='object_path', connection_keyword='connection')
    def Introspect(self, object_path, connection):
        ret = super(BaseService, self).Introspect(object_path, connection)
        self.log.debug("super.Introspect ret=%s", ret)
        bloop = self.props.add_introspection_xml(ret)
        return bloop

    #
    # org.freedesktop.DBus.Properties interface
    #
    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.log.debug("Properties Changed emitted.")

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='s',
                                    out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        self.log.debug("GetAll() interface_name=%s", interface_name)
        self.log.debug("sender=%s", sender)
        dr = dbus.Dictionary(self.props.get_all(interface_name=interface_name),
                             signature='sv')
        self.log.debug('dr=%s', dr)
        return dr

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        self.log.debug("Get() interface_name=%s property_name=%s", interface_name, property_name)
        self.log.debug("Get Property iface=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface_name=interface_name,
                              property_name=property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ssv')
    @decorators.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
        """Set a DBus property on this object.

        This is the base service class, and defaults to DBus properties
        being read-only. Attempts to Set a property will raise a
        DBusException of type org.freedesktop.DBus.Error.AccessDenied.

        Subclasses that need settable properties should override this."""

        log.debug("Set() interface_name=%s property_name=%s", interface_name, property_name)
        log.debug("Set() PPPPPPPPPPPPP self.props=%s %s", self.props, type(self.props))

        self.props.set(interface_name=interface_name,
                       property_name=property_name,
                       new_value=new_value)

    # Kluges

    # override the rhel7 slip version with a newer version that
    # includes upstream ea81f96a7746a4872e923b31dae646d1afa0043b
    # ie, don't listen to all NameOwnerChanged signals
    # TODO: This is likely optional on RHEL7, and should be removed
    #       especially if python-slip gets updated for RHEL7.
    def sender_seen(self, sender):
        if (sender, self.connection) not in BaseService.senders:
            BaseService.senders.add((sender, self.connection))
            if self.connection not in BaseService.connections_senders:
                BaseService.connections_senders[self.connection] = set()
                BaseService.connections_smobjs[self.connection] = \
                    self.connection.add_signal_receiver(
                        handler_function=self._name_owner_changed,
                        signal_name='NameOwnerChanged',
                        dbus_interface='org.freedesktop.DBus',
                        arg1=sender)
            BaseService.connections_senders[self.connection].add(sender)
