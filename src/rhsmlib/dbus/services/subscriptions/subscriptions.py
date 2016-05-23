import logging

import dbus
import slip.dbus

import rhsmlib.dbus.common as common

from rhsmlib.dbus.services import base_properties
from rhsmlib.dbus.services import base_service
from rhsmlib.dbus.services.subscriptions import constants

log = logging.getLogger(__name__)


class BaseSubscriptions(base_service.BaseService):
    _interface_name = constants.SUBSCRIPTIONS_DBUS_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(BaseSubscriptions, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    def _create_props(self):
        return base_properties.BaseProperties(self._interface_name,
                                              data=self.default_props_data,
                                              properties_changed_callback=self.PropertiesChanged)

    @slip.dbus.polkit.require_auth(constants.PK_SUBSCRIPTIONS_LIST)
    @common.dbus_service_method(dbus_interface=constants.SUBSCRIPTIONS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @common.dbus_handle_exceptions
    def GetSubscriptions(self, sender=None):
        cleaned = {'Not A Real Subscription': 'Not any useful info about a readl subscription.'}
        dbus_dict = dbus.Dictionary(cleaned, signature="ss")
        return dbus_dict
