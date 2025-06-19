# Copyright (c) 2024 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

from constants import RHSM, RHSM_CONSUMER
from funcy import partial
from utils import loop_until

import logging

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Consumer Object.

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#consumer
for more details.

Main usecases are presented in this file.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"


def test_getUUID_when_system_is_registered(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Consumer.GetUuid

    - The method returns uuid string in case a system is registered
    - the uuid is the same as a command 'subscription-manager identity' provides
    """
    candlepin_config = partial(test_config.get, "candlepin")
    subman.register(
        username=candlepin_config("username"),
        password=candlepin_config("password"),
        org=candlepin_config("org"),
    )
    loop_until(lambda: subman.is_registered)
    proxy = RHSM.get_proxy(RHSM_CONSUMER)
    uuid_from_dbus = proxy.GetUuid(locale)
    uuid_from_subman = subman.uuid
    assert uuid_from_dbus == str(uuid_from_subman)
    assert subman.is_registered


def test_getUUID_when_system_is_unregistered(any_candlepin):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Consumer.GetUuid

    - The method returns empty string in case a system is unregistered
    """
    proxy = RHSM.get_proxy(RHSM_CONSUMER)
    uuid_from_dbus = proxy.GetUuid(locale)
    assert str(uuid_from_dbus) == ""
