#!/usr/bin/python

import logging

log = logging.getLogger(__name__)

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
#import slip.dbus.service

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_service
from rhsm.dbus.services import base_properties

from rhsm.facts import hwprobe

# TODO: move these to a config/constants module
#FACTS_USER_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.User"
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_USER_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/User"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.User.collect"


class FactsUser(base_service.BaseService):

    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    default_props_data = {'version': '-infinity+37',
                          'answer': '42',
                          'daemon': 'user',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'before now, probably'}
    facts_collector_class = hwprobe.Hardware
    default_dbus_path = FACTS_USER_DBUS_PATH
    #default_dbus_name = FACTS_USER_DBUS_BUS_NAME

    def __init__(self, *args, **kwargs):
        super(FactsUser, self).__init__(*args, **kwargs)
        self._interface_name = FACTS_DBUS_INTERFACE
        self.facts_collector = self.facts_collector_class()
        self._props = base_properties.BaseProperties(self._interface_name,
                                                     data=self.default_props_data,
                                                     prop_changed_callback=self.PropertiesChanged)

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @decorators.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        facts_dict = self.facts_collector.get_all()
        cleaned = dict([(str(key), str(value)) for key, value in facts_dict.items()])
        dbus_dict = dbus.Dictionary(cleaned, signature="ss")
        return dbus_dict

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        self.props.set(self._interface_name, 'answer', 'What was the question?')

        # FIXME: trigger a props chang signal for testing, this should
        #        become the duty of the properties object
        #self.PropertiesChanged(self._interface_name,
        #                       {'answer': 'What was the question?'},
        #                      [])
        return '42'

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("Facts serviceStarted emit")

    # cut and paste for now, testing props stuff

    #@slip.dbus.polkit.require_auth(PK_DEFAULT_ACTION)
    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='s',
                                    out_signature='a{sv}')
    @decorators.dbus_handle_exceptions
    def GetAll(self, interface_name, sender=None):
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
        log.debug("Get Property ifact=%s property_name=%s", interface_name, property_name)
        return self.props.get(interface=interface_name,
                              prop=property_name)

    @decorators.dbus_service_method(dbus.PROPERTIES_IFACE,
                                    in_signature='ssv')
    @decorators.dbus_handle_exceptions
    def Set(self, interface_name, property_name, new_value, sender=None):
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

#def run():
#
#    base_service.run_service(dbus.SystemBus,
#                             FACTS_DBUS_BUS_NAME,
#                             FACTS_DBUS_INTERFACE,
#                             FACTS_DBUS_PATH,
#                             Facts)
