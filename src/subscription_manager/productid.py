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
from gzip import GzipFile
import logging
import os
import six
# for labelCompare
import rpm

from rhsm.certificate import create_from_pem

from subscription_manager.certdirectory import Directory, DEFAULT_PRODUCT_CERT_DIR
from subscription_manager.injection import PLUGIN_MANAGER, require

from subscription_manager import utils
from subscription_manager import repolib

import subscription_manager.injection as inj
from rhsm import ourjson as json

log = logging.getLogger(__name__)


class DatabaseDirectory(Directory):

    PATH = 'var/lib/rhsm'

    def __init__(self):
        super(DatabaseDirectory, self).__init__(self.PATH)
        self.create()


class ProductIdRepoMap(utils.DefaultDict):

    def __init__(self, *args, **kwargs):
        self.default_factory = list


class ProductDatabase(object):

    def __init__(self):
        self.dir = DatabaseDirectory()
        self.content = ProductIdRepoMap()
        self.create()

    def add(self, product, repo):
        self.content[product].append(repo)

    # TODO: need way to delete one prod->repo map
    def delete(self, product):
        try:
            del self.content[product]
        except Exception:
            pass

    def find_repos(self, product):
        return self.content.get(product, None)

    def create(self):
        if not os.path.exists(self.__fn()):
            self.write()

    def read(self):
        f = open(self.__fn())
        try:
            d = json.load(f)
            # munge old format to new if need be
            self.populate_content(d)
        except Exception:
            pass
        f.close()

    def populate_content(self, db_dict):
        """Populate map with info from a productid -> [repoids] map.

        Note this needs to support the old form of
        a {"productid": "repoid"} as well as the
        new form of {"productid: ["repoid1",...]}"""
        for productid, repo_data in list(db_dict.items()):
            if isinstance(repo_data, six.string_types):
                self.content[productid].append(repo_data)
            else:
                self.content[productid] = repo_data

    def write(self):
        f = open(self.__fn(), 'w')
        try:
            json.dump(self.content, f, indent=2, default=json.encode)
        except Exception:
            pass
        f.close()

    def __fn(self):
        return self.dir.abspath('productid.js')


class ComparableMixin(object):
    """Needs compare_keys to be implemented."""
    def _compare(self, keys, method):
        return method(keys[0], keys[1]) if keys else NotImplemented

    def __eq__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s == o)

    def __ne__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s != o)

    def __lt__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s < o)

    def __gt__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s > o)

    def __le__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s <= o)

    def __ge__(self, other):
        return self._compare(self.compare_keys(other), lambda s, o: s >= o)


class RpmVersion(object):
    """Represent the epoch, version, release of a rpm style version.

    This includes the rich comparison methods to support >,<,==,!-
    using rpm's labelCompare.

    See http://fedoraproject.org/wiki/Archive:Tools/RPM/VersionComparison
    for more details of the actual comparison rules.
    """

    # Ordered list of suffixes
    suffixes = ['alpha', 'beta']

    def __init__(self, epoch="0", version="0", release="1"):
        self.epoch = epoch
        self.version = version
        self.release = release

    @property
    def evr(self):
        return (self.epoch, self.version, self.release)

    @property
    def evr_nosuff(self):
        def no_suff(s):
            for suff in self.suffixes:
                if s and s.lower().endswith(suff):
                    return s[:-len(suff)].strip('- ')
            return s
        return (self.epoch, no_suff(self.version), self.release)

    def compare(self, other):
        def ends_with_which(s):
            for idx, suff in enumerate(self.suffixes):
                if s.lower().endswith(suff):
                    return idx
            # Easier compare
            return len(self.suffixes)

        raw_compare = rpm.labelCompare(self.evr, other.evr)
        non_beta_compare = rpm.labelCompare(self.evr_nosuff, other.evr_nosuff)
        if non_beta_compare != raw_compare:
            if ends_with_which(self.version) < ends_with_which(other.version):
                return -1
            return 1
        return raw_compare

    def __lt__(self, other):
        lc = self.compare(other)
        if lc == -1:
            return True
        return False

    def __le__(self, other):
        lc = self.compare(other)
        if lc > 0:
            return False
        return True

    def __eq__(self, other):
        lc = self.compare(other)
        if lc == 0:
            return True
        return False

    def __ne__(self, other):
        lc = self.compare(other)
        if lc != 0:
            return True
        return False


class ComparableProduct(ComparableMixin):
    """A comparable version from a Product. For comparing and sorting Product objects.

    Products are never equals if they do not have the same product id.
    lt and gt for different products are also always false.

    NOTE: This object doesn't make sense to compare Products with different
    Product ID. The results are kind of nonsense for that case.

    This could be extended to compare, either with a more complicated
    version compare, or using other attributes.

    Awesomeos-1.1 > Awesomeos-1.0
    Awesomeos-1.1 != Awesomeos-1.0
    Awesomeos-1.0 < Awesomeos-1.0

    The algorithm used for comparisions is the rpm version compare, as used
    by rpm, yum, etc. Also known as "rpmvercmp" or "labelCompare".

    There aren't any standard product version comparison rules, but the
    rpm rules are pretty flexible, documented, and well understood.
    """
    def __init__(self, product):
        self.product = product

    def compare_keys(self, other):
        """Create a a tuple of RpmVersion objects.

        Create a RpmVersion using the product's version attribute
        as the 'version' attribute for a rpm label tuple. We let the
        epoch default to 0, and the release to 1 for each, so we are
        only comparing the difference in the version attribute.
        """
        if self.product.id == other.product.id:
            return (RpmVersion(version=self.product.version),
                    RpmVersion(version=other.product.version))
        return None

    def __str__(self):
        return "<ComparableProduct id=%s version=%s name=%s product=%s>" % \
                (self.product.id, self.product.version, self.product.name, self.product)


class ComparableProductCert(ComparableMixin):
    """Compareable version of ProductCert.

    Used to determine the "newer" of two ProductCerts. Initially just based
    on a comparison of a ComparableProduct built from the Product, which compares
    using the Product.version field."""

    def __init__(self, product_cert):
        self.product_cert = product_cert
        self.product = self.product_cert.products[0]
        self.comp_product = ComparableProduct(self.product)

    # keys used to compare certificate. For now, just the keys for the
    # Product.version. This could include say, certificate serial or issue date
    def compare_keys(self, other):
        return self.comp_product.compare_keys(other.comp_product)


class ProductId(object):
    def __init__(self, product_cert):
        self.product_cert = product_cert

    # write out the cert
    def install(self):
        """Write out the product cert and run anything
        to trigger based on that"""

        pass

    def remove(self):
        """Delete product cert from the filesystem.

        Subclasses should override this."""
        pass

    # def compare(self, other):   # version check?


class ProductManager(object):
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

    PRODUCTID = 'productid'

    def __init__(self, product_dir=None, product_db=None):

        self.pdir = product_dir
        if not product_dir:
            self.pdir = inj.require(inj.PROD_DIR)

        self.db = product_db
        if not product_db:
            self.db = ProductDatabase()

        self.db.read()
        self.meta_data_errors = []

        self.plugin_manager = require(PLUGIN_MANAGER)

    def find_disabled_repos(self):
        """Find repos disabled in redhat.repo"""
        repo_file = repolib.YumRepoFile()
        repo_file.read()

        disabled_in_redhat_repo = []
        for section in repo_file.sections():
            repo = repo_file.section(section)

            if not utils.is_true_value(repo.get('enabled', '0')):
                disabled_in_redhat_repo.append(repo.id)

        return disabled_in_redhat_repo

    def find_temp_disabled_repos(self, enabled):
        """Find repo from redhat.repo that have been disabled from cli."""
        yum_enabled = [x[1] for x in enabled]

        # Read the redhat.repo file so we can check if any of our
        # repos have been disabled by --disablerepo or another plugin.
        repo_file = repolib.YumRepoFile()
        repo_file.read()

        enabled_in_redhat_repo = []
        for section in repo_file.sections():
            repo = repo_file.section(section)

            if utils.is_true_value(repo.get('enabled', '0')):
                enabled_in_redhat_repo.append(repo.id)

        temp_disabled = []
        for enabled_repo in enabled_in_redhat_repo:
            if enabled_repo not in yum_enabled:
                temp_disabled.append(enabled_repo)

        return temp_disabled

    def update(self, enabled, active, tracks_repos):
        # populate the temp_disabled list so update_remove has it
        # this could likely happen later...
        temp_disabled_repos = self.find_temp_disabled_repos(enabled)

        # only execute this on versions of yum that track
        # which repo a package came from, aka, 3.2.28 and newer
        if tracks_repos:
            # check that we have any repo's enabled
            # and that we have some enabled repo's. Not just
            # that we have packages from repo's that are
            # not active. See #806457
            if enabled and (active or temp_disabled_repos):
                # Check that we have either active repos
                # or that we have temp_disabled_repos
                # See bz 1222627
                self.update_removed(active, temp_disabled_repos)

        # TODO: it would probably be useful to keep track of
        # the state a bit, so we can report what we did
        self.update_installed(enabled, active)

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
        log.debug("Checking for product id certs to install or update.")
        products_to_install = []
        products_to_update_db = []
        products_installed = []

        log.debug("active %s", active)
        log.debug("enabled %s", enabled)
        # track updated product ids seperately in case we want
        # to run plugins
        products_to_update = []

        # enabled means we have a repo, it's enabled=1, it has a productid metadata
        # for it, and we understand that metadata. The cert for that productid
        # may or may not be installed at this point. If it is not installed,
        # we try to install it if there are packages installed from that repo

        # a ProductRepo object? ProductRepo's would have Repos and a
        # ProductCertificate
        #   .delete() -> delete ProductCert and it's entries in ProductDatabase
        #

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

            # this is all workaround for some messed up certs in rhel5
            # are we installing workstation cert?
            if self._is_workstation(p):
                # is the desktop product cert installed?
                for pc in self.pdir.list():
                    if self._is_desktop(pc.products[0]):
                        log.info("removing obsolete desktop cert: %s" % pc.path)
                        # desktop product cert is installed,
                        # delete the desktop product cert
                        pc.delete()
                        self.pdir.refresh()  # must refresh to see the removal of the cert
                        self.db.delete(pc.products[0].id)
                        self.db.write()

            # if installing desktop cert, see if workstation exists on disk and skip
            # the write if so:
            if self._is_desktop(p):
                if self._workstation_cert_exists():
                    log.debug("skipping obsolete desktop cert")
                    continue

            # See if the product cert already exists
            #
            # if we don't find this product cert, install it
            # otherwise, update it if necessary
            #
            # ProductCert.is_installed() -> search pdir for ProductCert
            # ProductCert.install() -> add to install list
            if not self.pdir.find_by_product(prod_hash):
                products_to_install.append((p, cert))
            else:
                installed_product_cert = self.pdir.find_by_product(prod_hash)
                installed_product = installed_product_cert.products[0]
                # NOTE: this compares the Product in the ProductCert, but not
                # the ProductCert itself. We should probably compare the
                # ProductCert itself, which would start out as just comparing
                # it's contained Product with ComparableProduct
                cmp_product_cert = ComparableProductCert(cert)
                cmp_installed_product_cert = ComparableProductCert(installed_product_cert)
                if cmp_product_cert > cmp_installed_product_cert:
                    log.debug("Updating installed product cert for %s %s to %s %s" %
                            (installed_product.name, installed_product.version,
                             p.name, p.version))
                    products_to_update.append((p, cert))
                else:
                    log.debug("Latest version of product cert for %s %s is already installed, not updating" %
                            (p.name, p.version))

            # look up what repo's we know about for that prod id

            # ProductCertDb.install() could do this?
            # look up what repo's we know about for that prod has
            known_repos = self.db.find_repos(prod_hash)

            # ??? What happens for a installed product with no repo info, that
            # we think we should update?
            # known_repos is None means we have no repo info at all
            if known_repos is None or repo not in known_repos:
                products_to_update_db.append((p, repo))

        # see rhbz #977896
        # handle cases where we end up with workstation and desktop certs in
        # the same "transaction".

        # ProductCertDB.cleanup_workstation()
        # if we do this after setting up the lists, we dont need
        # to check per ProductRepo
        products_to_install = self._desktop_workstation_cleanup(products_to_install)
        products_to_update_db = self._desktop_workstation_cleanup(products_to_update_db)
        products_to_update = self._desktop_workstation_cleanup(products_to_update)

        db_updated = False
        for (product, repo) in products_to_update_db:
            # known_repos is None means we have no repo info at all
            log.info("Updating product db with %s -> %s" % (product.id, repo))
            # if we don't have a db entry for that prod->repo mapping, add one
            self.db.add(product.id, repo)
            db_updated = True

        if db_updated:
            self.db.write()

        products_installed = self.install_product_certs(products_to_install)
        products_updated = self.update_product_certs(products_to_update)

        #FIXME: nothing uses the return value here
        return (products_installed, products_updated)

    def install_product_certs(self, product_certs):
        # collect info, then do the needful later, so we can hook
        # up a plugin in between and let it munge these lists, so a plugin
        # could blacklist a product cert for example.
        self.plugin_manager.run('pre_product_id_install', product_list=product_certs)
        # ProductCertDb.install()
        #  -> for each ProductCert:
        #         ProductCert.install()
        #           - if that needs to update the db, do it
        #           - if db needs written, do it
        #   ProductCertDb.list_installed()
        products_installed = self.write_product_certs(product_certs)

        # FIXME: we should include productid db with the conduit here
        log.debug("about to run post_product_id_install")
        self.plugin_manager.run('post_product_id_install', product_list=products_installed)

        return products_installed

    def update_product_certs(self, product_certs):
        self.plugin_manager.run('pre_product_id_update', product_list=product_certs)

        products_updated = self.write_product_certs(product_certs)

        # FIXME: we should include productid db with the conduit here
        log.debug("about to run post_product_id_update")
        self.plugin_manager.run('post_product_id_update', product_list=products_updated)

        return products_updated

    def write_product_certs(self, product_certs):
        products_installed = []
        for (product, cert) in product_certs:
            fn = '%s.pem' % product.id
            path = self.pdir.abspath(fn)
            cert.write(path)
            self.pdir.refresh()
            log.info("Installed product cert %s: %s %s" % (product.id, product.name, cert.path))
            products_installed.append(cert)
        return products_installed

    def _workstation_cert_exists(self):
        for pc in self.pdir.list():
            if self._is_workstation(pc.products[0]):
                return True
        return False

    def _desktop_workstation_cleanup(self, product_cert_list):
        """Remove desktop product if desktop and workstations are marked for install/update"""
        if not self._list_has_workstation_and_desktop_cert(product_cert_list):
            # list doesnt have desktop and workstation, so do nothing
            return product_cert_list

        log.debug("Workstation and Desktop product certs found, removing Desktop cert from list to update")
        return [(product, cert) for (product, cert) in product_cert_list if not self._is_desktop(product)]

    def _list_has_workstation_and_desktop_cert(self, product_cert_list):
        """determine if product cert list has desktop and workstation certs"""
        has_workstation = False
        has_desktop = False
        for product, _product_cert in product_cert_list:
            if self._is_workstation(product):
                has_workstation = True
            if self._is_desktop(product):
                has_desktop = True
        return has_desktop and has_workstation

    # We should only delete productcerts if there are no
    # packages from that repo installed (not "active")
    # and we have the product cert installed.
    def update_removed(self, active, temp_disabled_repos=None):
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
        temp_disabled_repos = temp_disabled_repos or []
        certs_to_delete = []

        log.debug("Checking for product certs to remove. Active include: %s",
                  active)

        disabled_repos = self.find_disabled_repos()

        for cert in self.pdir.list():
            product = cert.products[0]
            prod_hash = product.id

            # Protect all product certificates in /etc/pki/product-default
            # See: BZ: 1526622
            if cert.path.startswith(DEFAULT_PRODUCT_CERT_DIR):
                log.debug('Skipping prod. cert.: %s in protected directory' % cert.path)
                continue

            # FIXME: or if the productid.hs wasn't updated to reflect a new repo
            repos = self.db.find_repos(prod_hash)

            # If productid database does not know about the the product,
            # ie, repo is None (basically, return from a db.content.get(),
            # don't delete the cert because we don't know anything about it
            if repos is None or repos is []:
                # FIXME: this can also mean we need to update the product cert
                #        for prod_hash, since it is installed, but no longer maps to a repo
                # no repos to check, go to next cert
                log.debug('Skipping prod. cert.: %s without repos' % cert.path)
                continue

            delete_product_cert = True
            for repo in repos:
                # if we had errors with the repo or productid metadata
                # we could be very confused here, so do not
                # delete anything. see bz #736424
                if repo in self.meta_data_errors:
                    log.debug("%s has meta-data errors.  Not deleting product cert %s.", repo, prod_hash)
                    delete_product_cert = False

                # do not delete a product cert if the repo[a] associated with it's prod_hash
                # has packages installed.
                if repo in active:
                    log.debug("%s is an active repo. Not deleting product cert %s", repo, prod_hash)
                    delete_product_cert = False

                # If product id maps to a repo that we know is only temporarily
                # disabled, don't delete it.
                if repo in temp_disabled_repos:
                    log.warning("%s is disabled via yum cmdline. Not deleting product cert %s", repo, prod_hash)
                    delete_product_cert = False

                # If product id maps to a repo that we know is disabled, don't delete it.
                if repo in disabled_repos:
                    log.info("%s is disabled. Not deleting product cert %s", repo, prod_hash)
                    delete_product_cert = False

                # is the repo we find here actually active? try harder to find active?

            # for this prod cert/hash, we know what repo[a] it's for, but nothing
            # appears to be installed from the repo[s]
            #
            if delete_product_cert:
                certs_to_delete.append((product, cert))

        # TODO: plugin hook for pre_product_id_delete
        for product, cert in certs_to_delete:
            log.debug("None of the repos for %s are active: %s",
                     product.id,
                     self.db.find_repos(product.id))
            log.info("product cert %s for %s is being deleted" % (product.id, product.id))
            cert.delete()
            self.pdir.refresh()
            # TODO: plugin hook for post_product_id_delete

            # it should be safe to delete it's entry now, we either don't
            # know anything about it's repos, it doesnt have any, or none
            # of the repos are active
            self.db.delete(product.id)
            self.db.write()

    def _get_cert(self, filename):
        if filename.endswith('.gz'):
            f = GzipFile(filename)
        else:
            f = open(filename)
        try:
            pem = f.read()
            if type(pem) == bytes:
                pem = pem.decode('utf-8')
            cert = create_from_pem(pem)
            cert.pem = pem
            return cert
        finally:
            f.close()


if __name__ == '__main__':
    from subscription_manager.injectioninit import init_dep_injection
    init_dep_injection()

    logging.basicConfig(filename='/var/log/rhsm/rhsm.log', level=logging.DEBUG)
    log.debug('productid smoke testing')

    pm = ProductManager()
    pm.update_removed(active=set([]))
