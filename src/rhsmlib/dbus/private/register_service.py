#! /usr/bin/env python

from rhsmlib.dbus.common import dbus_utils, constants

import dbus.service
import gettext

from rhsm import connection

from rhsmlib.dbus.common import decorators

from rhsmlib.dbus.private.private_service import PrivateService

import socket
import argparse
import json

_ = gettext.gettext


class RegisterService(PrivateService):
    _interface_name = constants.REGISTER_SERVICE_NAME

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
        # TODO: Read from config if needed
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

        # For now return the json from the server as a string
        # TODO: Create standard return signature
        # NOTE: dbus python does not know what to do with the python NoneType
        # Otherwise we could just have our return signature be a dict of strings to variant
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
        # TODO: Implement
        # NOTE: We could probably manage doing this in one method with the use
        #       of variants in the in_signature (but I'd imagine that might be
        #       slightly more difficult to unit test)
        return "WITH ACTIVATION KEYS"


    @staticmethod
    def is_registered():
        # TODO: Implement this
        # NOTE: Likely needs some form of injection as in managercli
        return False

    @staticmethod
    def _validate_register_options(options):
        # TODO: Rewrite the error messages to be more dbus specific
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

if __name__ == '__main__':

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()

    mainloop = GLib.MainLoop()
    bus = dbus.SessionBus()
    service = RegisterService(bus, bus)

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
