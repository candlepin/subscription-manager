#
# Copyright (c) 2011 Red Hat, Inc.
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
import rpm


class InvalidProfileType(Exception):
    """
    Thrown when attempting to get a profile of an unsupported type.
    """
    pass


class Package(object):
    """
    Represents a package installed on the system.
    """
    def __init__(self, name, version, release, arch, epoch=0, vendor=None):
        self.name = name
        self.version = version
        self.release = release
        self.arch = arch
        self.epoch = epoch
        self.vendor = vendor

    def to_dict(self):
        """ Returns a dict representation of this packages info. """
        return {
                'name': self.name,
                'version': self.version,
                'release': self.release,
                'arch': self.arch,
                'epoch': self.epoch,
                'vendor': self.vendor,
        }


class RPMProfile(object):

    def __init__(self):
        ts = rpm.TransactionSet()
        ts.setVSFlags(-1)
        installed = ts.dbMatch()
        self.packages = self.__accumulateProfile(installed)

    def __accumulateProfile(self, rpm_header_list):
        """
        Accumulates list of installed rpm info
        @param rpm_header_list: list of rpm headers
        @type rpm_header_list: list
        @return: list of package info dicts
        @rtype: list
        """

        pkg_list = []
        for h in rpm_header_list:
            if h['name'] == "gpg-pubkey":
                #dbMatch includes imported gpg keys as well
                # skip these for now as there isnt compelling
                # reason for server to know this info
                continue
            info = {
                'name': h['name'],
                'version': h['version'],
                'release': h['release'],
                'epoch': h['epoch'] or 0,
                'arch': h['arch'],
                'vendor': h['vendor'] or None,
            }
            pkg_list.append(Package(
                name=h['name'],
                version=h['version'],
                release=h['release'],
                arch=h['arch'],
                epoch=h['epoch'] or 0,
                vendor=h['vendor'] or None
            ))
        return pkg_list

    def collect(self):
        """
        Returns a list of dicts containing the package info.

        See 'packages' member on this object for a list of actual objects.

        @return : list of package info dicts
        @rtype: list
        """
        pkg_dicts = []
        for pkg in self.packages:
            pkg_dicts.append(pkg.to_dict())
        return pkg_dicts


def get_profile(profile_type):
    """
    Returns an instance of a Profile object
    @param type: profile type
    @type type: string
    Returns an instance of a Profile object
    """
    if profile_type not in PROFILE_MAP:
        raise InvalidProfileType('Could not find profile for type [%s]', profile_type)
    profile = PROFILE_MAP[profile_type]()
    return profile


# Profile types we support:
PROFILE_MAP = {
    "rpm": RPMProfile,
}

