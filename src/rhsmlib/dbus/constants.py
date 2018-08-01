from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
__all__ = [
    'NAME_BASE',
    'VERSION',
    'BUS_NAME',
    'INTERFACE_BASE',
    'ROOT_DBUS_PATH',
    'MAIN_INTERFACE',
    'MAIN_DBUS_PATH',
    'REGISTER_INTERFACE',
    'REGISTER_DBUS_PATH',
    'UNREGISTER_INTERFACE',
    'UNREGISTER_DBUS_PATH',
    'CONFIG_INTERFACE',
    'CONFIG_DBUS_PATH',
    'ATTACH_INTERFACE',
    'ATTACH_DBUS_PATH',
    'PRODUCTS_INTERFACE',
    'PRODUCTS_DBUS_PATH',
    'ENTITLEMENT_INTERFACE',
    'ENTITLEMENT_DBUS_PATH',
    'CONSUMER_INTERFACE',
    'CONSUMER_DBUS_PATH',
    'SYSPURPOSE_INTERFACE',
    'SYSPURPOSE_DBUS_PATH',
    'DBUS_PROPERTIES_INTERFACE',
]

# The base of the 'well known name' used for bus and service names, as well
# as interface names and object paths.
#
# "com.redhat.RHSM1"
NAME_BASE = "com.redhat.RHSM"
VERSION = "1"
BUS_NAME = NAME_BASE + VERSION

# The default interface name for objects we share on this service.
INTERFACE_BASE = BUS_NAME

# The root of the objectpath tree for our services.
# Note: No trailing '/'
#
# /com/redhat/RHSM1
ROOT_DBUS_PATH = '/' + str.replace(BUS_NAME, '.', '/')

MAIN_INTERFACE = INTERFACE_BASE
MAIN_DBUS_PATH = ROOT_DBUS_PATH

REGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'RegisterServer')
REGISTER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'RegisterServer')

PRIVATE_REGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Register')
PRIVATE_REGISTER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Register')

UNREGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Unregister')
UNREGISTER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Unregister')

CONFIG_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Config')
CONFIG_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Config')

ATTACH_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Attach')
ATTACH_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Attach')

PRODUCTS_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Products')
PRODUCTS_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Products')

ENTITLEMENT_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Entitlement')
ENTITLEMENT_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Entitlement')

CONSUMER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Consumer')
CONSUMER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Consumer')

SYSPURPOSE_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Syspurpose')
SYSPURPOSE_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Syspurpose')

DBUS_PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'
