#!/usr/bin/python

import logging


from rhsm.facts import admin_facts

from rhsm.dbus.services.facts import constants
from rhsm.dbus.services.facts import base_facts

from rhsm.dbus.services.facts import host

log = logging.getLogger(__name__)


class FactsRoot(base_facts.BaseFacts):
    """Implement the 'root' of the Facts objectpath tree."""
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
    facts_collector_class = admin_facts.AdminFacts
    default_dbus_path = constants.FACTS_ROOT_DBUS_PATH
    default_props_data = {'version': constants.FACTS_ROOT_VERSION,
                          'name': constants.FACTS_ROOT_NAME,
                          'answer': '42',
                          'polkit_auth_action': constants.PK_ACTION_FACTS_COLLECT,
                          'last_update': 'before now, probably'}

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(FactsRoot, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        self.consumers = []
        self.log.debug("FactsRoot even object_path=%s", object_path)
        self.host = host.FactsHost(conn=conn, object_path=object_path, bus_name=bus_name)
