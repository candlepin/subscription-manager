# Copyright (c) 2013 Red Hat, Inc.
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

import subscription_manager.injection as inj

from subscription_manager.cache import ProductStatusCache, StatusCache
from subscription_manager.cert_sorter import CertSorter
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.certdirectory import ProductDirectory
from subscription_manager.identity import Identity
from subscription_manager.validity import ValidProductDateRangeCalculator


def init_dep_injection():
    """
    Initializes the default behaviour for all supported features.

    This needs to be called from any entry-point into subscription manager.
    """
    # Set up consumer identity as a singleton so we don't constantly re-load
    # it from disk. Call reload when anything changes and all references will be
    # updated.
    inj.provide(inj.IDENTITY, Identity())
    inj.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR,
            ValidProductDateRangeCalculator)

    # TODO: singletons possible?
    inj.provide(inj.ENT_DIR, EntitlementDirectory)
    inj.provide(inj.PROD_DIR, ProductDirectory)

    inj.provide(inj.STATUS_CACHE, StatusCache)
    inj.provide(inj.PROD_STATUS_CACHE, ProductStatusCache)

    # Must come after ent dir, prod dir, and identity
    inj.provide(inj.CERT_SORTER, CertSorter(lazy_load=True))
