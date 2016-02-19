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

# Note facts and facts-root provide the same interface on
# different object paths
#FACTS_ROOT_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.Root"
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_ROOT_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/Root"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class BaseFacts(base_service.BaseService):
    _interface_name = FACTS_DBUS_INTERFACE
    facts_collector_class = None

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(BaseFacts, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        if self.facts_collector_class:
            self.facts_collector = self.facts_collector_class()

    def _create_props(self):
        return base_properties.BaseProperties(self._interface_name,
                                              data=self.default_props_data,
                                              properties_changed_callback=self.PropertiesChanged)

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
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        self.log.debug("Return42")
        return '42'


class FactsTest(BaseFacts):
    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = "/com/redhat/Subscriptions1/Facts/Test"
    default_props_data = {'version': '11',
                          'daemon': 'Test',
                          'answer': '2112',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'soon'}


class FactsReadWrite(BaseFacts):
    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    facts_collector_class = None
    default_dbus_path = "/com/redhat/Subscriptions1/Facts/ReadWriteProps"
    default_props_data = {'version': '11',
                          'daemon': 'root',
                          'answer': '42',
                          'changeme': 'I am the default value',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'before now, probably'}

    def _create_props(self):
        return base_properties.ReadWriteProperties(self._interface_name,
                                              data=self.default_props_data,
                                              properties_changed_callback=self.PropertiesChanged)


class FactsRoot(BaseFacts):
    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = FACTS_ROOT_DBUS_PATH
    default_props_data = {'version': '11',
                          'daemon': 'root',
                          'answer': '42',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'before now, probably'}

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(FactsRoot, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        self.log.debug("FactsRoot even object_path=%s", object_path)
        self.other = FactsTest(conn=conn, object_path=object_path, bus_name=bus_name)
        self.read_write = FactsReadWrite(conn=conn, object_path=object_path, bus_name=bus_name)

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total


def run():
    base_service.service_classes.append(base_service.BaseService)
    base_service.service_classes.append(FactsRoot)
    base_service.service_classes.append(server.FactsUser)
    base_service.run()
    #base_service.run_service(dbus.SystemBus,
    #                         FACTS_ROOT_DBUS_BUS_NAME,
    #                         FACTS_DBUS_INTERFACE,
    #                         FactsRoot)
