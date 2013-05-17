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

import gettext
from gzip import GzipFile
import logging
import os
import simplejson as json
import types
import yum

from rhsm.certificate import create_from_pem

from subscription_manager.certdirectory import Directory, ProductDirectory
from subscription_manager import plugins

_ = gettext.gettext
log = logging.getLogger('rhsm-app.' + __name__)


class DatabaseDirectory(Directory):

    PATH = 'var/lib/rhsm'

    def __init__(self):
        super(DatabaseDirectory, self).__init__(self.PATH)
        self.create()


class ProductDatabase:

    def __init__(self):
        self.dir = DatabaseDirectory()
        self.content = {}
        self.create()

    def add(self, product, repo):
        if product not in self.content:
            self.content[product] = []
        # handle existing old format values
        if isinstance(self.content[product], types.StringType):
            self.content[product] = [self.content[product]]
        self.content[product].append(repo)

    def delete(self, product):
        try:
            del self.content[product]
        except Exception:
            pass

    # need way to delete one prod->repo map

    def find_repos(self, product):
        repo_value = self.content.get(product)
        # support the old format as well by
        # listafying if it's just a string value
        if isinstance(repo_value, types.ListType):
            return repo_value
        if repo_value is None:
            return None
        return [repo_value]

    def create(self):
        if not os.path.exists(self.__fn()):
            self.write()

    def read(self):
        f = open(self.__fn())
        try:
            d = json.load(f)
            self.content = d
        except Exception:
            pass
        f.close()

    def write(self):
        f = open(self.__fn(), 'w')
        try:
            json.dump(self.content, f, indent=2)
        except Exception:
            pass
        f.close()

    def __fn(self):
        return self.dir.abspath('productid.js')


class ProductManager:
    """Manager product certs, detecting when they need to be installed, or deleted.

    Note that this class has no knowledge of when it runs, and no nothing of the
    rpm transaction that may have causes it to run. So it only looks at the state
    of installed packages, yum repo states, installed product certs, and the
    product id->repo id mapping db productid.js.

    It finds yum repo's which are enabled.
    It finds repo's which are active. "active" in this case means one or more
      installed packages were installed from that repo. It does this my checking
      the 'repoid' field yum reports for each installed package.

    It removes certs that are no longer needed. If no packages are installed from
      a product (and more specifically, the repo's created from that product), it
      is considered unneeded and removed.

    Args:
        product_dir: a ProductDirectory class (optional)
        product_db: A ProductDatabase class (optional)
    """

    REPO = 'from_repo'
    PRODUCTID = 'productid'

    def __init__(self, product_dir=None, product_db=None):

        self.pdir = product_dir
        if not product_dir:
            self.pdir = ProductDirectory()

        self.db = product_db
        if not product_db:
            self.db = ProductDatabase()

        self.db.read()
        self.meta_data_errors = []

        self.plugin_manager = plugins.get_plugin_manager()

    def update(self, yb):
        if yb is None:
            yb = yum.YumBase()
        enabled = self.get_enabled(yb)
        active = self.get_active(yb)

        # only execute this on versions of yum that track
        # which repo a package came from, aka, 3.2.28 and newer
        if self._check_yum_version_tracks_repos():
            # check that we have any repo's enabled
            # and that we have some enabled repo's. Not just
            # that we have packages from repo's that are
            # not active. See #806457
            if enabled and active:
                self.update_removed(active)

        # TODO: it would probably be useful to keep track of
        # the state a bit, so we can report what we did
        self.update_installed(enabled, active)

    def _check_yum_version_tracks_repos(self):
        major, minor, micro = yum.__version_info__
        if major >= 3 and minor >= 2 and micro >= 28:
            return True
        return False

    def _is_workstation(self, product_cert):
        if product_cert.name == "Red Hat Enterprise Linux Workstation" and \
                "rhel-5-client-workstation" in product_cert.provided_tags and \
                product_cert.version[0] == '5':
            return True
        return False

    def _is_desktop(self, product_cert):
        if product_cert.name == "Red Hat Enterprise Linux Desktop" and \
                "rhel-5-client" in product_cert.provided_tags and \
                product_cert.version[0] == '5':
            return True
        return False

    def update_installed(self, enabled, active):
        """Install product certs for products with enabled and active repos

        If we find a new product cert, we install it to /etc/pki/product
        and update the productid database to show what repo it came from.

        If we already have the product cert, but it now maps to a new or
        different repo, then update productid database with that info.

        It is possible for a single product cert to map to multiple repos.
        If multiple repo's all have the same product cert id metadata, we
        can get into this scenario. The anaconda install is an example of
        this, since the 'anaconda' repo the installer uses has the product
        cert metadata, but so does the corresponding rhel repo we get
        from autosubscribing. In those cases, we track both.

        Args:
            enabled: list of tuples of (product_cert, repo_id)
                     The repo's that are enabled=1 and have product
                     id metadata
            active: a set of names of repos that installed packages were
                    installed from.

        Returns:
             list of product certs that were installed

        Side Effects:
            can delete certs for some odd rhel5 scenarios, where we
            have to obsolete some deprecated certs
        """
        log.debug("Updating installed certificates")
        products_to_install = []
        products_to_update_db = []
        products_installed = []

        # enabled means we have a repo, it's enabled=1, it has a productid metadata
        # for it, and we understand that metadata. The cert for that productid
        # may or may not be installed at this point. If it is not installed,
        # we try to install it if there are packages installed from that repo
        for cert, repo in enabled:
            log.debug("product cert: %s repo: %s" % (cert.products[0].id, repo))

            # nothing from this repo is installed
            #
            # check to see packages from this repo are installed and the repo
            # is considered active
            if repo not in active:
                continue

            # is this the same as v1 ProductCertificate.getProduct() ?
            # assume [0] indexed item is the same item
            p = cert.products[0]
            prod_hash = p.id

            # This is all workaround for some messed up certs in RHEL5
            # Are we installing Workstation cert?
            if self._is_workstation(p):
                # is the Desktop product cert installed?
                for pc in self.pdir.list():
                    if self._is_desktop(pc.products[0]):
                        log.info("Removing obsolete Desktop cert: %s" % pc.path)
                        # Desktop product cert is installed,
                        # delete the Desktop product cert
                        pc.delete()
                        self.pdir.refresh()  # must refresh to see the removal of the cert
                        self.db.delete(pc.products[0].id)
                        self.db.write()

            # If installing Desktop cert, see if Workstation exists on disk and skip
            # the write if so:
            if self._is_desktop(p):
                if self._workstation_cert_exists():
                    log.info("Skipping obsolete Desktop cert")
                    continue

            # See if the product cert already exists, if so no need to write it
            #
            # FIXME: this is where we would check to see if a product cert
            # needs to be updated
            #
            # if we dont find this product cert, install it
            if not self.pdir.find_by_product(prod_hash):
                products_to_install.append((p, cert))

            # look up what repo's we know about for that prod has
            known_repos = self.db.find_repos(prod_hash)

            # known_repos is None means we have no repo info at all
            if known_repos is None or repo not in known_repos:
                products_to_update_db.append((p, repo))

        # collect info, then do the needful later, so we can hook
        # up a plugin in between and let it munge these lists, so a plugin
        # could blacklist a product cert for example.
        # TODO: insert "pre_product_id_install" hook

        for (product, cert) in products_to_install:
            fn = '%s.pem' % product.id
            path = self.pdir.abspath(fn)
            cert.write(path)
            self.pdir.refresh()
            log.info("Installed product cert %s: %s %s" % (product.id, product.name, cert.path))
            products_installed.append(cert)

        db_updated = False
        for (product, repo) in products_to_update_db:
            # known_repos is None means we have no repo info at all
            log.info("Updating product db with %s -> %s" % (product.id, repo))
            # if we don't have a db entry for that prod->repo mapping, add one
            self.db.add(product.id, repo)
            db_updated = True

        if db_updated:
            self.db.write()

        # FIXME: we should include productid db with the conduit here
        log.debug("about to run post_product_id_install")
        self.plugin_manager.run('post_product_id_install', product_list=products_installed)
        #FIXME: nothing uses the return value here
        return products_installed

    def _workstation_cert_exists(self):
        for pc in self.pdir.list():
            if self._is_workstation(pc.products[0]):
                return True
        return False

    def _is_rhel_product_cert(self, product):
        """return true if this is a rhel product cert"""

        # FIXME: if there is a smarter way to detect this is the base os,
        # this would be a good place for it.
        if [tag for tag in product.provided_tags if tag[:4] == 'rhel']:
            # dont delete rhel product certs unless we have a better reason
            # FIXME: will need to handle how to update product certs seperately

            # if any of the tags are "rhel", that's enough
            return True

        return False

    # We should only delete productcerts if there are no
    # packages from that repo installed (not "active")
    # and we have the product cert installed.
    def update_removed(self, active):
        """remove product certs for inactive products

        For each installed product cert, check to see if we still have
        packages installed from the repo the product cert was installed
        from. If not, delete the product cert.

        With a few exceptions:
            1) if the productid db does not know about the product cert,
                do not delete it
            2) if the productid db doesn't know what repo that cert came
                from, do not delete it.
            3) If there were errors reading the repo metadata for any of
                the repos that provide that cert, do not delete it.
            4) If the product cert has providedtags for 'rhel*'

        Args:
            active: a set of repo name strings of the repos that installed
                    packages were installed from
        Side effects:
            deletes certs that need to be deleted
        """
        certs_to_delete = []
        for cert in self.pdir.list():
            p = cert.products[0]
            prod_hash = p.id

            # FIXME: or if the productid.hs wasn't updated to reflect a new repo
            repos = self.db.find_repos(prod_hash)

            delete_product_cert = True

            # this is the core of a fix for rhbz #859197
            #
            # which is a scenario where we have rhel installed, a rhel cert installed,
            # a rhel entitlement, a rhel enabled repo, yet no packages installed from
            # that rhel repo. Aka, a system anaconda installed from a cloned repo
            # perhaps. In that case, all the installed package think they came from
            # that other repo (say, 'anaconda-repo'), so it looks like the rhel repo
            # is not 'active'. So it ends up deleting the product cert for rhel since
            # it appears it is not being used. It is kind of a strange case for the
            # base os product cert, so we hardcode a special case here.
            if self._is_rhel_product_cert(p):
                delete_product_cert = False

            # If productid database does not know about the the product,
            # ie, repo is None (basically, return from a db.content.get(),
            # dont delete the cert because we dont know anything about it
            if repos is None or repos is []:
                # FIXME: this can also mean we need to update the product cert
                #        for prod_hash, since it is installed, but no longer maps to a repo
                delete_product_cert = False
                # no repos to check, go to next cert
                continue

            for repo in repos:
                # if we had errors with the repo or productid metadata
                # we could be very confused here, so do not
                # delete anything. see bz #736424
                if repo in self.meta_data_errors:
                    log.info("%s has meta-data errors.  Not deleting product cert %s." % (repo, prod_hash))
                    delete_product_cert = False

                # do not delete a product cert if the repo[a] associated with it's prod_hash
                # has packages installed.
                if repo in active:
                    delete_product_cert = False

                # other reasons not to delete.
                #  is this a rhel product cert?

                # is the repo we find here actually active? try harder to find active?

            # for this prod cert/hash, we know what repo[a] it's for, but nothing
            # appears to be installed from the repo[s]
            #
            if delete_product_cert:
                certs_to_delete.append((p, cert))

        # TODO: plugin hook for pre_product_id_delete
        for (product, cert) in certs_to_delete:
            log.info("product cert %s for %s is being deleted" % (product.id, product.id))
            cert.delete()
            self.pdir.refresh()
            #TODO: plugin hook for post_product_id_delete

            # it should be safe to delete it's entry now, we either dont
            # know anything about it's repos, it doesnt have any, or none
            # of the repos are active
            self.db.delete(product.id)
            self.db.write()

    # find the list of repo's that provide packages that
    # are actually installed.
    def get_active(self, yb):
        """find yum repos that have packages installed"""

        active = set([])

        packages = yb.pkgSack.returnPackages()
        for p in packages:
            repo = p.repoid

            # if a pkg is in multiple repo's, this will consider
            # all the repo's with the pkg "active".
            db_pkg = yb.rpmdb.searchNevra(name=p.name, arch=p.arch)

            # that pkg is not actually installed
            if not db_pkg:
                continue

            # yum on 5.7 list everything as "installed" instead
            # of the repo it came from
            if repo in (None, "installed"):
                continue
            active.add(repo)
        return active

    def get_enabled(self, yb):
        """find yum repos that are enabled"""
        lst = []
        enabled = yb.repos.listEnabled()

        # skip repo's that we don't have productid info for...
        for repo in enabled:
            try:
                fn = repo.retrieveMD(self.PRODUCTID)
                cert = self._get_cert(fn)
                if cert is None:
                    continue
                lst.append((cert, repo.id))
            except yum.Errors.RepoMDError, e:
                log.warn("Error loading productid metadata for %s." % repo)
                self.meta_data_errors.append(repo.id)
            except Exception, e:
                log.warn("Error loading productid metadata for %s." % repo)
                log.exception(e)
                self.meta_data_errors.append(repo.id)
        return lst

    def _get_cert(self, fn):
        if fn.endswith('.gz'):
            f = GzipFile(fn)
        else:
            f = open(fn)
        try:
            pem = f.read()
            return create_from_pem(pem)
        finally:
            f.close()

if __name__ == '__main__':
    pm = ProductManager()
    pm.update(yb=None)
