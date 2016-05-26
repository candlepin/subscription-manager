import os
import logging
import decorator
import string

import dbus.service
import dbus.exceptions

log = logging.getLogger(__name__)
logger_initialized = False

NAME_BASE = "com.redhat.RHSM"
VERSION = "1"

# The base of the 'well known name' used for bus and service names, as well
# as interface names and object paths.
#
# "com.redhat.RHSM1"
BUS_NAME = NAME_BASE + VERSION

# The default interface name for objects we share on this service.
INTERFACE_BASE = BUS_NAME

# The root of the objectpath tree for our services.
# Note: No trailing '/'
#
# /com/redhat/RHSM1
ROOT_DBUS_PATH = '/' + string.replace(BUS_NAME, '.', '/')

SERVICE_VAR_PATH = os.path.join('var', 'lib', 'rhsm', 'cache')
DBUS_SERVICE_CACHE_PATH = os.path.join(SERVICE_VAR_PATH, 'dbus')

MAIN_INTERFACE = INTERFACE_BASE
MAIN_DBUS_PATH = ROOT_DBUS_PATH

REGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Register')

CONFIG_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Config')
CONFIG_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Config')


def init_root_logger():
    global logger_initialized
    if logger_initialized:
        return
    # Set up root logger for debug purposes
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    logger_initialized = True


class Error(Exception):
    pass


# From system-config-firewall
class Subscriptions1DBusException(dbus.DBusException):
    """Base exceptions."""
    _dbus_error_name = "%s.Exception" % INTERFACE_BASE


@decorator.decorator
def dbus_handle_exceptions(func, *args, **kwargs):
    """Decorator to handle exceptions, log and report them into D-Bus

    :Raises DBusException: on a firewall error code problems.
    """
    try:
        log.debug("about to call %s %s", args, kwargs)
        ret = func(*args, **kwargs)
        return ret
    except dbus.DBusException as e:
        dbus_message = e.get_dbus_message()  # returns unicode
        dbus_name = e.get_dbus_name()
        # only log DBusExceptions once
        log.debug("DbusException caught")
        log.debug("dbus_message=%s", dbus_message)
        log.debug("dbus_name=%s", dbus_name)
        log.debug("msg=%s", e)
        log.exception(e)
        raise
    except Exception as e:
        log.debug("Exception caught")
        log.exception(e)
        raise Subscriptions1DBusException(str(e))


def dbus_service_method(*args, **kwargs):
    kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)
