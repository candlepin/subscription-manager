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

from .repos import disable_yum_repositories, enable_yum_repositories

from subscription_manager.version import rpm_version as version

from functools import wraps

__all__ = [
    'disable_yum_repositories',
    'enable_yum_repositories',
    'version',
]
