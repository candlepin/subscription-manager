#!/usr/bin/python

import logging

import slip.dbus

from rhsm.facts import admin_facts

from rhsm.dbus.common import decorators
from rhsm.dbus.services.facts import constants
from rhsm.dbus.services.facts import base_facts

from rhsm.dbus.services.facts import host
from rhsm.dbus.services.facts import user
from rhsm.dbus.services.facts import read_write
from rhsm.dbus.services.facts import example

log = logging.getLogger(__name__)


class FactsRoot(base_facts.BaseFacts):
    default_polkit_auth_required = constants.PK_FACTS_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = constants.FACTS_ROOT_DBUS_PATH
    default_props_data = {'version': constants.FACTS_ROOT_VERSION,
                          'name': constants.FACTS_ROOT_NAME,
                          'answer': '42',
                          'polkit_auth_action': constants.PK_FACTS_COLLECT,
                          'last_update': 'before now, probably'}

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(FactsRoot, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        self.log.debug("FactsRoot even object_path=%s", object_path)
        self.host = host.FactsHost(conn=conn, object_path=object_path, bus_name=bus_name)
        self.example = example.FactsExample(conn=conn, object_path=object_path, bus_name=bus_name)
        self.read_write = read_write.FactsReadWrite(conn=conn, object_path=object_path, bus_name=bus_name)
        self.user = user.FactsUser(conn=conn, object_path=object_path, bus_name=bus_name)

    @slip.dbus.polkit.require_auth(constants.PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=constants.FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        self.log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total
