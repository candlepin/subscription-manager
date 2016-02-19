#!/usr/bin/python

import logging

log = logging.getLogger(__name__)


from rhsm.facts import hwprobe
from rhsm.dbus.services.facts import server

# TODO: move these to a config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_USER_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/User"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class FactsUser(server.BaseFacts):
    default_polkit_auth_required = PK_FACTS_COLLECT
    persistent = True
    default_props_data = {'version': '-infinity+37',
                          'answer': '42',
                          'daemon': 'user',
                          'polkit_auth_action': PK_FACTS_COLLECT,
                          'last_update': 'before now, probably'}
    default_dbus_path = FACTS_USER_DBUS_PATH
    facts_collector_class = hwprobe.Hardware
