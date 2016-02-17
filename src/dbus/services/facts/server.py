#!/usr/bin/python

import logging

log = logging.getLogger(__name__)

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.facts import admin_facts

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_service
from rhsm.dbus.services import base_properties
from rhsm.dbus.services.facts_user import server
from rhsm.dbus.common import dbus_utils

# Note facts and facts-root provide the same interface on
# different object paths
#FACTS_ROOT_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.Root"
FACTS_ROOT_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_ROOT_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/Root"
PK_FACTS_ROOT_COLLECT = "com.redhat.Subscriptions1.Facts.Root.collect"


class FactsRoot(server.FactsUser):

    default_polkit_auth_required = PK_FACTS_ROOT_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = FACTS_ROOT_DBUS_PATH
    default_props_data = {'version': '11',
                          'daemon': 'root',
                          'answer': '42',
                          'polkit_auth_action': PK_FACTS_ROOT_COLLECT,
                          'last_update': 'before now, probably'}
#    default_dbus_name = FACTS_ROOT_DBUS_BUS_NAME

    def __init__(self, *args, **kwargs):
        super(FactsRoot, self).__init__(*args, **kwargs)

        self._interface_name = FACTS_ROOT_DBUS_INTERFACE

        self._props = base_properties.BaseProperties(interface=self._interface_name,
                                                     data={},
                                                     prop_changed_callback=self.PropertiesChanged)

    @slip.dbus.polkit.require_auth(PK_FACTS_ROOT_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_ROOT_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total

    @slip.dbus.polkit.require_auth(PK_FACTS_ROOT_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_ROOT_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        return '42'

    @dbus.service.signal(dbus_interface=FACTS_ROOT_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("Facts serviceStarted emit")

    #@slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='s',
                                    out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
        interface_name = dbus_utils.dbus_to_python(interface_name, str)
        log.debug("GetAll() interface_name=%s", interface_name)
        log.debug("sender=%s", sender)
        return {}
        #pass
        # TODO: use better test type conversion ala dbus_utils.py
#        log.debug("GetAll interface_name=%s, sender=%s", interface_name, sender)

#        return self.props.get_all(interface=interface_name)

    #@slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ss',
                                    out_signature='v')
    @decorators.dbus_handle_exceptions
    def Get(self, interface_name, property_name, sender=None):
        interface_name = dbus_utils.dbus_to_python(interface_name, str)
        property_name = dbus_utils.dbus_to_python(property_name, str)
        log.debug("Get() interface_name=%s property_name=%s", interface_name, property_name)
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface=interface_name,
                              prop=property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ssv')
    @decorators.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
        interface_name = dbus_utils.dbus_to_python(interface_name, str)
        property_name = dbus_utils.dbus_to_python(property_name, str)
        log.debug("Set() interface_name=%s property_name=%s", interface_name, property_name)

        self.props.set(interface=interface_name,
                       prop=property_name,
                       value=new_value)
        self.PropertiesChanged(interface_name,
                               {property_name: new_value},
                               [])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        log.debug("Properties Changed emitted.")


def run():
    base_service.service_classes.append(base_service.BaseService)
    base_service.service_classes.append(FactsRoot)
    base_service.service_classes.append(server.FactsUser)
    base_service.run()
    #base_service.run_service(dbus.SystemBus,
    #                         FACTS_ROOT_DBUS_BUS_NAME,
    #                         FACTS_ROOT_DBUS_INTERFACE,
    #                         FactsRoot)
