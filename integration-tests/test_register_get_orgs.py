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
from funcy import partial, first

import logging

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Register Object and method GetOrgs

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#GetOrgs
for more details.

It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"

REQUIRED_KEYS = ("key", "displayName", "contentAccessMode")


def non_empty(value):
    return value and value.strip() != ""


def test_get_orgs_for_one_org_account(any_candlepin, subman, test_config):
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.GetOrgs(
            test_config.get("candlepin", "username"),
            test_config.get("candlepin", "password"),
            {},
            locale,
        )
        response_data = json.loads(response)
        logger.debug(f"response from the call: {response_data}")

        assert len(response_data) == 1  # an account with one org registered

        org_data = first(response_data)
        for key in REQUIRED_KEYS:
            assert key in org_data

        # it returns the proper org id
        assert org_data.get("key") == test_config.get("candlepin", "org")

        for key in REQUIRED_KEYS:
            assert non_empty(org_data.get(key))


def test_get_orgs_for_multi_org_account(any_candlepin, subman, test_config):
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.GetOrgs(
            test_config.get("candlepin", "multi_org", "username"),
            test_config.get("candlepin", "multi_org", "password"),
            {},
            locale,
        )
        response_data = json.loads(response)

        # an application should return the right number of organizations
        assert len(response_data) == len(test_config.get("candlepin", "multi_org", "orgs"))

        # required keys must have some value
        for org in response_data:
            for key in REQUIRED_KEYS:
                assert non_empty(org.get(key)), f"key {key} is required. tested org: {org}"

        # every org in response data should have the right org id
        assert frozenset(test_config.get("candlepin", "multi_org", "orgs")) == frozenset(
            org.get("key") for org in response_data
        )


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param(("wrong username", None), id="wrong username"),
        pytest.param((None, "wrong password"), id="wrong password"),
        pytest.param(("wrong username", "wrong password"), id="wrong username, wrong password"),
        pytest.param(("", None), id="empty username"),
        pytest.param((None, ""), id="empty password"),
        pytest.param(("", ""), id="empty username, empty password"),
    ],
)
def test_get_orgs_wrong_credentials(any_candlepin, subman, test_config, credentials):
    # skip empty username - see CCT-1501
    if credentials[0] == "":
        pytest.skip("opened ticket for wrong behavior in case a username is empty string - see CCT-1501")
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    candlepin_config = partial(test_config.get, "candlepin")
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        with pytest.raises(DBusError) as exc_info:
            private_proxy.GetOrgs(
                (credentials[0] is None and candlepin_config("username")) or credentials[0],
                (credentials[1] is None and candlepin_config("password")) or credentials[1],
                {},
                locale,
            )
        data = json.loads(str(exc_info.value))
        assert "Invalid Credentials" in data["message"]
