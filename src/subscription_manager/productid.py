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

import os
import logging
import simplejson as json
import gettext
import yum
_ = gettext.gettext

from gzip import GzipFile
from rhsm.certificate import create_from_pem
from subscription_manager.certdirectory import Directory, ProductDirectory

from subscription_manager import plugins

log = logging.getLogger('rhsm-app.' + __name__)

import pprint
pp = pprint.pprint


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
        self.content[product].append(repo)

    def delete(self, product):
        try:
            del self.content[product]
        except:
            pass

    # need way to delete one prod->repo map

    def find_repos(self, product):
        return self.content.get(product)

    def create(self):
        if not os.path.exists(self.__fn()):
            self.write()

    def read(self):
        f = open(self.__fn())
        try:
            d = json.load(f)
            self.content = d
        except:
            pass
        f.close()

    def write(self):
        f = open(self.__fn(), 'w')
        try:
            json.dump(self.content, f, indent=2)
        except:
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

        self.plugin_manager = plugins.getPluginManager()

    def update(self, yb):
        if yb is None:
            yb = yum.YumBase()
        enabled = self.get_enabled(yb)
        active = self.get_active(yb)

        print "active", active
        print "enabled", enabled

       # only execute this on versions of yum that track
        # which repo a package came from, aka, 3.2.28 and newer
        if self._check_yum_version_tracks_repos():
            # check that we have any repo's enabled
            # and that we have some enabled repo's. Not just
            # that we have packages from repo's that are
            # not active. See #806457
            if enabled and active:
                self.update_removed(active)

        # FIXME: it would probably be useful to keep track of
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

    # FIXME: any reason we couldn't do this in repolib? populate the
    def update_installed(self, enabled, active):
        log.debug("Updating installed certificates")
        products_installed = []

        # enabled means we have a repo, it's enabled=1, it has a productid metadata
        # for it, and we understand that metadata. The cert for that productid
        # may or may not be installed at this point. If it is not installed,
        # we try to install it if there are packages installed from that repo
        for cert, repo in enabled:
            log.debug("product cert: %s repo: %s" % (cert.products[0].id, repo))

            # nothing from this repo is installed
            #
            # NOTE/FIXME: if the product cert needs to be updated (or
            #             installed) we do not do it if there are no packages installed
            #             from the repo for that product, so we can't update a cert
            #             if we dont have anytong from it installed. I can see cases where
            #             that might not be the right case (a GA rhel with an old product
            #             id for example, where it may be useful to update the cert before
            #             doing any of this.
            #
            #             tl;dr If we enable a repo, but havent installed anything from it,
            #               we dont install the cert OR update productid.js. If we don't
            #               update productid.js, update_remove thinks the repo
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
            # FIXME: if we already have a product cert on disk, we don't
            # update the productid.js db, even if the repo has changed
            #
            # so we can end up with a product cert installed, that the product
            # database thinks points at an old repo, and then update_removed
            # can't find the old repo name in active, and deletes it

            # if we dont find this product cert, install it
            if not self.pdir.findByProduct(prod_hash):
                fn = '%s.pem' % prod_hash
                path = self.pdir.abspath(fn)
                cert.write(path)
                # FIXME: should only need once
                self.pdir.refresh()  # must refresh product dir to see changes
                log.info("Installed product cert: %s %s" % (p.name, cert.path))
                # return associated repo's as well?
                products_installed.append(cert)

            # look up what repo's we know about for that prod has
            known_repos = self.db.find_repos(prod_hash)

            # known_repos is None means we have no repo info at all
            if known_repos is None or repo not in known_repos:
                # if we don't have a db entry for that prod->repo mapping, add one
                self.db.add(prod_hash, repo)
                #FIXME: can do after
                self.db.write()
                # FIXME: do we need to track productid.js updates? for plugin?

        log.debug("about to run post_product_id_install")
        self.plugin_manager.run('post_product_id_install', product_list=products_installed)
        #FIXME: nothing uses the return value here
        return products_installed

    def _workstation_cert_exists(self):
        for pc in self.pdir.list():
            if self._is_workstation(pc.products[0]):
                return True
        return False

    # We should only delete productcerts if there are no
    # packages from that repo installed (not "active")
    # and we have the product cert installed.
    def update_removed(self, active):
        for cert in self.pdir.list():
            p = cert.products[0]
            prod_hash = p.id

            # FIXME: or if the productid.hs wasn't updated to reflect a new repo
            repos = self.db.find_repos(prod_hash)

            delete_product_cert = True
            # If productid database does not know about the the product,
            # ie, repo is None (basically, return from a db.content.get(),
            # dont delete the cert because we dont know anything about it
            if repos is None or repos is []:
                # FIXME: this can also mean we need to update the product cert
                #        for prod_hash, since it is installed, but no longer maps to a repo
                delete_product_cert = False
                # no repos to check, go to next cert
                continue

            print "REPOS", repos
            for repo in repos:
                # if we had errors with the repo or productid metadata
                # we could be very confused here, so do not
                # delete anything. see bz #736424
                if repo in self.meta_data_errors:
                    log.info("%s has meta-data errors.  Not deleting product cert %s." % (repo, prod_hash))
                    delete_product_cert = False

                print "ur: active", active, "repo", repo, repo in active

                # do not delete a product cert if the repo[a] associated with it's prod_hash
                # has packages installed
                if repo in active:
                    delete_product_cert = False

                # other reasons not to delete.
                #  is this a rhel product cert?

                # is the repo we find here actually active? try harder to find active?

            # for this prod cert/hash, we know what repo[a] it's for, but nothing
            # appears to be installed from the repo[s]
            #
            if delete_product_cert:
                # TODO/FIXME: plugin call on cert delete specifically?
                log.info("product cert %s for %s is being deleted" % (prod_hash, p.name))
                cert.delete()
                self.pdir.refresh()

                # it should be safe to delete it's entry now, we either dont
                # know anything about it's repos, it doesnt have any, or none
                # of the repos are active
                self.db.delete(prod_hash)
                self.db.write()

    # find the list of repo's that provide packages that
    # are actually installed.
    def get_active(self, yb):
        """find yum repos that have packages installed"""

        # possibilities... detect rhel via -release pkg and always include
        # it in active.
        #
        # - just dont ever delete rhel unless we are replacing it
        #
        # hardcode whitelist for update_remove to check product cert
        # info against
        #
        # we could not remove product certs in no active scenario
        #
        # we could update productid db before we do this, based on
        # current yum repos, aka, update_installed first, then update_removed
        #
        # support multiple repos per product id, and make sure we update that
        # info
        active = set()

        packages = yb.pkgSack.returnPackages()
        for p in packages:
            repo = p.repoid

            # if a pkg is in multiple repo's, this will consider
            # all the repo's with the pkg "active".
            db_pkg = yb.rpmdb.searchNevra(name=p.name, arch=p.arch)

            # package was installed from a repo that is not currently
            # enabled (ala, 'anaconda' post install), if so, check
            # to see if the package is also available from an enabled
            # repo ('foo'). If it is, consider 'foo' active as well,
            # even if no package was directly installed from 'foo'.
            # (in this case, the package also lives in 'foo', so consider
            # it active as well)
            #if p.repoid not in enabled:
            #other_repos = self.find_enabled_repos_for_package(p)
            #pp(other_repos)

            # here, for anaconda repo installed packages, we ask yum
            # and it claims the package came from only anaconda, even if
            # it is potentially from other repos.
            #
            # should we be checking to see if the package is also in any
            # enabled repo's?

            # ugh, for added weirdness, at least one system it seems
            # like repoid=anaconda may just be a 'until some other package
            # is installed thing'

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
