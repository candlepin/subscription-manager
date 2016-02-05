#!/usr/bin/python

import logging

log = logging.getLogger('rhsm-app.' + __name__)

import dbus
import dbus.service
import dbus.mainloop.glib

import slip.dbus
import slip.dbus.service

from rhsm.dbus.services import decorators
from rhsm.dbus.services import base_service

# TODO: move these to a config/constants module
FACTS_DBUS_INTERFACE = "com.redhat.Subscriptions1.Facts"
FACTS_DBUS_PATH = "/com/redhat/Subscriptions1/Facts"
PK_FACTS_COLLECT = "com.redhat.Subscriptions1.Facts.collect"


class Facts(base_service.BaseService):

    persistent = True
    # FIXME: almost surely this is already available

    def __init__(self, *args, **kwargs):
        super(Facts, self).__init__(*args, **kwargs)
        self._interface_name = FACTS_DBUS_INTERFACE

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                    in_signature='ii',
                                    out_signature='i')
    @decorators.dbus_handle_exceptions
    def AddInts(self, int_a, int_b, sender=None):
        log.debug("AddInts %s %s, int_a, int_b")
        total = int_a + int_b
        return total

    @slip.dbus.polkit.require_auth(PK_FACTS_COLLECT)
    @decorators.dbus_service_method(dbus_interface=FACTS_DBUS_INTERFACE,
                                   out_signature='s')
    @decorators.dbus_handle_exceptions
    def Return42(self, sender=None):
        log.debug("Return42")
        return '42'

    @dbus.service.signal(dbus_interface=FACTS_DBUS_INTERFACE,
                         signature='')
    @decorators.dbus_handle_exceptions
    def ServiceStarted(self):
        log.debug("Facts serviceStarted emit")


def run():
    base_service.run_service(dbus.SystemBus,
                             FACTS_DBUS_INTERFACE,
                             FACTS_DBUS_PATH,
                             Facts)
