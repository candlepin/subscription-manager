

import logging

from rhsmlib.facts import virt
from rhsmlib.dbus.services.facts import constants
from rhsmlib.dbus.services.facts import base_facts

log = logging.getLogger(__name__)


class FactsExample(base_facts.BaseFacts):
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
    facts_collector_class = virt.VirtCollector
    default_dbus_path = constants.FACTS_EXAMPLE_DBUS_PATH
    default_props_data = {'version': constants.FACTS_EXAMPLE_VERSION,
                          'answer': '2112',
                          'name': constants.FACTS_EXAMPLE_NAME,
                          'polkit_auth_action': constants.PK_ACTION_FACTS_COLLECT,
                          'last_update': 'soon'}
