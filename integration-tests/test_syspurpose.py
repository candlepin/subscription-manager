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

from constants import RHSM, RHSM_SYSPURPOSE, RHSM_SYSPURPOSE_FILE_PATH, RHSM_VALID_FIELDS_FILE_PATH
from dasbus.error import DBusError
from dasbus.typing import get_variant, Str
from funcy import partial, first
from utils import loop_until, json_from_file
import logging
import json
import pytest

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Syspurpose Object.

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#syspurpose
for more details.

Main use cases are presented in this file.

There is a traditional way to play with syspurpose in a Red Hat ecosystem:
   subscription-manager syspurpose role --unset=foo --noproxy=subscription.rhsm.redhat.com

"""

# each call uses standard english locale
locale = "en_US.UTF-8"


@pytest.mark.parametrize("field", ["usage", "service_level_agreement", "role"])
def test_set_syspurpose(any_candlepin, field, subman):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.SetSyspurpose

    - The method sets syspurpose
    - the method returns actual syspurpose data
    - the data in the set request appear in the syspurpose file
      /etc/rhsm/syspurpose/syspurpose.json

    dbus-send --system --print-reply --dest=com.redhat.RHSM1 \
              /com/redhat/RHSM1/Syspurpose \
              com.redhat.RHSM1.Syspurpose.SetSyspurpose \
              dict:string:string:"usage","Production","service_level_agreement","Premium" \
              string:""
    """
    syspurpose_before_call = (
        json_from_file(RHSM_SYSPURPOSE_FILE_PATH) if RHSM_SYSPURPOSE_FILE_PATH.exists() else {}
    )
    valid_fields = json_from_file(RHSM_VALID_FIELDS_FILE_PATH)

    old_value = syspurpose_before_call.get(field)
    new_value = first(set(valid_fields.get(field)) - set([old_value] if old_value else []))

    syspurpose_to_set = {field: get_variant(Str, new_value)}
    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)
    response = proxy.SetSyspurpose(syspurpose_to_set, locale)
    syspurpose_from_dbus_call = json.loads(response)
    assert syspurpose_from_dbus_call == {field: new_value}

    # new value appears in the syspurpose file
    # the other data should be deleted
    # - ie. just the requested data appear in the file
    syspurpose_after_call = json_from_file(RHSM_SYSPURPOSE_FILE_PATH)
    assert syspurpose_after_call == {field: new_value}

    # subscription-manager should return the same data as DBus API call
    syspurpose_from_subman = json.loads(subman.run("syspurpose", "--show").stdout)
    assert syspurpose_from_subman == {field: new_value}


def test_set_syspurpose_with_empty_data(any_candlepin, subman):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.SetSyspurpose

    This test verifies that the method can delete syspurpose.
    - ie. empty data are sent in a request.
    """

    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)

    # I will set it at first
    syspurpose_to_set = {"usage": get_variant(Str, "Production")}
    proxy.SetSyspurpose(syspurpose_to_set, locale)
    syspurpose_before_call = json_from_file(RHSM_SYSPURPOSE_FILE_PATH)
    assert syspurpose_before_call["usage"] == "Production"

    # the cleaning call
    response = proxy.SetSyspurpose({}, locale)
    syspurpose_from_dbus_call = json.loads(response)
    syspurpose_after_call = (
        json_from_file(RHSM_SYSPURPOSE_FILE_PATH) if RHSM_SYSPURPOSE_FILE_PATH.exists() else {}
    )
    syspurpose_from_subman = json.loads(subman.run("syspurpose", "--show").stdout)

    assert syspurpose_after_call == {}
    assert syspurpose_from_dbus_call == {}
    assert syspurpose_from_subman == {}


@pytest.mark.xfail(reason="a dbus error message not implemented yet - see CCT-1555")
def test_set_syspurpose_with_invalid_value(any_candlepin, subman):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.SetSyspurpose

    This test verifies that the method informs a user that invalid value was requested
    the method should raise DBus Error
    """
    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)
    response = proxy.SetSyspurpose(
        {
            "usage": get_variant(Str, "Non Valid Value"),
            "service_level_agreement": get_variant(Str, "Premium"),
        },
        locale,
    )
    assert "Invalid value requested" in str(response)


@pytest.mark.xfail(reason="a dbus error message not implemented yet - see CCT-1555")
def test_set_syspurpose_with_invalid_field(any_candlepin, subman):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.SetSyspurpose

    This test verifies that the method informs a user that invalid value was requested
    the method should raise DBus Error
    """
    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)
    response = proxy.SetSyspurpose(
        {
            "invalid-field": get_variant(Str, "any value"),
            "service_level_agreement": get_variant(Str, "Premium"),
        },
        locale,
    )
    assert "Invalid field is set" in str(response)
    # TODO: add subman response


@pytest.mark.parametrize(
    "syspurpose",
    [
        pytest.param(
            {"usage": "Production", "service_level_agreement": "Premium"}, id="non empty syspurpose"
        ),
        pytest.param({}, id="empty syspurpose"),
    ],
)
def test_get_syspurpose(any_candlepin, subman, syspurpose):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.GetSyspurpose

    busctl call com.redhat.RHSM1 \
           /com/redhat/RHSM1/Syspurpose \
           com.redhat.RHSM1.Syspurpose \
           GetSyspurpose \
           s ""

    - this test verifies that it returns the same data as presented
    in the file /etc/rhsm/syspurpose/syspurpose.json

    - a command subscription-manager syspurpose --show
    should return the same data
    """
    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)

    data = dict([(key, get_variant(Str, value)) for (key, value) in syspurpose.items()])
    proxy.SetSyspurpose(data, locale)

    response = proxy.GetSyspurpose(locale)

    syspurpose_from_config = json_from_file(RHSM_SYSPURPOSE_FILE_PATH)
    syspurpose_from_dbus_call = json.loads(response)
    syspurpose_from_subman = json.loads(subman.run("syspurpose", "--show").stdout)

    assert syspurpose_from_config == syspurpose
    assert syspurpose_from_dbus_call == syspurpose
    assert syspurpose_from_subman == syspurpose


def test_get_valid_fields_when_system_is_registered(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.GetValidFiels

    - The method returns a list of valid fields for the current owner

    busctl call com.redhat.RHSM1 \
           /com/redhat/RHSM1/Syspurpose \
           com.redhat.RHSM1.Syspurpose \
           GetValidFields \
           s ""

    - this test verifies that it returns the same json data as candlepin stores
    """
    candlepin_config = partial(test_config.get, "candlepin")
    subman.register(
        username=candlepin_config("username"),
        password=candlepin_config("password"),
        org=candlepin_config("org"),
    )
    loop_until(lambda: subman.is_registered)

    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)
    response = proxy.GetValidFields(locale)

    data_from_dbus_call = json.loads(response)

    valid_fields_from_response = data_from_dbus_call.get("systemPurposeAttributes")
    valid_fields = json_from_file(candlepin_config("valid_fields_file"))
    assert valid_fields == valid_fields_from_response


def test_get_valid_fields_when_system_is_not_registered(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Syspurpose.GetValidFiels

    busctl call com.redhat.RHSM1 \
           /com/redhat/RHSM1/Syspurpose \
           com.redhat.RHSM1.Syspurpose \
           GetValidFields \
           s ""

    - this test verifies that the method returns error message
    """
    proxy = RHSM.get_proxy(RHSM_SYSPURPOSE)
    with pytest.raises(DBusError) as excinfo:
        proxy.GetValidFields(locale)
    assert "Unable to get valid system purpose fields. The system is not registered." in str(excinfo.value)
