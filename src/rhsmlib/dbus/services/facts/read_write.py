
import logging

from rhsmlib.dbus.services import base_properties
from rhsmlib.dbus.services.facts import constants
from rhsmlib.dbus.services.facts import base_facts

log = logging.getLogger(__name__)


class FactsReadWrite(base_facts.BaseFacts):
    default_polkit_auth_required = constants.PK_ACTION_FACTS_COLLECT
    persistent = True
    default_dbus_path = constants.FACTS_READ_WRITE_DBUS_PATH
    default_props_data = {'version': constants.FACTS_READ_WRITE_VERSION,
                          'answer': '42',
                          'name': constants.FACTS_READ_WRITE_NAME,
                          'changeme': 'I am the default value',
                          'polkit_auth_action': constants.PK_ACTION_FACTS_COLLECT,
                          'last_update': 'before now, probably'}

    def _create_props(self):
        return base_properties.ReadWriteProperties(self._interface_name,
                                                   data=self.default_props_data,
                                                   properties_changed_callback=self.PropertiesChanged)
