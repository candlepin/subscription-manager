from rhsmlib.dbus.common import decorators, dbus_utils

import dbus.service

import logging
# For testing purposes
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

class SubmanDaemon(dbus.service.Object):
    """ Subscription-managerD main class """
    DBUS_NAME = "com.redhat.Subscriptions1.SubmanDaemon1"
    DBUS_INTERFACE = "com.redhat.Subscriptions1.SubmanDaemon1"
    DBUS_PATH = "/com/redhat/Subscriptions1/SubmanDaemon1"
    _default_service_classes = []

    def __init__(self, conn=None, bus=None, object_path=DBUS_PATH, service_classes=None):
        print "Created SubmanDaemon"
        bus_name = None
        if bus is not None:
            bus_name = dbus.service.BusName(self.__class__.DBUS_NAME, bus)
        self.bus = bus
        self.conn = conn
        self.object_path = object_path

        self.service_classes = service_classes or self.__class__._default_service_classes
        self.services = {}
        super(SubmanDaemon, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature="s",
                                    out_signature="o")
    def get_service_by_name(self, service_name, sender=None):
        """ Returns the object path to a given service """
        service_name = dbus_utils.dbus_to_python(service_name, str)
        service_instance = self._get_service_by_name(service_name, create=True)
        return service_instance

    def _get_service_by_name(self, service_name, create=False):
        """ Returns an instance of an object """
        service = self.services.get(service_name)
        if service is None:
            # We don't have an object created for this name
            logger.debug('No instance of service name "%s" available', service_name)
            if create:
                self.services[service_name] = self._create_service_instance(service_name)
                service = self.services[service_name]
            else:
                raise decorators.Subscriptions1DBusException("No instance available")
        return service

    def _find_service_class_for_name(self, service_name):
        """ Finds the first class that has a DBUS_NAME that matches the
            requisite name """
        logger.debug('Finding class that matches service name "%s"', service_name)
        for service in self.service_classes:
            logger.debug(service_name)
            if service.DBUS_NAME == service_name:
                return service
        raise decorators.Subscriptions1DBusException('No class found that matches "%s"', service_name)

    def _create_service_instance(self, service_name):
        """ Creates an instance of the service_name if one can be found"""
        logger.debug('Attempting to create instance of service_name: "%s"', service_name)
        clazz = self._find_service_class_for_name(service_name)
        return clazz(conn=self.conn, bus=self.bus)
