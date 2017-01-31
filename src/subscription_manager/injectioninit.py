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


from subscription_manager.cache import ProductStatusCache, \
    EntitlementStatusCache, OverrideStatusCache, ProfileManager, \
    InstalledProductsManager, PoolTypeCache, ReleaseStatusCache, \
    RhsmIconCache, ContentAccessCache

from subscription_manager.cert_sorter import CertSorter
from subscription_manager.certdirectory import EntitlementDirectory
from subscription_manager.certdirectory import ProductDirectory
from subscription_manager.facts import Facts
from subscription_manager.identity import Identity
from subscription_manager.validity import ValidProductDateRangeCalculator
from subscription_manager.cp_provider import CPProvider
from subscription_manager.plugins import PluginManager
from subscription_manager.lock import ActionLock


def init_dep_injection():
    """
    Initializes the default behaviour for all supported features.

    This needs to be called from any entry-point into subscription manager.
    """
    # Set up consumer identity as a singleton so we don't constantly re-load
    # it from disk. Call reload when anything changes and all references will be
    # updated.
    inj.provide(inj.IDENTITY, Identity, singleton=True)

    inj.provide(inj.PRODUCT_DATE_RANGE_CALCULATOR,
            ValidProductDateRangeCalculator)

    inj.provide(inj.ENT_DIR, EntitlementDirectory, singleton=True)
    inj.provide(inj.PROD_DIR, ProductDirectory, singleton=True)

    # FIXME: find a way to handle exceptions when looking for
    #        attributes of inj (can happen if yum has old inj module,
    #        but runs a new version of injectioninit...)
    inj.provide(inj.ENTITLEMENT_STATUS_CACHE, EntitlementStatusCache, singleton=True)
    inj.provide(inj.RHSM_ICON_CACHE, RhsmIconCache, singleton=True)
    inj.provide(inj.PROD_STATUS_CACHE, ProductStatusCache, singleton=True)
    inj.provide(inj.OVERRIDE_STATUS_CACHE, OverrideStatusCache, singleton=True)
    inj.provide(inj.RELEASE_STATUS_CACHE, ReleaseStatusCache,
                singleton=False)
    inj.provide(inj.CONTENT_ACCESS_CACHE, ContentAccessCache, singleton=True)

    inj.provide(inj.PROFILE_MANAGER, ProfileManager, singleton=True)
    inj.provide(inj.INSTALLED_PRODUCTS_MANAGER, InstalledProductsManager, singleton=True)

    inj.provide(inj.CP_PROVIDER, CPProvider, singleton=True)

    inj.provide(inj.CERT_SORTER, CertSorter, singleton=True)

    # Set up plugin manager as a singleton.
    # FIXME: should we aggressively catch exceptions here? If we can't
    # create a PluginManager we should probably raise an exception all the way up
    inj.provide(inj.PLUGIN_MANAGER, PluginManager, singleton=True)

    inj.provide(inj.POOLTYPE_CACHE, PoolTypeCache, singleton=True)
    inj.provide(inj.ACTION_LOCK, ActionLock)

    # see what happens with non singleton, callable
    inj.provide(inj.FACTS, Facts)

    try:
        # This catch fixes the product-id module on anaconda
        # Anaconda does not have dbus module, which is imported in dbus_interface
        from subscription_manager.dbus_interface import DbusIface
        inj.provide(inj.DBUS_IFACE, DbusIface, singleton=True)
    except ImportError:
        pass
