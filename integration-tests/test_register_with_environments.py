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
import re
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str

import logging

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Register Object - with environments

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#register
for more details.

Usecases that use environment are presented in this file.

It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"


def subman_identity(subman):
    response = subman.run("identity", check=False)
    lines = [line.strip() for line in response.stdout.split("\n")]
    pairs = [re.split(r"[\ \t]*:[\ \t]*", line) for line in lines if line]
    return dict(pairs)


# a name of an environment comes from test_config. The param below is an index of the environment
#     in a property candlepin.environment.names - it is a test_config property
@pytest.mark.parametrize(
    "environment_indexes",
    [
        pytest.param([0], id="one valid environment"),
        pytest.param([0, 1], id="two valid environments"),
    ],
)
def test_register_with_org_and_environments(external_candlepin, subman, test_config, environment_indexes):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)

    env_names_in_config = test_config.get("candlepin", "environment", "names")
    env_ids_in_config = test_config.get("candlepin", "environment", "ids")
    env_ids = [env_ids_in_config[idx] for idx in environment_indexes]
    env_names = [env_names_in_config[idx] for idx in environment_indexes]

    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.Register(
            test_config.get("candlepin", "org"),
            test_config.get("candlepin", "username"),
            test_config.get("candlepin", "password"),
            {"environments": get_variant(Str, ",".join(env_ids))},
            {},
            locale,
        )
        response_data = json.loads(response)
        environment_in_response = response_data.get("environment")
        assert ",".join(env_names) == environment_in_response["name"]
        if len(environment_indexes) > 1:
            environment_names = subman_identity(subman).get("environment names")
            assert ",".join(env_names) == environment_names
        else:
            environment_name = subman_identity(subman).get("environment name")
            assert ",".join(env_names) == environment_name

    assert subman.is_registered


def test_register_with_org_and_wrong_environment(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)

    wrong_env_id = "wrong-env-id"
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        with pytest.raises(DBusError) as excinfo:
            private_proxy.Register(
                test_config.get("candlepin", "org"),
                test_config.get("candlepin", "username"),
                test_config.get("candlepin", "password"),
                {"environments": get_variant(Str, wrong_env_id)},
                {},
                locale,
            )
        error_msg = json.loads(str(excinfo.value))["message"]
        assert f'Environment with ID "{wrong_env_id}" could not be found' in error_msg

    assert not subman.is_registered


def test_register_with_org_and_empty_environment(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6

    The property environment will by set to empty string.
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)

    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        with pytest.raises(DBusError) as excinfo:
            private_proxy.Register(
                test_config.get("candlepin", "org"),
                test_config.get("candlepin", "username"),
                test_config.get("candlepin", "password"),
                {"environments": get_variant(Str, "")},
                {},
                locale,
            )
        error_msg = json.loads(str(excinfo.value))["message"]
        assert 'Environment with ID "" could not be found' in error_msg

    assert not subman.is_registered
