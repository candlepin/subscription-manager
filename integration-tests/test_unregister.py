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


import pytest
from utils import loop_until
from constants import RHSM, RHSM_UNREGISTER

import logging
from functools import partial
from dasbus.error import DBusError

logger = logging.getLogger(__name__)

locale = "en_US.UTF-8"

# Tests describe a case when an application unregisters a system.
#
# The API should handle even wrong cases friendly
# - ie. when a system is not registered the API should provide usefull feedback


def test_unregister(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#unregister
    """
    candlepin_config = partial(test_config.get, "candlepin")
    subman.register(
        username=candlepin_config("username"),
        password=candlepin_config("password"),
        org=candlepin_config("org"),
    )
    loop_until(lambda: subman.is_registered)

    proxy = RHSM.get_proxy(RHSM_UNREGISTER, interface_name=RHSM_UNREGISTER)
    response = proxy.Unregister({}, locale)
    assert response is None
    assert not subman.is_registered


def test_unregister_when_system_is_not_registered(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#unregister
    """
    proxy = RHSM.get_proxy(RHSM_UNREGISTER, interface_name=RHSM_UNREGISTER)
    with pytest.raises(DBusError) as excinfo:
        proxy.Unregister({}, locale)

    logger.debug(f"exception from dbus Unregister call: {excinfo}")
    assert "This object requires the consumer to be registered before it can be used." in str(excinfo.value)
    assert not subman.is_registered
