
import decorator
import logging

import dbus
import dbus.exceptions

log = logging.getLogger("rhsm_dbus.facts_service." + __name__)

# TODO: mv to shared config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"


# From system-config-firewall
class SubscriptionFactsDBusException(dbus.DBusException):
    _dbus_error_name = "%s.Exception" % FACTS_DBUS_INTERFACE


@decorator.decorator
def dbus_handle_exceptions(func, *args, **kwargs):
    """Decorator to handle exceptions, log and report them into D-Bus

    :Raises DBusException: on a firewall error code problems.
    """
    try:
        return func(*args, **kwargs)
#    except FirewallError as error:
#        log.error(str(error))
#        raise FirewallDBusException(str(error))
    except dbus.DBusException as e:
        # only log DBusExceptions once
        raise e
    except Exception as e:
        log.exception()
        raise SubscriptionFactsDBusException(str(e))


def dbus_service_method(*args, **kwargs):
    #kwargs.setdefault("sender_keyword", "sender")
    return dbus.service.method(*args, **kwargs)
