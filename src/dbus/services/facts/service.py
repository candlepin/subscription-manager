#!/usr/bin/python

import logging

log = logging.getLogger(__name__)


import slip.dbus
import slip.dbus.service

from rhsm.facts import admin_facts

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_properties
from rhsm.dbus.services.facts import base_facts_service
from rhsm.dbus.services.facts_user import service

# Note facts and facts-root provide the same interface on
# different object paths
#FACTS_ROOT_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.Root"
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_ROOT_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/Root"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class FactsTest(base_facts_service.BaseFacts):
    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = "/com/redhat/Subscriptions1/Facts/Test"
    default_props_data = {'version': '11',
                          'daemon': 'Test',
                          'answer': '2112',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'soon'}


class FactsReadWrite(base_facts_service.BaseFacts):
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


class FactsRoot(base_facts_service.BaseFacts):
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
        self.user = service.FactsUser(conn=conn, object_path=object_path, bus_name=bus_name)

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total
