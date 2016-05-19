import dbus.service

from rhsmlib.dbus.common import constants


class PrivateService(dbus.service.Object):
    """ The base class for service objects to be exposed on either a private connection
        or a bus."""
    _interface_name = None
    _default_dbus_path = constants.ROOT_DBUS_PATH
    _default_dbus_path += ("/" + _interface_name) if _interface_name else ""
    _default_bus_name = constants.SERVICE_NAME

    def __init__(self, conn=None, bus=None, object_path=None):
        if object_path is None or object_path == "":
            # If not given a path to be exposed on, use class defaults
            _interface_name = self.__class__._interface_name
            object_path = self.__class__._default_dbus_path + \
                ("/" + _interface_name) if _interface_name else ""

        bus_name = None
        if bus is not None:
            # If we are passed in a bus, try to claim an appropriate bus name
            bus_name = dbus.service.BusName(self.__class__._default_bus_name, bus)

        super(PrivateService, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)
