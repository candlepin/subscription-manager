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
# on subscription


import logging

from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class BrandsInstaller(object):
    def __init__(self, ent_certs):
        self.ent_certs = ent_certs

        # find brand installers
        self.brand_installers = self._get_brand_installers()

    def _get_brand_installers(self):
        brand_installers = []

        # only one brand installer at the moment
        brand_installer = BrandInstaller(self.ent_certs)
        brand_installers.append(brand_installer)

        return brand_installers

    def install(self):
        for brand_installer in self.brand_installers:
            brand_installer.install()


class BrandInstaller(object):
    """Install branding info for a set of entititlement certs."""

    def __init__(self, ent_certs):
        self.ent_certs = ent_certs

        log.debug("BrandInstaller ent_certs:  %s" % [x.serial for x in ent_certs])


    def install(self):
        """Create a Brand object if needed, and save it."""

        brand_picker = self._get_brand_picker()
        new_brand = brand_picker.get_brand()

        # no branded name info to install
        if not new_brand:
            return

        current_brand = self._get_current_brand()

        log.debug("Current branded name info, if any: %s" % current_brand.name)
        log.debug("Fresh ent cert has branded product info: %s" % new_brand.name)

        if current_brand.is_outdated_by(new_brand):
            self._install(new_brand)
        else:
            log.info("Product branding info does not need to be updated")

    def _get_brand_picker(self):
        raise NotImplementedError

    def _get_current_brand(self):
        raise NotImplementedError

    def _install(self, brand):
        raise NotImplementedError


def RHELBrandInstaller(BrandInstaller):
    def _get_brand_picker(self):
        return RHELBrandPicker(self.ent_certs)

    def _get_current_brand(self):
        return RHELCurrentBrand()

    def _install(self, brand):
        log.info("Updating product branding info for: %s" % brand.name)
        brand.save()


class BrandPicker(object):
    """Returns the branded name to install.

    Check installed product certs, and the list of entitlement certs
    passed in, and find the correct branded name, if any."""

    def __init__(self, ent_certs):
        self.ent_certs = ent_certs

        prod_dir = inj.require(inj.PROD_DIR)
        self.installed_products = prod_dir.get_installed_products()

    def get_brand(self):
        raise NotImplementedError


class RHELBrandPicker(BrandPicker):
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
        for cert, product in branded_certs:
            # uniq on product id and product name
            branded_name_set.add(product.name)

        log.debug("branded_name_set: %s" % branded_name_set)

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
                            branded_cert[1].id, branded_cert[1].name))
            return None

    def _get_branded_cert_products(self):
        branded_cert_products = []
        for cert in self.ent_certs:
            products = cert.products or []
            installed_branded_products = self._get_installed_branded_products(products)

            # this cert does not match any installed branded products
            if not installed_branded_products:
                continue

            # more than one brandable product installed
            if len(installed_branded_products) > 1:
                log.warning("More than one installed product with RHEL brand information is installed")
                for installed_branded_product in installed_branded_products:
                    log.info("Entitlement cert %s is providing brand info for product %s" %
                             (cert, installed_branded_product))
                continue
            else:
                log.debug("installed_branded_products %s" % installed_branded_products)
                installed_branded_product = installed_branded_products[0]
                branded_cert_products.append((cert, installed_branded_product))

        log.debug("%s entitlement certs with brand info found" % len(branded_cert_products))

        return branded_cert_products

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
        if not hasattr(product, 'os'):
            return False
        elif product.os != 'OS':
            return False

        if not product.name:
            return False

        return True


class Brand(object):
    """Base class for Brand objects."""

    name = None

    # could potentially be a __lt__ etc, though there is some
    # oddness in the compares are not symetric for the empty
    # cases (ie, we update nothing with something,etc)
    def is_outdated_by(self, new_brand):
        """If a Brand should be replaced with new_brand."""
        if not self.name:
            return True

        # prevent empty branded_name
        if not new_brand.name:
            return False

        # Don't install new branded_name if it's the same to prevent
        # churn
        return new_brand.name != self.name


class ProductBrand(Brand):
    """A brand for a branded product"""
    def __init__(self, name):
        self.brand_file = self._get_brand_file()
        self.name = name

    def _get_brand_file(self):
        return BrandFile()

    def save(self):
        brand = self.format_brand(self.name)
        self.brand_file.write(brand)

    @classmethod
    def from_product(cls, product):
        return cls(product.name)

    @staticmethod
    def format_brand(brand):
        if not brand.endswith('\n'):
            brand += '\n'

        return brand


class RHELProductBrand(ProductBrand):
    def _get_brand_file(self):
        return RHELBrandFile()


class CurrentBrand(Brand):
    """The currently installed brand"""
    def __init__(self):
        self.brand_file = self._get_brand_file()
        self.load()

    def _get_brand_file(self):
        return BrandFile()

    def load(self):
        try:
            brand_info = self.brand_file.read()
        except IOError:
            log.info("No brand info file found (%s) " % self.brand_file)
            return

        self.name = self.unformat_brand(brand_info)

    @staticmethod
    def unformat_brand(brand):
        if brand:
            return brand.strip()
        return None


class RHELCurrentBrand(CurrentBrand):
    def _get_brand_file(self):
        return RHELBrandFile()


class BrandFile(object):
    """The file used for storing product branding info.

    Default is "/var/lib/rhsm/branded_name
    """

    path = "/var/lib/rhsm/branded_name"

    def write(self, brand_info):
        with open(self.path, 'w') as brand_file:
            brand_file.write(brand_info)

    def read(self):
        brand_info = None
        with open(self.path, 'r') as brand_file:
            brand_info = brand_file.read()
        return brand_info

    def __str__(self):
        return "<BrandFile path=%s>" % self.path


class RHELBrandFile(BrandFile):
    path = "/var/lib/rhsm/branded_name"

    def __str__(self):
        return "<BrandFile path=%s>" % self.path
