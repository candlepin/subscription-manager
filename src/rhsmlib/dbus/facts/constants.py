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
from rhsmlib.dbus import constants

__all__ = [
    'SUB_SERVICE_NAME',
    'FACTS_DBUS_NAME',
    'FACTS_DBUS_INTERFACE',
    'FACTS_DBUS_PATH',
    'FACTS_VERSION',
    'FACTS_NAME',
]

SUB_SERVICE_NAME = "Facts"

# com.redhat.RHSM1.Facts
FACTS_DBUS_NAME = constants.BUS_NAME + '.' + SUB_SERVICE_NAME

# also, com.redhat.RHSM1.Facts
FACTS_DBUS_INTERFACE = constants.BUS_NAME + '.' + SUB_SERVICE_NAME

# /com/redhat/RHSM1/Facts
FACTS_DBUS_PATH = constants.ROOT_DBUS_PATH + '/' + SUB_SERVICE_NAME

FACTS_VERSION = "1.1e1"
FACTS_NAME = "Red Hat Subscription Manager facts."
