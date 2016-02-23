
import logging

from rhsm.facts import hwprobe
from rhsm.dbus.services.facts import constants
from rhsm.dbus.services.facts import base_facts

log = logging.getLogger(__name__)


class FactsHost(base_facts.BaseFacts):
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
    default_props_data = {'version': constants.FACTS_HOST_VERSION,
                          'answer': '42',
                          'name': constants.FACTS_HOST_NAME,
                          'polkit_auth_action': constants.PK_ACTION_FACTS_COLLECT,
                          'last_update': 'before now, probably'}
    default_dbus_path = constants.FACTS_HOST_DBUS_PATH
    facts_collector_class = hwprobe.Hardware
