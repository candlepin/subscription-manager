#!/usr/bin/python

import logging

log = logging.getLogger(__name__)

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
#import slip.dbus.service

from rhsm.dbus.common import decorators
from rhsm.dbus.services import base_service
from rhsm.dbus.services import base_properties

from rhsm.facts import hwprobe

# TODO: move these to a config/constants module
FACTS_DBUS_BUS_NAME = "com.redhat.Subscriptions1.Facts.User"
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts/User"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.User.collect"


class Facts(base_service.BaseService):

    default_polkit_auth_required = None
    persistent = True
    default_props_data = {'version': '-infinity+37',
                          'answer': '42',
                          'last_update': 'before now, probably'}
    facts_collector_class = hwprobe.Hardware

    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)
        self._interface_name = FACTS_DBUS_INTERFACE
        self.facts_collector = self.facts_collector_class()
        self._props = base_properties.BaseProperties(self._interface_name,
                                                     data=self.default_props_data,
                                                     prop_changed_callback=self.PropertiesChanged)

#    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='a{ss}')
    @decorators.dbus_handle_exceptions
    def GetFacts(self, sender=None):
        facts_dict = self.facts_collector.get_all()
        cleaned = dict([(str(key), str(value)) for key, value in facts_dict.items()])
        dbus_dict = dbus.Dictionary(cleaned, signature="ss")
        return dbus_dict

#    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s, int_a, int_b")
        total = int_a + int_b
        return total

#    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        self.props.set(self._interface_name, 'answer', 'What was the question?')

        # FIXME: trigger a props chang signal for testing, this should
        #        become the duty of the properties object
        #self.PropertiesChanged(self._interface_name,
        #                       {'answer': 'What was the question?'},
        #                      [])
        return '42'

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("Facts serviceStarted emit")


def run():
    base_service.run_service(dbus.SystemBus,
                             FACTS_DBUS_BUS_NAME,
                             FACTS_DBUS_INTERFACE,
                             FACTS_DBUS_PATH,
                             Facts)
