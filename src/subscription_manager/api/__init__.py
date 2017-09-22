from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2015 Red Hat, Inc.
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
"""
Class and methods made available in __all__ are provided for use by
external applications.

All reasonable efforts will be made to maintain compatibility.
"""
from functools import wraps
from subscription_manager import logutil

injected = False


def request_injection(func):
    """This idempotent decorator can be applied to initialize the dependency
    injection used by subscription manager.  Users of the API methods will not
    normally need to use this decorator as it will already have been called."""
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        global injected
        if not injected:
            logutil.init_logger()

            from subscription_manager.injectioninit import init_dep_injection
            init_dep_injection()
            injected = True
        return func(*args, **kwargs)
    return func_wrapper


from .repos import disable_yum_repositories, enable_yum_repositories

from subscription_manager.version import rpm_version as version

__all__ = [
    'request_injection',
    'disable_yum_repositories',
    'enable_yum_repositories',
    'version',
]
