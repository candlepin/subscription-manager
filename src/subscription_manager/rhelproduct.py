from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2014 Red Hat, Inc.
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
#
# RHEL product specific code
#

import re


# NOTE: This class compares a Product that could be from a ProductCertificate
#       or from an Entitlement. Product's from Entitlements may include a
#       brand_type attribute. A Product that represents a RHEL base os
#       may or may not be a RHEL "branded" Product. See rhelentbranding for
#       code that handles finding and comparing RHEL "branded" Product objects.
#
class RHELProductMatcher(object):
    """Check a Product object to see if it is a RHEL product.

    Compares the provided tags to see if any provide 'rhel-VERSION'.
    """
    def __init__(self, product=None):
        self.product = product
        # Match "rhel-6" or "rhel-11" or "rhel-alt-7" (bz1510024)
        # but not "rhel-6-server" or "rhel-6-server-highavailabilty"
        # NOTE: we considered rhel(-[\w\d]+)?-\d+$ but decided against it
        # due to possibility of unintentional matches
        self.pattern = "rhel(-alt)?-\d+$|rhel-5-workstation$"

    def is_rhel(self):
        """return true if this is a rhel product cert"""

        return any([re.match(self.pattern, tag)
                    for tag in self.product.provided_tags])
