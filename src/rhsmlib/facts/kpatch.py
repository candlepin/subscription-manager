# Copyright (c) 2019 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import logging
import os

from rhsmlib.facts import collector
from rhsm.utils import which

log = logging.getLogger(__name__)


class KPatchCollector(collector.FactsCollector):
    """
    Class used for collecting facts related to installed and loaded liver kernel patches (kpatch)
    """

    DIR_WITH_INSTALLED_KPATCH_MODULES = "/var/lib/kpatch"

    # Current kpatch module can be in several directories according version of kpatch
    DIRS_WITH_LOADED_MODULE = [
        "/sys/kernel/livepatch",
        "/sys/kernel/kpatch/patches",
        "/sys/kernel/kpatch"
    ]

    def get_all(self):
        return self.get_kpatch_info()

    def get_kpatch_info(self):
        """
        Get all information about kpatch on current system
        :return: dictionary with kpatch information
        """
        kpatch_info = {}

        if self._is_kpatch_installed():
            kpatch_info['kpatch.installed'] = self._get_installed_live_kernel_patches()
            kpatch_info['kpatch.loaded'] = self._get_loaded_live_kernel_patch()

        return kpatch_info

    @staticmethod
    def _is_kpatch_installed():
        """
        Check if kpatch is installed
        :return: Return true, when kpatch CLI tool is installed. Otherwise return False
        """
        return which('kpatch') is not None

    def _get_installed_live_kernel_patches(self):
        """
        Return list of installed live kernel patches
        :return: list of strings with live kernel patches
        """
        installed_kpatches = []

        # Directory with installed kpatches contains several directories
        # Each directory should contain installed kpatch
        if os.path.isdir(self.DIR_WITH_INSTALLED_KPATCH_MODULES):
            files = os.listdir(self.DIR_WITH_INSTALLED_KPATCH_MODULES)
            for kpatch in files:
                if os.path.isdir(os.path.join(self.DIR_WITH_INSTALLED_KPATCH_MODULES, kpatch)):
                    installed_kpatches.append(kpatch)

        return " ".join(installed_kpatches)

    def _get_loaded_live_kernel_patch(self):
        """
        Get currently used kpatch
        :return: String with current kpach
        """
        current_kpatch = ""

        # Installed kpatches can be installed in several directories.
        # Use first existing directory from the list
        for kpatch_dir in self.DIRS_WITH_LOADED_MODULE:
            if os.path.isdir(kpatch_dir):
                files = os.listdir(kpatch_dir)
                for kpatch in files:
                    if os.path.isdir(os.path.join(kpatch_dir, kpatch)):
                        current_kpatch = kpatch
                break

        return current_kpatch
