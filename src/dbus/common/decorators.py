
import decorator
import logging

import dbus
import dbus.exceptions

log = logging.getLogger(__name__)

# TODO: mv to shared config/constants module
DBUS_INTERFACE = "com.redhat.Subscriptions1"


# From system-config-firewall
class Subscriptions1DBusException(dbus.DBusException):
    _dbus_error_name = "%s.Exception" % DBUS_INTERFACE


@decorator.decorator
def dbus_handle_exceptions(func, *args, **kwargs):
    """Decorator to handle exceptions, log and report them into D-Bus

    :Raises DBusException: on a firewall error code problems.
    """
    try:
        log.debug("about to call %s %s", args, kwargs)
        ret = func(*args, **kwargs)
        #log.debug("about to return ret=%s", ret)
        return ret
#    except FirewallError as error:
#        log.error(str(error))
#        raise FirewallDBusException(str(error))
    except dbus.DBusException as e:
        dbus_message = e.get_dbus_message()  # returns unicode
        dbus_name = e.get_dbus_name()
        # only log DBusExceptions once
        log.debug("DbusException caught")
        log.debug("dbus_message=%s", dbus_message)
        log.debug("dbus_name=%s", dbus_name)
        log.debug("msg=%s", e)
        log.exception(e)
        raise e
    except Exception as e:
        log.debug("Exception caught")
        log.exception(e)
        raise Subscriptions1DBusException(str(e))


def dbus_service_method(*args, **kwargs):
    kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)
