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
# on subscription


import logging

log = logging.getLogger(__name__)


class BrandsInstaller(object):
    def __init__(self, ent_certs=None):
        self.ent_certs = ent_certs

        # find brand installers
        self.brand_installers = self._get_brand_installers()

    def _get_brand_installers(self):
        """returns a list or iterable of BrandInstaller(s)"""
        return []

    def install(self):
        for brand_installer in self.brand_installers:
            brand_installer.install()


class BrandInstaller(object):
    """Install branding info for a set of entititlement certs."""

    def __init__(self, ent_certs=None):
        self.ent_certs = ent_certs

        log.debug("BrandInstaller ent_certs:  %s" % [x.serial for x in ent_certs or []])

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
            log.debug("Product branding info does not need to be updated")

    def _get_brand_picker(self):
        raise NotImplementedError

    def _get_current_brand(self):
        raise NotImplementedError

    def _install(self, brand):
        raise NotImplementedError


class BrandPicker(object):
    """Returns the branded name to install.

    Check installed product certs, and the list of entitlement certs
    passed in, and find the correct branded name, if any."""

    def __init__(self, ent_certs=None):
        self.ent_certs = ent_certs

    def get_brand(self):
        raise NotImplementedError


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
        return cls(product.brand_name)

    @staticmethod
    def format_brand(brand):
        if not brand.endswith('\n'):
            brand += '\n'

        return brand


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
            log.error("No brand info file found (%s) " % self.brand_file)
            return

        self.name = self.unformat_brand(brand_info)

    @staticmethod
    def unformat_brand(brand):
        if brand:
            return brand.strip()
        return None


class BrandFile(object):
    """The file used for storing product branding info.

    Default is "/var/lib/rhsm/branded_name
    """

    path = "/var/lib/rhsm/branded_name"

    def write(self, brand_info):
        with open(self.path, 'w') as brand_file:
            brand_file.write(brand_info)

    def read(self):
        with open(self.path, 'r') as brand_file:
            return brand_file.read()

    def __str__(self):
        return "<BrandFile path=%s>" % self.path
