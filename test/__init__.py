import os
import pathlib
import sys
from typing import Callable, List

import pytest

from . import rhsm_display
rhsm_display.set_display()

# Hijack sys.path, so we don't have to use 'PYTHONPATH=src/' prefix
rootdir = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(rootdir / "src"))


subman_marker_dbus = pytest.mark.dbus
subman_marker_functional = pytest.mark.functional
subman_marker_zypper = pytest.mark.zypper
subman_marker_slow = pytest.mark.slow
# This allows us to set higher timeout limit for tests that are known to be slow
subman_marker_slow_timeout = pytest.mark.timeout(40)


def subman_marker_needs_envvars(*envvars: List[str]) -> Callable:
    """Skip test if one or more environment variables are missing."""
    missing_vars: List[str] = [v for v in envvars if v not in os.environ]
    skip_func: Callable = pytest.mark.skipif(
        missing_vars,
        reason=f"Missing environment variables {', '.join(missing_vars)}."
    )
    return skip_func
