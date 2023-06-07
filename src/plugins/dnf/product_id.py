# Copyright (c) 2015 Red Hat, Inc.
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
from typing import Set

from subscription_manager.productid import ProductManager
from subscription_manager.utils import chroot
from subscription_manager.injectioninit import init_dep_injection
from subscription_manager.i18n import ugettext as _
from rhsm.certificate import create_from_pem

from dnfpluginscore import logger
import dnf
import dnf.base
import dnf.sack
import dnf.exceptions
import errno
import librepo
import os
from rhsm import ourjson as json, logutil

log = logging.getLogger("rhsm-app." + __name__)


class ProductId(dnf.Plugin):
    name = "product-id"

    def __init__(self, base, cli):
        super(ProductId, self).__init__(base, cli)
        self.base = base
        self.cli = cli
        self._enabled_repos = []

    def config(self):
        super(ProductId, self).config()
        # We are adding list of enabled repos to the list to be
        # able to access this list later in transaction hook
        for repo in self.base.repos.iter_enabled():
            self._enabled_repos.append(repo)
            if hasattr(repo, "add_metadata_type_to_download"):
                log.debug("Adding productid metadata type to download for repo: %s" % repo.id)
                repo.add_metadata_type_to_download("productid")

    def transaction(self):
        """
        Update product ID certificates.
        """
        if self.base.transaction is None or len(self.base.transaction) == 0:
            # nothing to update after empty transaction
            return

        try:
            init_dep_injection()
        except ImportError as e:
            log.error(str(e))
            return

        logutil.init_logger_for_yum()
        chroot(self.base.conf.installroot)
        try:
            pm = DnfProductManager(self.base)
            pm.update_all(self._enabled_repos)
            logger.info(_("Installed products updated."))
        except Exception as e:
            log.error(str(e))


class DnfProductManager(ProductManager):
    # Json file containing dictionary. Key is id of repository and
    # value is content of productid certificate of corresponding repository
    PRODUCTID_CACHE_FILE = "/var/lib/rhsm/cache/productid_repo_mapping.json"

    def __init__(self, base):
        self.base = base
        ProductManager.__init__(self)

    def update_all(self, enabled_repos):
        return self.update(self.get_certs_for_enabled_repos(enabled_repos), self.get_active(), True)

    def _download_productid(self, repo, tmpdir):
        if hasattr(repo, "get_metadata_content"):
            log.debug("Getting productid cert for repo: %s" % repo.id)
            content = repo.get_metadata_content("productid")
            log.debug("Content of productid cert: %s" % content)

            filename = repo.get_metadata_path("productid")
            if filename == "":
                filename = None
            if filename is not None:
                log.debug("Filename with productid cert: %s" % filename)
            else:
                log.debug("Unable to load product id cert")
        else:
            handle = repo._handle_new_remote(tmpdir)
            handle.setopt(librepo.LRO_PROGRESSCB, None)
            handle.setopt(librepo.LRO_YUMDLIST, [self.PRODUCTID])
            res = handle.perform()
            filename = res.yum_repo.get(self.PRODUCTID, None)
        return filename

    def get_certs_for_enabled_repos(self, enabled_repos):
        """
        Find enabled repos that are providing product certificates
        """
        lst = []
        cache = self.read_productid_cache()
        if cache is None:
            cache = {}

        # skip repo's that we don't have productid info for...
        for repo in enabled_repos:
            try:
                with dnf.util.tmpdir() as tmpdir:
                    filename = self._download_productid(repo, tmpdir)
                    if filename:
                        cert = self._get_cert(filename)
                        if cert is None:
                            log.debug("Repository %s does not provide cert" % repo.id)
                            continue
                        lst.append((cert, repo.id))
                        cache[repo.id] = cert.pem
                    elif repo.id in cache and cache[repo.id] is not None:
                        cert = create_from_pem(cache[repo.id])
                        lst.append((cert, repo.id))
                    else:
                        # We have to look in all repos for productids, not just
                        # the ones we create, or anaconda doesn't install it.
                        self.meta_data_errors.append(repo.id)
            except Exception as e:
                log.warning("Error loading productid metadata for %s." % repo)
                log.exception(e)
                self.meta_data_errors.append(repo.id)

        if self.meta_data_errors:
            log.debug("Unable to load productid metadata for repos: %s", self.meta_data_errors)

        if len(cache) > 0:
            self.write_productid_cache(cache)

        return lst

    @staticmethod
    def _get_available():
        """Try to get list of available packages"""
        # FIXME: It is not safe to use two base objects in transaction hook.
        # Try to remove it, when dnf support getting list of available
        # packages during "dnf remove".
        with dnf.base.Base() as base:
            base.read_all_repos()
            base.fill_sack(load_system_repo=True, load_available_repos=True)
            available = base.sack.query().available()
        return available

    @staticmethod
    def _write_cache_file(data, file_name: str) -> None:
        """
        Try to write data to cache file
        """
        dir_name = os.path.dirname(file_name)
        cache_dir_exists: bool = False
        if os.path.exists(dir_name):
            cache_dir_exists = True
        else:
            log.debug("Try to create directory: %s" % dir_name)
            try:
                os.makedirs(dir_name)
            except PermissionError as err:
                log.warning(f"Unable to create directory {dir_name}: {err}")
            else:
                cache_dir_exists = True
        if cache_dir_exists is True:
            try:
                with open(file_name, "w") as file:
                    json.dump(data, file, default=json.encode)
            except PermissionError as err:
                log.warning(f"Unable to write to cache file {file_name}: {err}")
            except IOError as err:
                log.error("Unable to write cache: %s" % file_name)
                log.exception(err)
            else:
                log.debug("Wrote cache: %s" % file_name)

    @staticmethod
    def _read_cache_file(file_name: str):
        """
        Try to load data from cache file
        """
        try:
            with open(file_name) as file:
                json_str = file.read()
                data = json.loads(json_str)
            return data
        except PermissionError as err:
            log.warning(f"Unable to open cache file {file_name}: {err}")
        except IOError as err:
            # if the file does not exist we'll create it later
            if err.errno != errno.ENOENT:
                log.warning("Unable to read cache: %s" % file_name)
                log.exception(err)
        except ValueError:
            # ignore json file parse errors, we are going to generate
            # a new as if it didn't exist
            pass
        return None

    def write_productid_cache(self, product_ids):
        self._write_cache_file(product_ids, self.PRODUCTID_CACHE_FILE)

    def read_productid_cache(self):
        return self._read_cache_file(self.PRODUCTID_CACHE_FILE)

    def get_active(self) -> Set[str]:
        """
        Find the list of repos that provide packages that are actually installed.
        """

        # Create new sack to get fresh list of installed packages
        rpmdb_sack = dnf.sack._rpmdb_sack(self.base)
        q_installed = rpmdb_sack.query().installed()

        active = set()
        for pkg in q_installed:
            # FIXME: this protected attribute should be replaced with something
            #  from public DNF API in the future.
            # The public API doesn't provide anything ATM.
            repo_name = pkg._from_repo
            # The repository name includes '@' at the beginning of the string
            active.add(repo_name[1:])

        return active
