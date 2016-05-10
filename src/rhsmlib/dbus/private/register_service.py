#! /usr/bin/env python
from rhsmlib.dbus.common import gi_kluge
gi_kluge.kluge_it()

from rhsmlib.dbus.common import dbus_utils, constants
from rhsmlib.dbus.services.submand.subman_daemon import SubmanDaemon

from gi.repository import GLib

import dbus.service
import dbus.mainloop.glib
import gettext
from rhsm import connection
from rhsmlib.dbus.common import decorators

import socket
import argparse
import json

import logging
# For testing purposes
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

_ = gettext.gettext

class BaseService(dbus.service.Object):
    default_dbus_path = ""

    def __init__(self, conn=None, bus=None, object_path=default_dbus_path):
        print "Created SubmanDaemon"
        if object_path is None or object_path == "":
            object_path = constants.SUBMAND_PATH
        bus_name = None
        if bus is not None:
            bus_name = dbus.service.BusName(self.__class__.DBUS_NAME, bus)

        super(BaseService, self).__init__(object_path=object_path, conn=conn, bus_name=bus_name)



class ConfigServiceMixin(dbus.service.Object):
    DBUS_NAME = "com.redhat.Subscriptions1.ConfigService"
    DBUS_PATH = "/com/redhat/Subscriptions1/ConfigService"


    @decorators.dbus_service_method(dbus_interface=constants.CONFIG_INTERFACE,
                                    in_signature='',
                                    out_signature='s')
    def getConfig(self, sender=None):
        return "My Cool config"


class ConfigService(BaseService, ConfigServiceMixin):
    pass


class RegisterServiceMixin(dbus.service.Object):
    DBUS_NAME = "com.redhat.Subscriptions1.RegisterService"
    DBUS_PATH = "/com/redhat/Subscriptions1/RegisterService"

    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
                                    out_signature='s',
                                    in_signature='s')
    def reverse(self, text, sender=None):
        text = list(text)
        text.reverse()
        return ''.join(text)

    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
                                    out_signature='o')
    def get_self(self, sender=None):
        return self

    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
                                    in_signature="",
                                    out_signature="")
    def throw_exception(self, sender=None):
        raise Exception('throw_exception')

    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
                                    in_signature="",
                                    out_signature="")
    @decorators.dbus_handle_exceptions
    def throw_exception_2(self, sender=None):
        raise Exception('throw_exception_2')

    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
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
        registration_output = cp.registerConsumer(name=options['name'],
                                                  owner=org)
        print registration_output
        return json.dumps(registration_output)
    @decorators.dbus_service_method(dbus_interface=constants.REGISTER_INTERFACE,
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


class RegisterService(BaseService, RegisterServiceMixin):
    pass


class PrivateRegisterService(BaseService, RegisterServiceMixin, ConfigServiceMixin):
    DBUS_NAME = "com.redhat.Subscriptions1.SubmanDaemon1"
    pass


class SuperSubmanService(SubmanDaemon,
                         RegisterServiceMixin,
                         ConfigServiceMixin):
    pass


if __name__ == '__main__':

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    bus = dbus.SessionBus()
    service = PrivateRegisterService(bus, bus)

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
