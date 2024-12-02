"""
This Python module contains integration tests for rhc.
It uses pytest-client-tools Python module.More information about this
module could be found: https://github.com/ptoscano/pytest-client-tools/
"""

import contextlib
import sh


def test_busctl_get_consumer_uuid():
    """
    Simple smoke test using busctl CLI tool. It tries to call simple D-Bus method.
    """
    with contextlib.suppress(Exception):
        sh.busctl(
            "call",
            "com.redhat.RHSM1",
            "/com/redhat/RHSM1/Consumer",
            "com.redhat.RHSM1.Consumer",
            "GetUuid",
            "s",
            '""',
        )
