import dbus
import dbus.service
import slip.dbus

from rhsm.dbus.common import decorators
from rhsm.dbus.common import constants
from rhsm.dbus.services import base_service
from rhsm.dbus.services import base_properties

DBUS_NAME = "com.redhat.Subscriptions1.Examples"
DBUS_INTERFACE = "com.redhat.Subscriptions1.Examples"
DBUS_PATH = "/com/redhat/Subscriptions1/Examples"
EXAMPLES_VERSION = "1.0.0"
EXAMPLES_NAME = "Example service."


class Examples(base_service.BaseService):
    _interface_name = DBUS_INTERFACE
    default_polkit_auth_required = constants.PK_ACTION_DEFAULT
    default_dbus_path = DBUS_PATH
    default_props_data = {'version': EXAMPLES_VERSION,
                          'name': EXAMPLES_NAME}

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(Examples, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    def _create_props(self):
        return base_properties.BaseProperties(self._interface_name,
                                              data=self.default_props_data,
                                              properties_changed_callback=self.PropertiesChanged)

    @slip.dbus.polkit.require_auth(constants.PK_ACTION_DEFAULT)
    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                   out_signature='i')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        self.log.debug("Return42")

        the_answer = 42

        self.IntReturnSignal(the_answer)
        return 42

    @slip.dbus.polkit.require_auth(constants.PK_ACTION_DEFAULT)
    @decorators.dbus_service_method(dbus_interface=DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        self.log.debug("AddInts %s %s", int_a, int_b)
        total = int_a + int_b
        return total

    @dbus.service.signal(dbus_interface=DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ExampleSignal(self):
        self.log.debug("ExampleSignal emitted")

    @dbus.service.signal(dbus_interface=DBUS_INTERFACE,
                         signature='i')
    @decorators.dbus_handle_exceptions
    def IntReturnSignal(self, the_int_returned):
        self.log.debug("IntReturnSignal the_int_returned=%s", the_int_returned)
