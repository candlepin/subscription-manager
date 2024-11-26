import os
import pytest
import contextlib
from pytest_client_tools.util import Version
import conftest
from constants import RHSM, RHSM_REGISTER_SERVER, RHSM_UNREGISTER

import sh
import subprocess
import json
import logging
from functools import partial

log = logging.getLogger(__name__)

def test_unregister(external_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#methods-6
    """
    candlepin_config = partial(test_config.get, "candlepin")
    subman.register(username=candlepin_config("username"),
                    password=candlepin_config("password"))
    conftest.loop_until(lambda: subman.is_registered)
    proxy=RHSM.get_proxy(RHSM_UNREGISTER, interface_name=RHSM_UNREGISTER)    
    # proxy = RHSM.get_proxy(RHSM.service_name,
    #                        RHSM_UNREGISTER.object_path)
    locale = os.environ.get("LANG", "")
    proxy.Unregister({},locale)
    assert not subman.is_registered
