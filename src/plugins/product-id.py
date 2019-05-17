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


def postverifytrans_hook(conduit):
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

    def get_active(self):
        """
        find the list of repo's that provide packages that are actually installed
        """

        active = set([])

        installed_packages = self.base.rpmdb.returnPackages()
        for pkg in installed_packages:
            try:
                # pkg.repoid contains only "installed" string not valid origin
                # of repository
                repo = pkg.yumdb_info.from_repo
            except AttributeError:
                # When package is installed from local RPM and not from repository
                # then yumdb_info doesn't have from_source attribute in some case
                log.debug('Unable to get repo for package: %s' % pkg.name)
            else:
                # When repo name begins with '/', then it means that RPM was installed
                # from local .rpm file. Thus productid certificate cannot exist for such
                # origin of RPM
                if repo[0] == '/':
                    log.debug('Not adding local source of RPM: %s to set of active repos' % repo)
                    continue
                active.add(repo)

        return active

    @staticmethod
    def check_version_tracks_repos():
        major, minor, micro = yum.__version_info__
        yum_version = RpmVersion(version="%s.%s.%s" % (major, minor, micro))
        needed_version = RpmVersion(version="3.2.28")
        if yum_version >= needed_version:
            return True
        return False
