from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
#
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
# module for updating product branding info
# on subscription, RHEL specific implementation

import logging

from subscription_manager import injection as inj
from subscription_manager import entbranding

log = logging.getLogger(__name__)


class RHELBrandsInstaller(entbranding.BrandsInstaller):
    """RHEL specific impl of BrandsInstaller.

    Currently just the RHELBrandInstaller."""
    def _get_brand_installers(self):
        return [RHELBrandInstaller(self.ent_certs)]


class RHELBrandInstaller(entbranding.BrandInstaller):
    def _get_brand_picker(self):
        return RHELBrandPicker(self.ent_certs)

    def _get_current_brand(self):
        return RHELCurrentBrand()

    def _install(self, brand):
        log.debug("Updating product branding info for: %s" % brand.name)
        brand.save()


class RHELBrandPicker(entbranding.BrandPicker):
    def __init__(self, ent_certs=None):
        super(RHELBrandPicker, self).__init__(ent_certs=ent_certs)

        prod_dir = inj.require(inj.PROD_DIR)
        self.installed_products = prod_dir.get_installed_products()

    def get_brand(self):
        branded_cert_product = self._get_branded_cert_product()

        if not branded_cert_product:
            return None

        branded_product = branded_cert_product[1]
        return RHELProductBrand.from_product(branded_product)

    def _get_branded_cert_product(self):
        """Given a list of ent certs providing product branding, return one.

        If we can collapse them into one, do it. Otherwise, return nothing
        and log errors."""

        branded_certs = self._get_branded_cert_products()

        if not branded_certs:
            return None

        # Try to find cases where multiple ent certs provide the same branding
        # information. This can happen for say, two similar ent certs that
        # overlap at the moment.

        # There is potentially more than cert providing branding info, see if they are for the
        # same product, with the same branded name.

        branded_name_set = set([])
        for _cert, product in branded_certs:
            # uniq on product id and product name
            branded_name_set.add(product.brand_name)

        if len(branded_name_set) == 1:
            # all the ent certs provide the same branding info,
            # so return the first one
            return branded_certs[0]
        else:
            # note product_name_set should never be empty here, since we check
            # for emtpty branded_certs
            log.warning("More than one entitlement provided branded name information for an installed RHEL product")
            for branded_cert in branded_certs:
                log.debug("Entitlement cert %s (%s) provided branded name information for (%s, %s)" %
                            (branded_cert[0].serial, branded_cert[0].order.name,
                            branded_cert[1].id, branded_cert[1].brand_name))
            return None

    def _get_branded_cert_products(self):
        branded_cert_products = []
        for cert in self._get_ent_certs():
            products = cert.products or []
            installed_branded_products = self._get_installed_branded_products(products)

            # this cert does not match any installed branded products
            if not installed_branded_products:
                continue

            # more than one brandable product installed
            if len(installed_branded_products) > 1:
                log.warning("More than one installed product with RHEL brand information is installed")
                for installed_branded_product in installed_branded_products:
                    log.debug("Entitlement cert %s is providing brand info for product %s" %
                             (cert, installed_branded_product))
                continue
            else:
                installed_branded_product = installed_branded_products[0]
                log.debug("Installed branded product: %s" % installed_branded_product)
                branded_cert_products.append((cert, installed_branded_product))

        log.debug("%s entitlement certs with brand info found" % len(branded_cert_products))

        return branded_cert_products

    def _get_ent_certs(self):
        """Returns contents of injected ENT_DIR, or self.ent_dir if set"""
        if self.ent_certs:
            return self.ent_certs
        ent_dir = inj.require(inj.ENT_DIR)
        ent_dir.refresh()
        return ent_dir.list_valid()

    def _get_installed_branded_products(self, products):
        branded_products = []

        for product in products:
            # could support other types of branded products
            if not self._is_rhel_branded_product(product):
                continue

            if not self._is_installed_rhel_branded_product(product):
                continue

            branded_products.append(product)

        return branded_products

    def _is_installed_rhel_branded_product(self, product):
        return product.id in self.installed_products

    def _is_rhel_branded_product(self, product):
        if not hasattr(product, 'brand_type'):
            return False
        elif product.brand_type != 'OS':
            return False

        if not hasattr(product, 'brand_name'):
            return False

        if not product.brand_name:
            return False

        return True


class RHELProductBrand(entbranding.ProductBrand):
    def _get_brand_file(self):
        return RHELBrandFile()


class RHELCurrentBrand(entbranding.CurrentBrand):
    def _get_brand_file(self):
        return RHELBrandFile()


class RHELBrandFile(entbranding.BrandFile):
    path = "/var/lib/rhsm/branded_name"

    def __str__(self):
        return "<BrandFile path=%s>" % self.path
