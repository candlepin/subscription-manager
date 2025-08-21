import pytest
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.error import DBusError
from funcy import partial, take, first
from dasbus.typing import get_variant, Str
import json
import logging
from utils import subman_identity

logger = logging.getLogger(__name__)
locale = "en_US.UTF-8"

"""
It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""


@pytest.mark.parametrize("enable_content", ["true", "false", "wrong-value", "not-applied"])
@pytest.mark.parametrize("num_of_act_keys_to_use", [1, 2])
def test_register_with_activation_keys_and_enable_content(
    external_candlepin, subman, test_config, num_of_act_keys_to_use, enable_content
):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    enable_content is tested for historical reason.

    It should not have any impact on registration to use enable_content True/False.

    There is even wrong case of a value for enable_content.
    """
    assert not subman.is_registered

    candlepin_config = partial(test_config.get, "candlepin")
    act_keynames = take(num_of_act_keys_to_use, candlepin_config("activation_keys"))

    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name, object_path=RHSM_REGISTER.object_path
        )
        if enable_content == "not-applied":
            options = {}
        else:
            options = {"enable_content": get_variant(Str, enable_content)}
        response = json.loads(
            private_proxy.RegisterWithActivationKeys(
                candlepin_config("org"),
                act_keynames,
                options,
                {},
                locale,
            )
        )
        assert "activationKeys" in response
        assert sorted([ii["activationKeyName"] for ii in response["activationKeys"]]) == sorted(act_keynames)
        assert subman.is_registered


def test_register_with_activation_keys_and_environments(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    candlepin_config = partial(test_config.get, "candlepin")

    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    act_keynames = candlepin_config("activation_keys")
    environment_id = first(candlepin_config("environment", "ids"))
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name, RHSM_REGISTER.object_path)
        response = private_proxy.RegisterWithActivationKeys(
            candlepin_config("org"),
            act_keynames,
            {"environments": get_variant(Str, environment_id)},
            {},
            locale,
        )
        response_data = json.loads(response)
        assert "activationKeys" in response_data
        assert frozenset(ii["activationKeyName"] for ii in response_data["activationKeys"]) == frozenset(
            act_keynames
        )

        # applied environment appears in the response
        environment_name = first(candlepin_config("environment", "names"))
        assert response_data["environment"]["name"] == environment_name
        assert first(response_data["environments"])["name"] == environment_name
        assert first(response_data["environments"])["id"] == environment_id

        # applied environment appears in response of 'subscription-manager identity"
        pairs = subman_identity(subman)
        assert pairs["environment name"] == environment_name
        assert subman.is_registered


@pytest.mark.xfail(reason="openned bug for this case: CCT-1559")
def test_register_with_activation_keys_with_empty_list(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered

    candlepin_config = partial(test_config.get, "candlepin")
    act_keys = []
    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name,
            object_path=RHSM_REGISTER.object_path,
            interface_name=RHSM_REGISTER.interface_name,
        )
        response = private_proxy.RegisterWithActivationKeys(candlepin_config("org"), act_keys, {}, {}, locale)
        response_data = json.loads(response)
        assert "No activation key specified" in response_data["message"]
        assert response_data["activationKeys"] == []

    assert subman.is_registered


def test_register_with_activation_keys_with_wrong_key_among_good_ones(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6

    Given a DBus method RegisterWithActivationKeys is used to register a system
    When an invalid activation key appears in a list of valid activation keys
    Then an application registers a system using all valid activation keys
    and the application returns a list of activation keys that was used for registration.
    """
    valid_act_keys = test_config.get("candlepin", "activation_keys") or []
    act_keys = valid_act_keys + ["wrong-act-key"]
    org_to_use = test_config.get("candlepin", "org")

    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name,
            object_path=RHSM_REGISTER.object_path,
            interface_name=RHSM_REGISTER.interface_name,
        )
        response = private_proxy.RegisterWithActivationKeys(org_to_use, act_keys, {}, {}, locale)
        response_data = json.loads(response)
        assert "activationKeys" in response_data
        assert sorted([ii["activationKeyName"] for ii in response_data["activationKeys"]]) == sorted(
            valid_act_keys
        ), "A list of activation keys in the response is not the same as a list of valid activation keys"

    assert subman.is_registered


def test_register_with_activation_keys_wrong_act_key(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    act_keys = ["wrong-act-key"]
    org_to_use = test_config.get("candlepin", "org")

    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name,
            object_path=RHSM_REGISTER.object_path,
            interface_name=RHSM_REGISTER.interface_name,
        )
        with pytest.raises(DBusError) as exc_info:
            private_proxy.RegisterWithActivationKeys(org_to_use, act_keys, {}, {}, locale)
        assert "None of the activation keys specified exist for this org" in str(exc_info.value)

    assert not subman.is_registered


def test_register_with_activation_keys_wrong_org(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    candlepin_config = partial(test_config.get, "candlepin")
    act_keys = candlepin_config("activation_keys")
    org_to_use = "wrong-org"

    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name,
            object_path=RHSM_REGISTER.object_path,
            interface_name=RHSM_REGISTER.interface_name,
        )
        with pytest.raises(DBusError) as exc_info:
            json.loads(private_proxy.RegisterWithActivationKeys(org_to_use, act_keys, {}, {}, locale))
        assert f"Organization {org_to_use} does not exist." in str(exc_info.value)

    assert not subman.is_registered


def test_register_with_activation_keys_wrong_org_and_wrong_key(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    act_keys = ["wrong-act-key"]
    org_to_use = "wrong-org"

    proxy = RHSM.get_proxy(
        object_path=RHSM_REGISTER_SERVER.object_path, interface_name=RHSM_REGISTER_SERVER.interface_name
    )
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(
            service_name=RHSM.service_name,
            object_path=RHSM_REGISTER.object_path,
            interface_name=RHSM_REGISTER.interface_name,
        )
        with pytest.raises(DBusError) as exc_info:
            json.loads(private_proxy.RegisterWithActivationKeys(org_to_use, act_keys, {}, {}, locale))
        assert f"Organization {org_to_use} does not exist." in str(exc_info.value)

    assert not subman.is_registered
