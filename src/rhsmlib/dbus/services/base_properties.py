import logging

import dbus

from rhsmlib.dbus.common import dbus_utils

log = logging.getLogger(__name__)


class Property(object):
    default_access = 'read'
    default_value_signature = 's'

    def __init__(self, name, value, value_signature=None, access=None):
        self.access = access or self.default_access
        self.name = name
        self.value = value
        self.value_signature = value_signature or self.default_value_signature


# TODO: Make properties class a gobject, so we can reused it's prop handling
#       (And maybe python-dbus can do something useful with a Gobject?
class BaseProperties(object):
    def __init__(self, interface_name,
                 data=None,
                 properties_changed_callback=None):
        self.log = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        # dict of  of prop_name:a_Property_object
        self.props_data = data
        self.interface_name = interface_name
        self.properties_changed_callback = properties_changed_callback

    @classmethod
    def from_string_to_string_dict(cls, interface_name, prop_dict, properties_changed_callback=None):
        base_prop = cls(interface_name,
                        properties_changed_callback=properties_changed_callback)
        props = {}
        for prop_key, prop_value in prop_dict.items():
            prop = Property(name=prop_key, value=prop_value)
            props[prop.name] = prop

        base_prop.props_data = props
        return base_prop

    def get(self, interface_name=None, property_name=None):
        self._check_interface(interface_name)
        self._check_prop(property_name)

        try:
            return self.props_data[property_name].value
        except KeyError as e:
            self.log.exception(e)
            self.raise_access_denied_or_unknown_property(property_name)

    def get_all(self, interface_name=None):
        self._check_interface(interface_name)

        # For now at least, likely need to filter.
        # Or perhaps a self.props_data.to_dbus() etc.
        a = dict([(p_name, p_v.value) for p_name, p_v in self.props_data.items()])
        log.debug('a=%s', a)
        return a

    def set(self, interface_name, property_name, new_value):
        """On attempts to set a property, raise AccessDenied.

        The default base_properties is read-only. Attempts to set()
        a property will raise a DBusException of type
        org.freedesktop.DBus.Error.AccessDenied.

        Subclasses that need settable properties should override this.
        BaseService subclasses that need rw properties should use
        a ReadWriteBaseProperties instead of BaseProperties."""

        self.raise_access_denied(property_name)

    def _set(self, interface_name, property_name, new_value):
        """Set a property to given value, ignoring access writes.

        Ie, BaseProperties.set() can be exposed through the dbus.Properties 'Set()'
        method, where it will check access rights. But internal use can use _set."""
        props = [(property_name, new_value)]
        self._set_props(interface_name, props)

    def _set_props(self, interface_name, properties_iterable):
        interface_name = dbus_utils.dbus_to_python(interface_name, str)

        self._check_interface(interface_name)

        for property_name, new_value in properties_iterable:
            self._set_prop(interface_name, property_name, new_value)

        self._emit_properties_changed(properties_iterable)

    def _set_prop(self, interface_name, property_name, new_value):
        property_name = dbus_utils.dbus_to_python(property_name, str)
        new_value = dbus_utils.dbus_to_python(new_value)

        self._check_prop(property_name)

        # FIXME/TODO: Plug in access checks and data validation
        # FIXME/TODO: Plug in checking if prop should emit a change signal.
        try:
            self.props_data[property_name].value = new_value
            # WARNING: if emitting a signal causes an exception...?
        except Exception as e:
            self.log.debug("ReadWriteProperties Exception i=%s p=%s n=%s",
                           interface_name, property_name, new_value)
            self.log.exception(e)
            self._error_on_set(e, property_name, new_value)

    # FIXME: This is kind of weird. Would be easier if we track the DBus
    #        signature for each property.
    def add_introspection_xml(self, interface_xml):
        ret = dbus_utils.add_properties(interface_xml, self.interface_name,
                                        self.to_introspection_props())
        return ret

    # FIXME: This only supports string type values at the moment.
    def to_introspection_props(self):
        """ Transform self.props_data (a dict) to:

        data = {'blah': '1', 'blip': some_int_value}
        props_tup = ({'p_t': 's',
                      'p_name': 'blah',
                      'p_access': 'read' },
                      {'p_t': 'i',
                      'p_name': blip,
                      'p_access': 'read'}))
        """
        props_list = []
        props_dict = {}
        for prop_info in self.props_data.values():
            #p_t = dbus_utils._type_map(type(prop_value))
            # FIXME: all strings atm
            # self.log.debug("prop_info=%s", prop_info)
            props_dict = dict(p_t=prop_info.value_signature,
                              p_name=prop_info.name,
                              p_access=self.access_mask(prop_info.access))
            props_list.append(props_dict)

        # self.log.debug("t_i_p=%s", props_list)
        return props_list

    # FIXME: THis is a read only props class, ReadWriteProperties needs
    #        to be smarter
    def access_mask(self, prop_key):
        return 'read'

    def _check_interface(self, interface_name):
        if interface_name != self.interface_name:
            self.raise_unknown_interface(interface_name)

        if interface_name == '':
            self._get_all_empty()
        # Unset None/'' interface is default

    def _get_all_empty(self):
        """On a request for props for interface '', do what makes sense.

        Default is to raise UnknownInterace for ''.

        If subclasses overrides so this doesn't raise an exception,
        the default behavior is for get_all() to return self.props_data"""
        self.raise_unknown_interface('')

    def _check_prop(self, property_name):
        if property_name not in self.props_data:
            # if not any([prop for prop in self.props_data if prop.name == property_name]):
            self.raise_property_does_not_exist(property_name)

    # FIXME: likely a more idiomatic way to do this.
    def _emit_properties_changed(self, properties_iterable):
        if not self.properties_changed_callback:
            return

        changed_properties = {}
        invalidated_properties = []

        for property_name, new_value in properties_iterable:
            changed_properties[property_name] = new_value

        self.properties_changed_callback(self.interface_name,
                                         changed_properties,
                                         invalidated_properties)

    def _error_on_set(self, exception, prop, value):
        self.log.debug("Exception on Properties.Set prop=%s value=%s", prop, value)
        self.log.exception(exception)
        msg = "Error setting property %s=%s on interface_name=%s: %s" % \
            (prop, value, self.interface_name, exception)
        self.log.debug('msg=%s', msg)
        raise dbus.exceptions.DBusException(msg)

    def raise_access_denied(self, property_name):
        self.log.debug('rae')
        # The base service assumes that properties are read only.
        raise dbus.exceptions.DBusException(
            "org.freedesktop.DBus.Error.AccessDenied: "
            "Property '%s' is not settable" % property_name)

    def raise_property_does_not_exist(self, property_name):
        self.log.debug('rpdne')
        msg = "org.freedesktop.DBus.Error.AccessDenied: " \
        "Property '%s' does not exist" % property_name
        raise dbus.exceptions.DBusException(msg)

    def raise_unknown_interface(self, interface_name):
        self.log.debug('rui')
        msg = "org.freedesktop.DBus.Error.UnknownInterface: " \
        "%s does not handle properties for %s" % (self.interface_name, interface_name)
        raise dbus.exceptions.DBusException(msg)

    def raise_access_denied_or_unknown_property(self, property_name):
        self.log.debug('radoup')
        msg = "org.freedesktop.DBus.Error.AccessDenied: " \
        "Property '%s' isn't exported (or may not exist) on interface: %s" % \
            (property_name, self.interface_name)

        raise dbus.exceptions.DBusException(msg)


class ReadWriteProperties(BaseProperties):
    """A read-write BaseProperties.

    Use this if you want to be able to set()/Set() DBus.Properties
    on a service."""

    def set(self, interface_name, property_name, new_value):
        if self.access_mask(property_name) != 'write':
            self.raise_access_denied(property_name)

        return self._set(interface_name, property_name, new_value)

    # FIXME: track read/write per property
    def access_mask(self, prop_key):
        return 'write'
