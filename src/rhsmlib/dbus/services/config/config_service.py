from rhsmlib.dbus.services.base_service import BaseService
from rhsmlib.dbus.common import constants, decorators


class ConfigService(BaseService):
    """ Represents the system config """
    _service_name = constants.CONFIG_NAME
    _interface_name = constants.CONFIG_INTERFACE
    # TODO: Implement this


    @decorators.dbus_service_method(dbus_interface=constants.CONFIG_INTERFACE,
                                    in_signature='',
                                    out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"
