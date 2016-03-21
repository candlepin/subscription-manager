#!/usr/bin/python

import logging

from rhsmlib.dbus.services.facts import constants
from rhsmlib.dbus.services.facts import base_facts

from rhsmlib.dbus.services.facts import host

log = logging.getLogger(__name__)


class FactsRoot(base_facts.BaseFacts):
    """Implement the 'root' of the Facts objectpath tree."""
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
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

        # We could potentially aggregate facts up to here, or provide dynamic/meta
        # facts  (fact collector types and versions, fact count, timestamps, any/all()
        # functions facts like virt.is_guest, etc).
        #
        # But for now, FactsRoot has no facts of it's own.

        # In this object path, Facts/Machine is equilivent to 'subscription-manager facts --list'. Ie, the facts associated with the local running system image. 'Machine'
        # moniker is based on similar conventions in NetworkManager and systemd dbus
        # services. At some point, there could be other 'hosts' here (systemd
        # managed containers and vm guests perhaps).

        self.machine = host.FactsHost(conn=conn, object_path=object_path, bus_name=bus_name)
