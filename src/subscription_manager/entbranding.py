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


from subscription_manager.certdirectory import Path


class BrandFile(object):
    """The file used for storing product branding info.

    Default is "/var/lib/rhsm/branded_name
    """
    PATH = "/var/lib/rhsm/branded_name"

    @classmethod
    def brand_path(cls):
        return Path.abs(cls.PATH)

    def read(self):
        brand_info = ''
        with open(self.brand_path()) as brand_file:
            brand_info = brand_file.read()

        return brand_info

    def write(self, brand_info):
        self._write(self.brand_path(), brand_info)

    def _write(self, path, brand_info):

        # python 2.5+, woohoo!
        with open(path, 'w') as brand_file:
            brand_file.write(brand_info)

        # set perms?


class Brand(object):
    """A brand for a branded product"""
    def __init__(self, brand):
        self.brand_file = BrandFile()
        self.brand = brand

    def save(self):
        self.brand_file.write(self.brand)
