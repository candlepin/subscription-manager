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

import types

# Supported Features:
IDENTITY = "IDENTITY"
CERT_SORTER = "CERT_SORTER"
PRODUCT_DATE_RANGE_CALCULATOR = "PRODUCT_DATE_RANGE_CALCULATOR"
ENT_DIR = "ENT_DIR"
PROD_DIR = "PROD_DIR"
RHSM_ICON_CACHE = "RHSM_ICON_CACHE"
ENTITLEMENT_STATUS_CACHE = "ENTITLEMENT_STATUS_CACHE"
PROD_STATUS_CACHE = "PROD_STATUS_CACHE"
OVERRIDE_STATUS_CACHE = "OVERRIDE_STATUS_CACHE"
CP_PROVIDER = "CP_PROVIDER"
PLUGIN_MANAGER = "PLUGIN_MANAGER"
DBUS_IFACE = "DBUS_IFACE"
POOLTYPE_CACHE = "POOLTYPE_CACHE"
ACTION_LOCK = "ACTION_LOCK"
FACTS = "FACTS"
PROFILE_MANAGER = "PROFILE_MANAGER"
INSTALLED_PRODUCTS_MANAGER = "INSTALLED_PRODUCTS_MANAGER"
RELEASE_STATUS_CACHE = "RELEASE_STATUS_CACHE"
CONTENT_ACCESS_CACHE = "CONTENT_ACCESS_CACHE"


class FeatureBroker:
    """
    Tracks all configured features.

    Can track both objects to be created on the fly, and singleton's only
    created once throughout the application.

    Do not use this class directly, rather the global instance created below.
    """
    def __init__(self):
        self.providers = {}

    def provide(self, feature, provider):
        """
        Provide an implementation for a feature.

        Can pass a callable you wish to be called on every invocation.

        Can also pass an actual instance which will be returned on every
        invocation. (i.e. pass an actual instance if you want a "singleton".
        """
        self.providers[feature] = provider

    def require(self, feature, *args, **kwargs):
        """
        Require an implementation for a feature. Can be used to create objects
        without requiring an exact implementation to use.

        Depending on how the feature was configured during initialization, this
        may return a class, or potentially a singleton object. (in which case
        the args passed would be ignored)
        """
        try:
            provider = self.providers[feature]
        except KeyError:
            raise KeyError("Unknown feature: %r" % feature)

        if isinstance(provider, (type, types.ClassType)):
            # Args should never be used with singletons, they are ignored
            self.providers[feature] = provider()
        elif callable(provider):
            return provider(*args, **kwargs)

        return self.providers[feature]


def nonSingleton(other):
    """
    Creates a factory method for a class. Passes args to the constructor
    in order to create a new object every time it is required.
    """
    def factory(*args, **kwargs):
        return other(*args, **kwargs)
    return factory


# Create a global instance we can use in all components. Tests can override
# features as desired and that change should trickle out to all components.
FEATURES = FeatureBroker()


# Small wrapper functions to make usage look a little cleaner, can use these
# instead of the global:
def require(feature, *args, **kwargs):
    global FEATURES
    return FEATURES.require(feature, *args, **kwargs)


def provide(feature, provider, singleton=False):
    global FEATURES
    if not singleton and isinstance(provider, (type, types.ClassType)):
        provider = nonSingleton(provider)
    return FEATURES.provide(feature, provider)
