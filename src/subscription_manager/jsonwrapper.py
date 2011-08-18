# Copyright (c) 2011 Red Hat, Inc.
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

# This module contains wrappers for JSON returned from the CP server.


class PoolWrapper(object):

    def __init__(self, pool_json):
        self.data = pool_json

    def is_virt_only(self):
        attributes = self.data['attributes']
        virt_only = False
        for attribute in attributes:
            name = attribute['name']
            value = attribute['value']
            if name == "virt_only":
                if value and value.upper() == "TRUE" or value == "1":
                    virt_only = True
                break

        return virt_only

    def get_stacking_id(self):
        product_attrs = self.data['productAttributes']
        for attribute in product_attrs:
            name = attribute['name']
            value = attribute['value']
            if name == "stacking_id" and value:
                return value
        return None