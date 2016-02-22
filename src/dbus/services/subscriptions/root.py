import logging

import slip.dbus

from rhsm.dbus.common import decorators

# FIXME: relative imports
from rhsm.dbus.services import base_service
from rhsm.dbus.services.subscriptions import constants

log = logging.getLogger(__name__)


class SubscriptionsRoot(base_service.BaseService):
    default_polkit_auth_required = constants.PK_SUBSCRIPTIONS_DEFAULT
    persistent = True
    default_dbus_path = constants.SUBSCRIPTIONS_ROOT_DBUS_PATH
    default_props_data = {'version': constants.SUBSCRIPTIONS_ROOT_VERSION,
                          'name': constants.SUBSCRIPTIONS_ROOT_NAME,
                          'answer': '42?',
                          'polkit_auth_action': constants.PK_SUBSCRIPTIONS_DEFAULT,
                          'last_update': 'just now. No, now!'}

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(SubscriptionsRoot, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

        self.log.debug("SubscriptionsRoot even object_path=%s", object_path)

    @slip.dbus.polkit.require_auth(constants.PK_SUBSCRIPTIONS_DEFAULT)
    @decorators.dbus_service_method(dbus_interface=constants.SUBSCRIPTIONS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        self.log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total
