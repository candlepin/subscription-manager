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
from funcy import partial, all, first

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


# I use text parameter since I cannot count how many orgs belong to a multi org account
# it is calculated dynamically using test_config
#
# And pytest id of a test is well readable
#     rather than test_GetOrgs[1] test_GetOrgs[2]
#     you see     test_GetOrgs[one org], test_GetOrgs[more orgs]
@pytest.mark.parametrize("num_of_orgs", ["one org", "more orgs"])
def test_GetOrgs(any_candlepin, subman, test_config, num_of_orgs):
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.GetOrgs(
            num_of_orgs == "one org"
            and test_config.get("candlepin", "username")
            or test_config.get("candlepin", "more_orgs", "username"),
            num_of_orgs == "one org"
            and test_config.get("candlepin", "password")
            or test_config.get("candlepin", "more_orgs", "password"),
            {},
            locale,
        )
        response_data = json.loads(response)
        # an application should return the right number of environments
        if num_of_orgs == "one org":
            assert len(response_data) == 1
        else:
            assert len(response_data) == len(test_config.get("candlepin", "more_orgs", "orgs"))

        required_keys = frozenset(("key", "displayName", "contentAccessMode"))
        assert all(required_keys.issubset(frozenset(org.keys())) for org in response_data)

        # it returns the proper environment ids
        if num_of_orgs == "one org":
            assert first(response_data).get("key") == test_config.get("candlepin", "org")
        else:
            assert frozenset(test_config.get("candlepin", "more_orgs", "orgs")) == frozenset(
                org.get("key") for org in response_data
            )

        # each value is filled
        def is_filled(value):
            return value and value.strip() != ""

        def every_required_value(predicate):
            def composition(org):
                required_values = [org.get(key) for key in required_keys]
                return all(predicate(value) for value in required_values)

            return composition

        def for_each_org_in(iterator, predicate):
            return all(predicate(item) for item in iterator)

        assert for_each_org_in(response_data, every_required_value(is_filled))


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
def test_GetOrgs_wrong_credentials(any_candlepin, subman, test_config, credentials):
    # skip empty username - see CCT-1501
    if credentials[0] == "":
        pytest.skip("openned ticket for wrong behavior in case username is empty string - see CCT-1501")
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    candlepin_config = partial(test_config.get, "candlepin")
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        with pytest.raises(DBusError) as excinfo:
            private_proxy.GetOrgs(
                (credentials[0] is None and candlepin_config("username")) or credentials[0],
                (credentials[1] is None and candlepin_config("password")) or credentials[1],
                {},
                locale,
            )
        data = json.loads(str(excinfo.value))
        assert "Invalid Credentials" in data["message"]
