from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.typing import get_variant, Str
from funcy import first, partial

import json
import re
import logging

logger = logging.getLogger(__name__)
locale = "en_US.UTF-8"

"""
It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""


def test_register_with_activation_keys_and_environments(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    candlepin_config = partial(test_config.get, "candlepin")

    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    act_keynames = candlepin_config("activation_keys")
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = json.loads(
            private_proxy.RegisterWithActivationKeys(
                candlepin_config("org"),
                act_keynames,
                {"environments": get_variant(Str, first(candlepin_config("environment", "ids")))},
                {},
                locale,
            )
        )

        assert (
            "activationKeys" in response
        ), "DBus method returns what activation keys were used to register a system"

        logger.debug(response["activationKeys"])
        assert sorted([ii["activationKeyName"] for ii in response["activationKeys"]]) == sorted(act_keynames)

        subman_response = subman.run("identity")
        """
        (env) [root@kvm-08-guest21 integration-tests]# subscription-manager identity

        system identity: 5c00d2c6-5bea-4b6d-8662-8680e38f0dab
        name: kvm-08-guest21.lab.eng.rdu2.dc.redhat.com
        org name: Donald Duck
        org ID: donaldduck
        environment name: env-name-01
        """

        def read_pair(line):
            result = re.search(r"^([^:]+):(.*)", line.strip())
            if result:
                pair = [g.strip() for g in result.groups()]
                return pair
            return []

        pairs = dict([read_pair(line) for line in subman_response.stdout.splitlines()])
        logger.debug(pairs)
        assert pairs["environment name"] == first(candlepin_config("environment", "names"))

    assert subman.is_registered
