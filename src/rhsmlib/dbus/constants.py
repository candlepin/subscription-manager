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
import string

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
    'CONFIG_INTERFACE',
    'CONFIG_DBUS_PATH',
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
ROOT_DBUS_PATH = '/' + string.replace(BUS_NAME, '.', '/')

MAIN_INTERFACE = INTERFACE_BASE
MAIN_DBUS_PATH = ROOT_DBUS_PATH

REGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'RegisterServer')
REGISTER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'RegisterServer')

PRIVATE_REGISTER_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Register')
PRIVATE_REGISTER_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Register')

CONFIG_INTERFACE = '%s.%s' % (INTERFACE_BASE, 'Config')
CONFIG_DBUS_PATH = '%s/%s' % (ROOT_DBUS_PATH, 'Config')
