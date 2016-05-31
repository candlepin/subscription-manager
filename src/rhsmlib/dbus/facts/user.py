
import logging

from rhsmlib.facts import hwprobe
from rhsmlib.dbus.facts import constants
from rhsmlib.dbus.facts import base_facts

log = logging.getLogger(__name__)


class FactsUser(base_facts.BaseFacts):
    persistent = True
    default_props_data = {
        'version': constants.FACTS_USER_VERSION,
        'name': constants.FACTS_USER_NAME,
    }
    default_dbus_path = constants.FACTS_USER_DBUS_PATH
    facts_collector_class = hwprobe.Hardware
