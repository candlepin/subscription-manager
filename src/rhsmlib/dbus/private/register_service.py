#! /usr/bin/env python
from rhsmlib.dbus.common import gi_kluge
gi_kluge.kluge_it()

from rhsmlib.dbus.common import dbus_utils, constants

from gi.repository import GLib

import dbus.service
import dbus.mainloop.glib
import gettext
from rhsm import connection
from rhsmlib.dbus.common import decorators

import socket
import argparse

import logging
# For testing purposes
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

_ = gettext.gettext


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
            bus_name = dbus.service.BusName(DBUS_NAME, bus)
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
                return self.services[service_name]
            else:
                raise decorators.Subscriptions1DBusException("No instance available")
        return service

    def _find_service_class_for_name(self, service_name):
        logger.debug('Finding class that matches service name "%s"', service_name)
        for service in self.service_classes:
            logger.debug(service_name)
            if service.DBUS_NAME == service_name:
                logger.debug("Made it")
                return service
        raise decorators.Subscriptions1DBusException('No class found that matches "%s"', service_name)

    def _create_service_instance(self, service_name):
        logger.debug('Attempting to create instance of service_name: "%s"', service_name)
        clazz = self._find_service_class_for_name(service_name)
        return clazz(conn=self.conn, bus=self.bus)


class ConfigService(dbus.service.Object):
    DBUS_NAME = "com.redhat.Subscriptions1.ConfigService"
    DBUS_INTERFACE = "com.redhat.Subscriptions1.ConfigService"
    DBUS_PATH = "/com/redhat/Subscriptions1/ConfigService"

    def __init__(self, conn=None, bus=None, object_path=DBUS_PATH):
        print "Created ConfigService"
        self.name = self.__class__.DBUS_NAME
        bus_name = None
        if bus is not None:
            bus_name = dbus.service.BusName(DBUS_NAME, bus)
        super(ConfigService, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature='',
                                    out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"


class RegisterService(dbus.service.Object):
    DBUS_NAME = "com.redhat.Subscriptions1.RegisterService"
    DBUS_INTERFACE = "com.redhat.Subscriptions1.RegisterService"
    DBUS_PATH = "/com/redhat/Subscriptions1/RegisterService"

    def __init__(self, conn=None, bus=None, object_path=DBUS_PATH):
        print "Created RegisterService"
        self.name = self.__class__.DBUS_NAME
        bus_name = None
        if bus is not None:
            bus_name = dbus.service.BusName(DBUS_NAME, bus)
        super(RegisterService, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    out_signature='s',
                                    in_signature='s')
    def reverse(self, text, sender=None):
        text = list(text)
        text.reverse()
        return ''.join(text)

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    out_signature='o')
    def get_self(self, sender=None):
        return self

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature="",
                                    out_signature="")
    def throw_exception(self, sender=None):
        raise Exception('throw_exception')

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature="",
                                    out_signature="")
    @decorators.dbus_handle_exceptions
    def throw_exception_2(self, sender=None):
        raise Exception('throw_exception_2')

    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature='sssa{ss}',
                                    out_signature='s')
    def register(self, username, password, org, options, sender=None):
        """
        This method registers the system using basic auth
        (username and password for a given org).
        For any option that is required but not included the default will be
        used.

        Options is a dict of strings that modify the outcome of this method.
        """
        validation_result = RegisterService._validate_register_options(options)
        if validation_result:
            return validation_result
        # We have to convert dictionaries from the dbus objects to their
        # python equivalents. Seems like the dbus dictionaries don't work
        # in quite the same way as regular python ones.
        options = dbus_utils.dbus_to_python(options)

        if options.get('name') is None:
            options['name'] = socket.gethostname()
        cp = connection.UEPConnection(username=username,
                                      password=password,
                                      host=options['host'],
                                      ssl_port=connection.safe_int(options['port']),
                                      handler=options['handler'])
        logger.info(cp.registerConsumer(name=options['name'],
                                   owner=org))
        return "haha"
    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature='sa(s)a{ss}',
                                    out_signature='s')
    def register_with_activation_keys(self,
                                      org,
                                      activation_keys,
                                      options, sender=None):
        """ This method registers a system with the given options, using
        an activation key.
        """
        return "WITH ACTIVATION KEYS"


    @staticmethod
    def is_registered():
        #TODO: Implement this
        return False

    @staticmethod
    def _validate_register_options(options):
        # From managercli.RegisterCommand._validate_options
        autoattach = options.get('autosubscribe') or options.get('autoattach')
        if RegisterService.is_registered() and not options.get('force'):
            return _("This system is already registered. Use --force to override")
        elif (options.get('consumername') == ''):
            return _("Error: system name can not be empty.")
        elif (options.get('username') and options.get('activation_keys')):
            return _("Error: Activation keys do not require user credentials.")
        elif (options.get('consumerid') and options.get('activation_keys')):
            return _("Error: Activation keys can not be used with previously registered IDs.")
        elif (options.get('environment') and options.get('activation_keys')):
            return _("Error: Activation keys do not allow environments to be specified.")
        elif (autoattach and options.get('activation_keys')):
            return _("Error: Activation keys cannot be used with --auto-attach.")
        # 746259: Don't allow the user to pass in an empty string as an activation key
        elif (options.get('activation_keys') and '' in options.get('activation_keys')):
            return _("Error: Must specify an activation key")
        elif (options.get('service_level') and not autoattach):
            return _("Error: Must use --auto-attach with --servicelevel.")
        elif (options.get('activation_keys') and not options.get('org')):
            return _("Error: Must provide --org with activation keys.")
        elif (options.get('force') and options.get('consumerid')):
            return _("Error: Can not force registration while attempting to recover registration with consumerid. Please use --force without --consumerid to re-register or use the clean command and try again without --force.")
        return None


class PrivateRegisterService(SubmanDaemon):
    _default_service_classes = [ConfigService, RegisterService]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Start the registration service")
    parser.add_argument('--private', action="store_true", default=False,
                        help="Start the service on private socket",
                        dest="private")
    args = parser.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    bus = dbus.SessionBus(private=args.private)
    service = RegisterService(bus) if args.private else RegisterService(bus, bus)

    try:
        mainloop.run()
    except KeyboardInterrupt as e:
        print(e)
    except SystemExit as e:
        print(e)
    except Exception as e:
        print(e)
    finally:
        mainloop.quit()
