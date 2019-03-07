from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 - 2012 Red Hat, Inc.
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
import logging

import rpm
import six
import os.path
from rhsm import ourjson as json
from iniparse import SafeConfigParser

try:
    import dnf
except ImportError:
    dnf = None

try:
    import libdnf
except ImportError:
    libdnf = None

try:
    import yum
except ImportError:
    yum = None


REPOSITORY_PATH = "/etc/yum.repos.d/redhat.repo"

log = logging.getLogger(__name__)


class InvalidProfileType(Exception):
    """
    Thrown when attempting to get a profile of an unsupported type.
    """
    pass


class ModulesProfile(object):

    def __init__(self):
        self.content = self.__generate()

    def __str__(self):
        return str(self.content)

    def __eq__(self, other):
        return self.content == other.content

    @staticmethod
    def _uniquify(module_list):
        ret = {}
        for module in module_list:
            key = (module["name"], module["stream"], module["version"], module["context"], module["arch"])
            ret[key] = module
        return list(ret.values())

    @staticmethod
    def __generate():
        module_list = []
        if dnf is not None and libdnf is not None:
            base = dnf.Base()
            base.read_all_repos()
            base.fill_sack()
            # FIXME: DNF doesn't provide public API for modulemd
            try:
                modules = base._moduleContainer
            except AttributeError:
                log.warn("DNF does not provide modulemd functionality")
                return []
            all_module_list = modules.getModulePackages()

            for module_pkg in all_module_list:
                status = "unknown"
                if modules.isEnabled(module_pkg.getName(), module_pkg.getStream()):
                    status = "enabled"
                elif modules.isDisabled(module_pkg.getName()):
                    status = "disabled"
                installed_profiles = []
                if status == "enabled":
                    installed_profiles = modules.getInstalledProfiles(module_pkg.getName())
                module_list.append({
                    "name": module_pkg.getName(),
                    "stream": module_pkg.getStream(),
                    "version": module_pkg.getVersion(),
                    "context": module_pkg.getContext(),
                    "arch": module_pkg.getArch(),
                    "profiles": [profile.getName() for profile in module_pkg.getProfiles()],
                    "installed_profiles": installed_profiles,
                    "status": status
                })

        return ModulesProfile._uniquify(module_list)

    def collect(self):
        """
        Gather list of modules reported to candlepin server
        :return: List of modules
        """
        return self.content


class EnabledRepos(object):
    def __generate(self):
        if not os.path.exists(self.repofile):
            return []

        config = SafeConfigParser()
        config.read(self.repofile)
        enabled_sections = [section for section in config.sections() if config.getboolean(section, "enabled")]
        enabled_repos = []
        for section in enabled_sections:
            try:
                enabled_repos.append(
                    {
                        "repositoryid": section,
                        "baseurl": [self._replace_vars(config.get(section, "baseurl"))]
                    }
                )
            except ImportError:
                break
        return enabled_repos

    def __init__(self, repo_file):
        """
        :param path: A .repo file path used to filter the report.
        :type path: str
        """
        self.repofile = repo_file
        self.content = self.__generate()

    def __str__(self):
        return str(self.content)

    def _replace_vars(self, repo_url):
        """
        returns a string with "$basearch" and "$releasever" replaced.

        :param repo_url: a repo URL that you want to replace $basearch and $releasever in.
        :type path: str
        """
        mappings = self._obtain_mappings()
        return repo_url.replace('$releasever', mappings['releasever']).replace('$basearch', mappings['basearch'])

    def _obtain_mappings(self):
        """
        returns a hash with "basearch" and "releasever" set. This will try dnf first, and them yum if dnf is
        not installed.
        """
        if dnf is not None:
            return self._obtain_mappings_dnf()
        elif yum is not None:
            return self._obtain_mappings_yum()
        else:
            log.error('Unable to load module for any supported package manager (dnf, yum).')
            raise ImportError

    def _obtain_mappings_dnf(self):
        db = dnf.dnf.Base()
        return {'releasever': db.conf.substitutions['releasever'], 'basearch': db.conf.substitutions['basearch']}

    def _obtain_mappings_yum(self):
        yb = yum.YumBase()
        return {'releasever': yb.conf.yumvar['releasever'], 'basearch': yb.conf.yumvar['basearch']}


class EnabledReposProfile(object):
    """
    Collect information about enabled repositories
    """

    def __init__(self, repo_file=REPOSITORY_PATH):
        self._enabled_repos = EnabledRepos(repo_file)

    def __eq__(self, other):
        return self._enabled_repos.content == other._enabled_repos.content

    def collect(self):
        """
        Gather list of enabled repositories
        :return: List of enabled repositories
        """
        return self._enabled_repos.content


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
                'name': self._normalize_string(self.name),
                'version': self._normalize_string(self.version),
                'release': self._normalize_string(self.release),
                'arch': self._normalize_string(self.arch),
                'epoch': self._normalize_string(self.epoch),
                'vendor': self._normalize_string(self.vendor),  # bz1519512 handle vendors that aren't utf-8
        }

    def __eq__(self, other):
        """
        Compare one profile to another to determine if anything has changed.
        """
        if not isinstance(self, type(other)):
            return False

        if self.name == other.name and \
                self.version == other.version and \
                self.release == other.release and \
                self.arch == other.arch and \
                self.epoch == other.epoch and \
                self._normalize_string(self.vendor) == self._normalize_string(other.vendor):
            return True

        return False

    def __str__(self):
        return "<Package: %s %s %s>" % (self.name, self.version, self.release)

    # added in support of bz1519512, bz1543639
    @staticmethod
    def _normalize_string(value):
        if type(value) is six.binary_type:
            return value.decode('utf-8', 'replace')
        return value


class RPMProfile(object):

    def __init__(self, from_file=None):
        """
        Load the RPM package profile from a given file, or from rpm itself.

        NOTE: from_file is a file descriptor, not a file name.
        """
        self.packages = []
        if from_file:
            log.debug("Loading RPM profile from file: %s" % from_file.name)
            json_buffer = from_file.read()
            pkg_dicts = json.loads(json_buffer)
            for pkg_dict in pkg_dicts:
                self.packages.append(Package(
                    name=pkg_dict['name'],
                    version=pkg_dict['version'],
                    release=pkg_dict['release'],
                    arch=pkg_dict['arch'],
                    epoch=pkg_dict['epoch'],
                    vendor=pkg_dict['vendor']
                ))
        else:
            log.debug("Loading current RPM profile.")
            ts = rpm.TransactionSet()
            ts.setVSFlags(-1)
            installed = ts.dbMatch()
            self.packages = self._accumulate_profile(installed)

    @staticmethod
    def _accumulate_profile(rpm_header_list):
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
                # dbMatch includes imported gpg keys as well
                # skip these for now as there isn't compelling
                # reason for server to know this info
                continue
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

    def __eq__(self, other):
        """
        Compare one profile to another to determine if anything has changed.
        """
        if not isinstance(self, type(other)):
            return False

        # Quickly check if we have a different number of packages for an
        # easy answer before we start checking everything:
        if len(self.packages) != len(other.packages):
            return False

        for pkg in self.packages:
            if pkg not in other.packages:
                return False

        return True


def get_profile(profile_type):
    """
    Returns an instance of a Profile object
    @param profile_type: profile type
    @type profile_type: string
    Returns an instance of a Profile object
    """
    if profile_type not in PROFILE_MAP:
        raise InvalidProfileType('Could not find profile for type [%s]', profile_type)
    profile = PROFILE_MAP[profile_type]()
    return profile


# Profile types we support:
PROFILE_MAP = {
    "rpm": RPMProfile,
    "enabled_repos": EnabledReposProfile,
    "modulemd": ModulesProfile
}
