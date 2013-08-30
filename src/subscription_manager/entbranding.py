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


#  hmm, we can subscribe before we have a product
#       cert installed? Would we need to check
#       on product cert install as well?
import logging

from subscription_manager import injection as inj

log = logging.getLogger('rhsm-app.' + __name__)


class BrandInstaller(object):
    """Install any branding info for a set of entititlement certs."""

    def __init__(self, ent_certs):
        self.ent_certs = ent_certs

        prod_dir = inj.require(inj.PROD_DIR)
        self.installed_products = prod_dir.get_installed_products()

    def install(self):
        branded_certs = self.get_branded_certs()

        if not branded_certs:
            return
        elif len(branded_certs) > 1:
            log.warning("More than one entitlement provided branding information for an installed RHEL product")
            return

        cert, branded_product = branded_certs[0]
        log.info("Entitlement cert %s is providing branding info for product %s" %
                 (cert, branded_product.name))
        self._install_rhel_branding(branded_product.name)

    def get_branded_certs(self):
        branded_cert_products = []
        for cert in self.ent_certs:
            products = cert.products or []
            installed_branded_products = self.get_installed_branded_products(products)

            # this cert does not match any installed branded products
            if not installed_branded_products:
                continue
            # more than one brandable product installed
            elif len(installed_branded_products) > 1:
                log.warning("More than one installed product with RHEL branding information is installed")
                continue
            else:
                branded_cert_products.append((cert, installed_branded_products[0]))
        return branded_cert_products

    def get_installed_branded_products(self, products):
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

    def _install_rhel_branding(self, product_name):
        """Create Brand object and save it."""

        log.info("Updating product branding info for: %s" % product_name)
        brand = Brand(product_name)
        brand.save()


class Brand(object):
    """A brand for a branded product"""
    def __init__(self, brand):
        self.brand_file = BrandFile()
        self.brand = brand

    def save(self):
        brand = self.format_brand(self.brand)
        self.brand_file.write(brand)

    @staticmethod
    def format_brand(brand):
        if not brand.endswith('\n'):
            brand += '\n'

        return brand


class BrandFile(object):
    """The file used for storing product branding info.

    Default is "/var/lib/rhsm/branded_name
    """

    brand_path = "/var/lib/rhsm/branded_name"

    def write(self, brand_info):
        # python 2.5+, woohoo!
        with open(self.brand_path, 'w') as brand_file:
            brand_file.write(brand_info)
