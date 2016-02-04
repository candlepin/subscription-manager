
import decorator
import logging

import dbus
import dbus.exceptions

#log = logging.getLogger("rhsm_dbus.facts_service." + __name__)
log = logging.getLogger("rhsm-app." + __name__)

log.debug("decorators import time")

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
        log.debug("about to call %s %s", args, kwargs)
        ret = func(*args, **kwargs)
        log.debug("about to return ret=%s", ret)
        return ret
#    except FirewallError as error:
#        log.error(str(error))
#        raise FirewallDBusException(str(error))
    except dbus.DBusException as e:
        # only log DBusExceptions once
        log.debug("DbusException caught")
        log.exception(e)
        raise e
    except Exception as e:
        log.debug("Exception caught")
        log.exception(e)
        raise SubscriptionFactsDBusException(str(e))


def dbus_service_method(*args, **kwargs):
    kwargs.setdefault("sender_keyword", "sender")
    log.debug("adding sender_keyword to args=%s and kwargs=%s", args, kwargs)
    return dbus.service.method(*args, **kwargs)
