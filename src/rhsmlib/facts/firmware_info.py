from __future__ import print_function, division, absolute_import

#
# Get the right platform specific provider or a null provider
#
# Copyright (c) 2010-2016 Red Hat, Inc.
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

from rhsmlib.facts import dmiinfo
from rhsmlib.facts import collector

ARCHES_WITHOUT_DMI = ["ppc64", "ppc64le", "s390x"]

log = logging.getLogger(__name__)


# This doesn't really do anything other than provide a null/noop provider for
# non-DMI platforms.
class NullFirmwareInfoCollector(object):
    """Default provider for platform without a specific platform info provider.

    ie, all platforms except those with DMI (ie, intel platforms)"""
    def __init__(self, *args, **kwargs):
        self.info = {}

    def get_all(self):
        return self.info


class FirmwareCollector(collector.FactsCollector):
    def __init__(self, prefix=None, testing=None, collected_hw_info=None):
        super(FirmwareCollector, self).__init__(
            prefix=prefix,
            testing=testing,
            collected_hw_info=collected_hw_info
        )

    def get_firmware_info(self):
        """Read and parse data that comes from platform specific interfaces.

        This is only dmi/smbios data for now (which isn't on ppc/s390).
        """
        firmware_info_collector = get_firmware_collector(
            arch=self.arch,
            prefix=self.prefix,
            testing=self.testing
        )

        # Pass in collected hardware so DMI etc can potentially override it
        firmware_info_dict = firmware_info_collector.get_all()
        # This can potentially clobber facts that already existed in self.allhw
        # (and is supposed to).
        return firmware_info_dict

    def get_all(self):
        virt_info = {}
        firmware_info = self.get_firmware_info()

        virt_info.update(firmware_info)
        return virt_info


# TODO/FIXME: As a first pass, move dmi and the generic firmware code here,
#             even though with kernels with sysfs dmi support, and a recent
#             version of dmidecode (> 3.0), most of the dmi info is readable
#             by a user. However, the system-uuid is not readable by a user,
#             and that is pretty much the only thing from DMI we care about,
def get_firmware_collector(arch, prefix=None, testing=None,
                           collected_hw_info=None):
    """
    Return a class that can be used to get firmware info specific to
    this systems platform.

    ie, DmiFirmwareInfoProvider on intel platforms, and a
    NullFirmwareInfoProvider otherwise.
    """
    # we could potential consider /proc/sysinfo as a FirmwareInfoProvider
    # but at the moment, it is just firmware/dmi stuff.

    if arch in ARCHES_WITHOUT_DMI:
        log.debug("Not looking for DMI info since it is not available on '%s'" % arch)
        firmware_provider_class = NullFirmwareInfoCollector
    else:
        try:
            import dmidecode  # noqa
            firmware_provider_class = dmiinfo.DmiFirmwareInfoCollector
        except:
            firmware_provider_class = NullFirmwareInfoCollector

    firmware_provider = firmware_provider_class(
        prefix=prefix,
        testing=testing,
        collected_hw_info=collected_hw_info
    )

    return firmware_provider
