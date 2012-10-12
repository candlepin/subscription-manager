#
# Copyright (c) 2012 Red Hat, Inc.
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
from rhsm.profile import RPMProfile


class VersionError(Exception):
    pass


class Versions(object):
    """
    Collects version information about the installed versions of
    python-rhsm and subscription-manager RPMs.
    """

    SUBSCRIPTION_MANAGER = "subscription-manager"
    PYTHON_RHSM = "python-rhsm"
    UPSTREAM_SERVER = "upstream-server"

    __shared_data = {}
    __initialized = False
    __to_collect = [SUBSCRIPTION_MANAGER, PYTHON_RHSM]

    def __init__(self):
        # Replace __dict__ so that we can share data across instances,
        # and load only once.
        self.__dict__ = self.__shared_data

        # We only want to initialize this data once.
        if not self.__initialized:
            self.__initialized = True
            self._collect_data()

    def _collect_data(self):
        self._version_info = {}

        for package_def in self._get_packages():
            name = package_def['name']
            if name in self.__to_collect:
                self._version_info[name] = package_def

    def _get_packages(self):
        profile = RPMProfile()
        return profile.collect()

    def get_version(self, package_name):
        return self._get_package_attribute(package_name, "version")

    def get_release(self, package_name):
        return self._get_package_attribute(package_name, "release")

    def _get_package_attribute(self, package_name, attribute_name):
        if not package_name in self._version_info:
            return ''

        return self._version_info[package_name][attribute_name]
