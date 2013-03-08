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

# Supported Features:
IDENTITY = "IDENTITY"
CERT_SORTER = "CERT_SORTER"
PRODUCT_DATE_RANGE_CALCULATOR = "PRODUCT_DATE_RANGE_CALCULATOR"

import logging
log = logging.getLogger('rhsm-app.' + __name__)


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
        log.debug("Registering provider for feature %s: %s" % (feature, provider))
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
            if callable(provider):
                log.debug("Returning callable provider for feature %s: %s" %
                        (feature, provider))
                return provider(*args, **kwargs)
            else:
                log.debug("Returning instance for feature %s" % feature)
                return provider
        except KeyError:
            raise KeyError("Unknown feature: %r" % feature)
        return provider(*args, **kwargs)

# Create a global instance we can use in all components. Tests can override
# features as desired and that change should trickle out to all components.
FEATURES = FeatureBroker()
