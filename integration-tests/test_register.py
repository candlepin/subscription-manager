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
import json
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str
from funcy import partial

import logging

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Register Object.

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#register
for more details.

Main usecases are presented in this file.

Special usecases for registering (with proxy, activation keys, ...) are presented
in its own files.

It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"


def test_register(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.Register(
            "",
            test_config.get("candlepin", "username"),
            test_config.get("candlepin", "password"),
            {},
            {},
            locale,
        )
        response_data = json.loads(response)
        assert "idCert" in response_data, "A response contains of consumer certificate"
        assert frozenset(["key", "cert", "updated", "created", "id", "serial"]).issubset(
            frozenset(response_data["idCert"].keys())
        )

    assert subman.is_registered


def test_register_with_org(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        private_proxy.Register(
            test_config.get("candlepin", "org"),
            test_config.get("candlepin", "username"),
            test_config.get("candlepin", "password"),
            {},
            {},
            locale,
        )
    assert subman.is_registered


@pytest.mark.parametrize("enable_content", ["true", "false"])
def test_register_with_enable_content(external_candlepin, subman, test_config, enable_content):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        private_proxy.Register(
            test_config.get("candlepin", "org"),
            test_config.get("candlepin", "username"),
            test_config.get("candlepin", "password"),
            {"enable_content": get_variant(Str, enable_content)},
            {},
            locale,
        )
    assert subman.is_registered


@pytest.mark.parametrize(
    "credentials",
    [("wrong username", None, None), (None, "wrong password", None), (None, None, "wrong organization")],
)
def test_register_with_wrong_values(external_candlepin, subman, test_config, credentials):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered

    candlepin_config = partial(test_config.get, "candlepin")

    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)

        wrong_org = "wrong-organization"

        username = credentials[0] or candlepin_config("username")
        password = credentials[1] or candlepin_config("password")
        organization = credentials[2] or ""

        with pytest.raises(DBusError) as excinfo:
            private_proxy.Register(organization, username, password, {}, {}, locale)
            logger.debug(f"raised exception: {excinfo}")
            if credentials.organization == wrong_org:
                assert f"Organization {wrong_org} does not exist." in str(excinfo.value)
            else:
                assert "Invalid Credentials" in str(excinfo.value)
            assert not subman.is_registered
