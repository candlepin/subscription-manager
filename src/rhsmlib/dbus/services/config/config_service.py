from rhsmlib.dbus.services.base_service import BaseService
import rhsmlib.dbus as common


class ConfigService(BaseService):
    """ Represents the system config """
    _service_name = common.CONFIG_NAME
    _interface_name = common.CONFIG_INTERFACE
    # TODO: Implement this

    @common.dbus_service_method(dbus_interface=common.CONFIG_INTERFACE,
                                    in_signature='',
                                    out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"
