import rhsmlib.dbus as common


class ConfigService(object):
    """ Represents the system config """
    @common.dbus_service_method(
        dbus_interface=common.CONFIG_INTERFACE,
        in_signature='',
        out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"
