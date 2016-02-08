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
import os

# The dmiinfo module will raise a ImportError if the 'dmidecode' module
# fails to import. So expect that.
try:
    import dmiinfo
except ImportError, e:
    dmiinfo = None

FIRMWARE_DUMP_FILENAME = "dmi.dump"
ARCHES_WITHOUT_DMI = ["ppc64", "ppc64le", "s390x"]

log = logging.getLogger(__name__)


# This doesn't really do anything other than provide a null/noop provider for
# non-DMI platforms.
class NullFirmwareInfoProvider(object):
    """Default provider for platform without a specific platform info provider.

    ie, all platforms except those with DMI (ie, intel platforms)"""
    def __init__(self, hardware_info, dump_file=None):
        self.info = {}


# TODO/FIXME: As a first pass, move dmi and the generic firmware code here,
#             even though with kernels with sysfs dmi support, and a recent
#             version of dmidecode (> 3.0), most of the dmi info is readable
#             by a user. However, the system-uuid is not readable by a user,
#             and that is pretty much the only thing from DMI we care about,
def get_firmware_provider(arch, prefix=None, testing=None):
    """
    Return a class that can be used to get firmware info specific to
    this systems platform.

    ie, DmiFirmwareInfoProvider on intel platforms, and a
    NullFirmwareInfoProvider otherwise.
    """
    # we could potential consider /proc/sysinfo as a FirmwareInfoProvider
    # but at the moment, it is just firmware/dmi stuff.

    dump_file = None
    if testing and prefix:
        dump_file = os.path.join(prefix, FIRMWARE_DUMP_FILENAME)

    if arch in ARCHES_WITHOUT_DMI:
        log.debug("Not looking for DMI info since it is not available on '%s'" % arch)
        firmware_provider_class = NullFirmwareInfoProvider
    else:
        if dmiinfo:
            firmware_provider_class = dmiinfo.DmiFirmwareInfoProvider
        else:
            firmware_provider_class = NullFirmwareInfoProvider

    if dump_file:
        firmware_provider = firmware_provider_class.from_dump_file(dump_file)
    else:
        firmware_provider = firmware_provider_class()

    return firmware_provider
