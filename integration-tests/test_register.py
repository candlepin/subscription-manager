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

Main use cases are presented in this file.

Special use cases for registering (with proxy, activation keys, ...) are presented
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


wrong_org = "wrong organization"


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param(("wrong username", None, None), id="wrong username"),
        pytest.param((None, "wrong password", None), id="wrong password"),
        pytest.param((None, None, wrong_org), id="wrong organization"),
    ],
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

        username = credentials[0] or candlepin_config("username")
        password = credentials[1] or candlepin_config("password")
        organization = credentials[2] or ""

        with pytest.raises(DBusError) as excinfo:
            private_proxy.Register(organization, username, password, {}, {}, locale)
            logger.debug(f"raised exception: {excinfo}")
        if organization == wrong_org:
            assert f"Organization {wrong_org} does not exist." in str(excinfo.value)
        else:
            assert "Invalid Credentials" in str(excinfo.value)
        assert not subman.is_registered


def test_get_environments(external_candlepin, subman, test_config):
    """
    GetEnvironments(username: string,
                    password: string,
                    org_id: string,
                    connection_options: dictionary(string, variant),
                    locale: string)
    -> list[dictionary(string, variant)]

    The parameters are the same as GetOrgs():

    "username" & "password" are the credentials that would be used to register later on

    "org_id" is the organization to query for the environments; this is required to avoid querying
    all the organizations of an user (there is the GetOrgs() API already for it)

    "connection_options" contains the connection options

    "locale" is the locale to use for translating the returned messages in case of errors
    The return value is a list of dictionaries representing the environments, each like this:
    {
    "description": "The environment 2",
    "id": "envId2",
    "name": "Environment 2",
    "type": "",
    }
    "description" is the description of the environment
    "id" is the ID of the environment
    "name" is the name of the environment
    "type" is the type of the environment (can be empty of "classic" environments)
    """

    candlepin_config = partial(test_config.get, "candlepin")

    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)

        username = candlepin_config("username")
        password = candlepin_config("password")
        organization = candlepin_config("org")
        response = private_proxy.GetEnvironments(username, password, organization, {}, locale)
        # Expected result could look like this:
        # [
        #   {
        #     "id": "env-id-01",
        #     "name": "env-name-01",
        #     "type": "",
        #     "description": "Testing environment num. 1"
        #   },
        #   {
        #     "id": "env-id-02",
        #     "name": "env-name-02",
        #     "type": "content-template",
        #     "description": "Testing environment num. 2"
        #   }
        # ]
        data = json.loads(response)
        environments_in_response = frozenset(f"({ii.get('id')},{ii.get('name')})" for ii in data)
        environments_in_config = frozenset(
            f"({ii[0]},{ii[1]})"
            for ii in zip(candlepin_config("environment", "ids"), candlepin_config("environment", "names"))
        )
        assert environments_in_response == environments_in_config

        required_keys = frozenset(["id", "name", "type", "description"])
        assert all(required_keys == frozenset(item.keys()) for item in data)
