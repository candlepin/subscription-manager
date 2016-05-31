
import logging

from rhsmlib.dbus import base_properties
from rhsmlib.dbus.facts import constants
from rhsmlib.dbus.facts import base_facts

log = logging.getLogger(__name__)


class FactsReadWrite(base_facts.BaseFacts):
    persistent = True
    default_dbus_path = constants.FACTS_READ_WRITE_DBUS_PATH
    default_props_data = {
        'version': constants.FACTS_READ_WRITE_VERSION,
        'name': constants.FACTS_READ_WRITE_NAME,
    }

    def _create_props(self):
        return base_properties.ReadWriteProperties(
            self._interface_name,
            data=self.default_props_data,
            properties_changed_callback=self.PropertiesChanged)
