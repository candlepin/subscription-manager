# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

#
# Copyright (C) 2011,2012 Red Hat, Inc.
#
# Authors:
# Thomas Woerner <twoerner@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import pwd
import xml.etree.ElementTree as Et

import dbus
import six

PY2 = six.PY2

log = logging.getLogger(__name__)


def command_of_pid(pid):
    """ Get command for pid from /proc """
    try:
        with open("/proc/%d/cmdline" % pid, "r") as f:
            cmd = f.readlines()[0].replace('\0', " ").strip()
    except:
        return None
    return cmd


def pid_of_sender(bus, sender):
    """ Get pid from sender string using
    org.freedesktop.DBus.GetConnectionUnixProcessID """

    dbus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus')

    try:
        pid = int(dbus_iface.GetConnectionUnixProcessID(sender))
    except ValueError:
        return None
    return pid


def uid_of_sender(bus, sender):
    """ Get user id from sender string using
    org.freedesktop.DBus.GetConnectionUnixUser """

    dbus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus')

    try:
        uid = int(dbus_iface.GetConnectionUnixUser(sender))
    except ValueError:
        return None
    return uid


def user_of_uid(uid):
    """ Get user for uid from pwd """

    try:
        pws = pwd.getpwuid(uid)
    except Exception:
        return None
    return pws[0]


def context_of_sender(bus, sender):
    """ Get SELinux context from sender string using
    org.freedesktop.DBus.GetConnectionSELinuxSecurityContext """

    dbus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus')

    try:
        context = dbus_iface.GetConnectionSELinuxSecurityContext(sender)
    except:
        return None

    return "".join(map(chr, dbus_to_python(context)))


def command_of_sender(bus, sender):
    """ Return command of D-Bus sender """

    return command_of_pid(pid_of_sender(bus, sender))


def user_of_sender(bus, sender):
    return user_of_uid(uid_of_sender(bus, sender))


def dbus_to_python(obj, expected_type=None):
    if obj is None:
        python_obj = obj
    elif isinstance(obj, dbus.Boolean):
        python_obj = bool(obj)
    elif isinstance(obj, dbus.String):
        python_obj = obj.encode('utf-8') if PY2 else str(obj)
    elif PY2 and isinstance(obj, dbus.UTF8String):  # Python3 has no UTF8String
        python_obj = str(obj)
    elif isinstance(obj, dbus.ObjectPath):
        python_obj = str(obj)
    elif isinstance(obj, dbus.Byte) or \
            isinstance(obj, dbus.Int16) or \
            isinstance(obj, dbus.Int32) or \
            isinstance(obj, dbus.Int64) or \
            isinstance(obj, dbus.UInt16) or \
            isinstance(obj, dbus.UInt32) or \
            isinstance(obj, dbus.UInt64):
        python_obj = int(obj)
    elif isinstance(obj, dbus.Double):
        python_obj = float(obj)
    elif isinstance(obj, dbus.Array):
        python_obj = [dbus_to_python(x) for x in obj]
    elif isinstance(obj, dbus.Struct):
        python_obj = tuple([dbus_to_python(x) for x in obj])
    elif isinstance(obj, dbus.Dictionary):
        #python_obj = {dbus_to_python(k): dbus_to_python(v) for k, v in obj.items()}
        python_obj = dict([dbus_to_python(k), dbus_to_python(v)] for k, v in list(obj.items()))
    elif isinstance(obj, bool) or \
         isinstance(obj, str) or isinstance(obj, bytes) or \
         isinstance(obj, int) or isinstance(obj, float) or \
         isinstance(obj, list) or isinstance(obj, tuple) or \
         isinstance(obj, dict):
        python_obj = obj
    else:
        raise TypeError("Unhandled %s" % obj)

    if expected_type is not None:
        if (expected_type == bool and not isinstance(python_obj, bool)) or \
           (expected_type == str and not isinstance(python_obj, str)) or \
           (expected_type == int and not isinstance(python_obj, int)) or \
           (expected_type == float and not isinstance(python_obj, float)) or \
           (expected_type == list and not isinstance(python_obj, list)) or \
           (expected_type == tuple and not isinstance(python_obj, tuple)) or \
           (expected_type == dict and not isinstance(python_obj, dict)):
            raise TypeError("%s is %s, expected %s" % (python_obj, type(python_obj), expected_type))

    return python_obj


# From lvm-dubstep/lvmdbus/utils.py  (GPLv2, copyright Red Hat)
# https://github.com/tasleson/lvm-dubstep
_type_map = dict(
    s=dbus.String,
    o=dbus.ObjectPath,
    t=dbus.UInt64,
    x=dbus.Int64,
    u=dbus.UInt32,
    i=dbus.Int32,
    n=dbus.Int16,
    q=dbus.UInt16,
    d=dbus.Double,
    y=dbus.Byte,
    b=dbus.Boolean)


def _pass_through(v):
    """
    If we have something which is not a simple type we return the original
    value un-wrapped.
    :param v:
    :return:"""
    return v


def _dbus_type(t, value):
    return _type_map.get(t, _pass_through)(value)


def add_properties(xml, interface, props):
    """
    Given xml that describes the interface, add property values to the XML
    for the specified interface.
    :param xml:         XML to edit
    :param interface:   Interface to add the properties too
    :param props:       Output from get_properties
    :return: updated XML string
    """
    root = Et.fromstring(xml)

    if props:

        for c in root:
            # print c.attrib['name']
            if c.attrib['name'] == interface:
                for p in props:
                    temp = '<property type="%s" name="%s" access="%s"/>\n' % \
                        (p['p_t'], p['p_name'], p['p_access'])
                    log.debug("intro xml temp buf=%s", temp)
                    c.append(Et.fromstring(temp))

        return Et.tostring(root, encoding='utf8')
    return xml


def dict_to_variant_dict(in_dict):
    # Handle creating dbus.Dictionaries with signatures of 'sv'
    for key, value in six.iteritems(in_dict):
        if isinstance(value, dict):
            in_dict[key] = dict_to_variant_dict(value)
    return dbus.Dictionary(in_dict, signature="sv")
