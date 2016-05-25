import logging
import decorator

import dbus.service
import dbus.exceptions

log = logging.getLogger(__name__)
logger_initialized = False

TOP_LEVEL_DOMAIN = "com"
DOMAIN_NAME = "redhat"
SERVICE_DOMAIN = TOP_LEVEL_DOMAIN + '.' + DOMAIN_NAME
SERVICE_SUB_DOMAIN_BASE = "Subscriptions"
SERVICE_VERSION = "1"

# "Subscriptions1"
SERVICE_SUB_DOMAIN_NAME_VER = SERVICE_SUB_DOMAIN_BASE + SERVICE_VERSION

# The base of the 'well known name' used for bus and service names, as well
# as interface names and object paths.
#
# "com.redhat.Subscriptions1"
SERVICE_NAME = SERVICE_DOMAIN + '.' + SERVICE_SUB_DOMAIN_NAME_VER

# The default interface name for objects we share on this service.
# Also "com.redhat.Subscriptions1"
DBUS_INTERFACE = SERVICE_NAME

# The root of the objectpath tree for our services.
# Note: No trailing '/'
#
# /com/redhat/Subscriptions1
ROOT_DBUS_PATH = '/' + "/".join([TOP_LEVEL_DOMAIN, DOMAIN_NAME, SERVICE_SUB_DOMAIN_NAME_VER])

SUBMAND_PATH = ROOT_DBUS_PATH + '/' + "SubmanDaemon1"

SERVICE_VAR_PATH = '/var/lib/rhsm/cache'

DBUS_SERVICE_CACHE_PATH = SERVICE_VAR_PATH + '/' + 'dbus'

# Default base of policy kit action ids

# com.redhat.Subscriptions1
PK_ACTION_PREFIX = SERVICE_NAME

# com.redhat.Subscriptions1.default
PK_ACTION_DEFAULT = PK_ACTION_PREFIX + '.' + 'default'

# CONFIG
CONFIG_INTERFACE_VERSION = '1'
CONFIG_NAME = "Config" + CONFIG_INTERFACE_VERSION
CONFIG_INTERFACE = '.'.join([SERVICE_NAME,
                             CONFIG_NAME])
CONFIG_DBUS_PATH = ROOT_DBUS_PATH + '/' + CONFIG_NAME

# REGISTER SERVICE
REGISTER_INTERFACE_VERSION = '1'
REGISTER_SERVICE_NAME = "RegisterService" + REGISTER_INTERFACE_VERSION

REGISTER_INTERFACE = '.'.join([SERVICE_NAME,
                               REGISTER_SERVICE_NAME])
REGISTER_DBUS_PATH = ROOT_DBUS_PATH + '/' + REGISTER_SERVICE_NAME

# MAIN SERVICE
MAIN_SERVICE_NAME = "SubmanD"
MAIN_SERVICE_INTERFACE = '.'.join([SERVICE_NAME, MAIN_SERVICE_NAME])


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
    """Base exceptions. com.redhat.Subscriptions1.Exception"""
    _dbus_error_name = "%s.Exception" % DBUS_INTERFACE


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
