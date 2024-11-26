import os
import pytest
import contextlib
from pytest_client_tools.util import Version
from conftest import RHSMPrivateBus
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_REGISTER
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str, get_native

import sh
import subprocess
import json
import logging

import re
from dataclasses import dataclass
from functools import reduce
import json
from funcy import first

logger = logging.getLogger(__name__)

"""
It is important to run tests as root. Since RegisterServer is a system dbus service.
And it provides a unix socket connection.
"""

def test_register(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register("",
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {},
                               {},
                               locale)
    assert subman.is_registered
    

def test_register_with_org(external_candlepin, subman, test_config): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register(test_config.get("candlepin","org"),
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {},
                               {},
                               locale)
    assert subman.is_registered


@pytest.mark.parametrize("enable_content",["true","false"])
def test_register_with_enable_content(external_candlepin, subman, test_config, enable_content): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        private_proxy.Register(test_config.get("candlepin","org"),
                               test_config.get("candlepin","username"),
                               test_config.get("candlepin","password"),
                               {
                                   "enable_content": get_variant(Str,enable_content)
                               },
                               {},
                               locale)
    assert subman.is_registered
   

def test_register_with_wrong_values(external_candlepin, subman, test_config, subtests): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")

        with subtests.test(msg="Register with wrong username"):
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register("",
                                       "wrong-username",
                                       test_config.get("candlepin","password"),
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert "Invalid username or password." in str(excinfo.value)
            assert not subman.is_registered
            
        with subtests.test(msg="Register with wrong password"):
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register("",
                                       test_config.get("candlepin","username"),
                                       "wrong-password",
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert "Invalid username or password." in str(excinfo.value)
            assert not subman.is_registered
            
        with subtests.test(msg="Register with wrong organization"):
            wrong_org="wrong-organization"
            with pytest.raises(DBusError) as excinfo:
                private_proxy.Register(wrong_org,
                                       test_config.get("candlepin","username"),
                                       test_config.get("candlepin","password"),
                                       {},
                                       {},
                                       locale)
            logger.debug(f"raised exception: {excinfo}")
            assert f"Organization {wrong_org} does not exist." in str(excinfo.value)
            assert not subman.is_registered


def test_get_environments(external_candlepin, subman, test_config):
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        dbus_response = private_proxy.GetEnvironments(test_config.get("candlepin","username"),
                                                      test_config.get("candlepin","password"),
                                                      test_config.get("candlepin","org") or "",
                                                      {},
                                                      locale)
        logger.debug(f"response from Register/GetEnvironments: {dbus_response}")
        subman_response = subman.run(
            "environments",
            f"--username={test_config.get('candlepin','username')}",
            f"--password={test_config.get('candlepin','password')}",
            f"--org={test_config.get('candlepin','org')}"
        )
        """
        (env) [root@dell-r640-008 integration-tests]# subscription-manager environments --list --username duey --password password --org donaldduck
        +-------------------------------------------+
              Environments
        +-------------------------------------------+
        Name:        env-01
        Description: 
        
        Name:        env-0r
        Description: Environment 0r
        """
        @dataclass
        class Accumulator:
            actual_env: dict
            environments: list[dict]

        def parse_pair(acc,line):
            result = re.search(r"^([\w]+):(.*)",line.strip())
            if result:
                pair = dict([[g.strip() for g in result.groups()]])
                key=list(pair.keys())[0]
                if key in acc.actual_env:
                    # new environment appeared
                    acc.environments.append(acc.actual_env)
                    acc.actual_env = pair
                else:
                    acc.actual_env.update(pair)
            return acc

        result = reduce(parse_pair, subman_response.stdout.splitlines(), Accumulator(actual_env=dict(), environments=[]))
        environments = result.environments + [result.actual_env,]

        # I will transform dicts to a set of strings aka 'key=something'
        # It will be much easier to compare sets rather than dicts

        def as_set(env):
            return frozenset([f"{item[0].lower()}={item[1]}" for item in env.items()])
        
        environments_as_sets=list(map(as_set, sorted(environments, key=lambda env: env['Name'])))
        response_set=list(map(as_set,sorted(json.loads(dbus_response), key=lambda env: env['name'])))

        logger.debug(environments_as_sets)
        logger.debug(response_set)

        assert len(environments_as_sets) == len(response_set)
        for orig_env, env_from_response in zip(environments_as_sets, response_set):
            assert orig_env.issubset(env_from_response), \
                "environment from sub-man command is a subset of fields returned by dbus GetEnvironments"
            

def test_register_with_activation_key(external_candlepin, subman, test_config): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    act_keyname_in_use = first(test_config.get("candlepin","activation_keys"))
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        response = json.loads(private_proxy.RegisterWithActivationKeys(test_config.get("candlepin","org"),
                                                                       [ act_keyname_in_use ],
                                                                       {},
                                                                       {},
                                                                       locale))

        assert 'activationKeys' in response,\
            "DBus method returns what activation keys were used to register a system"

        assert [ii['activationKeyName'] for ii in response['activationKeys']] == [act_keyname_in_use]
                   
    assert subman.is_registered


def test_register_with_activation_keys(external_candlepin, subman, test_config): 
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    assert not subman.is_registered
    proxy = RHSM.get_proxy(RHSM_REGISTER_SERVER)
    act_keynames = test_config.get("candlepin","activation_keys")
    with RHSMPrivateBus(proxy) as private_bus:
        private_proxy = private_bus.get_proxy(RHSM.service_name,
                                              RHSM_REGISTER.object_path)
        locale = os.environ.get("LANG", "")
        response = json.loads(private_proxy.RegisterWithActivationKeys(test_config.get("candlepin","org"),
                                                                       act_keynames,
                                                                       {},
                                                                       {},
                                                                       locale))

        assert 'activationKeys' in response,\
            "DBus method returns what activation keys were used to register a system"

        assert sorted([ii['activationKeyName'] for ii in response['activationKeys']]) == sorted(act_keynames)
                   
    assert subman.is_registered
