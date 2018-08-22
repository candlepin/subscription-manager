from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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
import yum
from yum.plugins import TYPE_CORE

from subscription_manager import logutil
from subscription_manager.productid import ProductManager, RpmVersion
from subscription_manager.utils import chroot
from subscription_manager.injectioninit import init_dep_injection

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,)

log = logging.getLogger('rhsm-app.' + __name__)


def posttrans_hook(conduit):
    """
    Update product ID certificates.
    """
    # register rpm name for yum history recording
    # yum on 5.7 doesn't have this method, so check for it
    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("subscription-manager")

    try:
        init_dep_injection()
    except ImportError as e:
        conduit.error(3, str(e))
        return

    logutil.init_logger_for_yum()
    # If a tool (it's, e.g., Anaconda and Mock) manages a chroot via
    # 'yum --installroot', we must update certificates in that directory.
    chroot(conduit.getConf().installroot)
    try:
        pm = YumProductManager(conduit._base)
        pm.update_all()
        conduit.info(3, 'Installed products updated.')
    except Exception as e:
        conduit.error(3, str(e))


class YumProductManager(ProductManager):
    def __init__(self, base):
        self.base = base
        ProductManager.__init__(self)

    def update_all(self):
        return self.update(self.get_enabled(),
                           self.get_active(),
                           self.check_version_tracks_repos())

    def get_enabled(self):
        """find yum repos that are enabled"""
        lst = []
        enabled = self.base.repos.listEnabled()

        # skip repo's that we don't have productid info for...
        for repo in enabled:
            try:
                fn = repo.retrieveMD(self.PRODUCTID)
                cert = self._get_cert(fn)
                if cert is None:
                    continue
                lst.append((cert, repo.id))
            except yum.Errors.RepoMDError as e:
                # We have to look in all repos for productids, not just
                # the ones we create, or anaconda doesn't install it.
                self.meta_data_errors.append(repo.id)
            except Exception as e:
                log.warning("Error loading productid metadata for %s." % repo)
                log.exception(e)
                self.meta_data_errors.append(repo.id)

        if self.meta_data_errors:
            log.debug("Unable to load productid metadata for repos: %s",
                      self.meta_data_errors)
        return lst

    # find the list of repo's that provide packages that
    # are actually installed.
    def get_active(self):
        """find yum repos that have packages installed"""

        active = set([])

        # If a package is in a enabled and 'protected' repo

        # This searches all the package sacks in this yum instances
        # package sack, aka all the enabled repos
        packages = self.base.pkgSack.returnPackages()

        for p in packages:
            repo = p.repoid
            # if a pkg is in multiple repo's, this will consider
            # all the repo's with the pkg "active".
            # NOTE: if a package is from a disabled repo, we won't
            # find it with this, because 'packages' won't include it.
            db_pkg = self.base.rpmdb.searchNevra(name=p.name, arch=p.arch)
            # that pkg is not actually installed
            if not db_pkg:
                # Effect of this is that a package that is only
                # available from disabled repos, it is not considered
                # an active package.
                # If none of the packages from a repo are active, then
                # the repo will not be considered active.
                #
                # Note however that packages that are installed, but
                # from an disabled repo, but that are also available
                # from another enabled repo will mark both repos as
                # active. This is why add on repos that include base
                # os packages almost never get marked for product cert
                # deletion. Anything that could have possible come from
                # that repo or be updated with makes the repo 'active'.
                continue

            # The pkg is installed, so the repo it was installed
            # from is considered 'active'
            # yum on 5.7 list everything as "installed" instead
            # of the repo it came from
            if repo in (None, "installed"):
                continue
            active.add(repo)

        return active

    def check_version_tracks_repos(self):
        major, minor, micro = yum.__version_info__
        yum_version = RpmVersion(version="%s.%s.%s" % (major, minor, micro))
        needed_version = RpmVersion(version="3.2.28")
        if yum_version >= needed_version:
            return True
        return False
