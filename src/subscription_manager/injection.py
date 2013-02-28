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

class FeatureBroker:
    """
    Tracks all configured features.

    Can track both objects to be created on the fly, and singleton's only
    created once throughout the application.

    Do not use this class directly, rather the global instance created below.
    """
    def __init__(self):
        self.providers = {}

    # TODO: remove args, we either get a method to call with args later, or an
    # actual object here
    def provide(self, feature, provider, *args, **kwargs):
        """
        Provide an implementation for a feature.

        Can pass a callable you wish to be called on every invocation.

        Can also pass an actual instance which will be returned on every
        invocation. (i.e. pass an actual instance if you want a "singleton".
        """
        self.providers[feature] = provider

    def require(self, feature, *args, **kwargs):
        try:
            provider = self.providers[feature]
            if callable(provider):
                return provider(*args, **kwargs)
            else:
                return provider
        except KeyError:
            raise KeyError, "Unknown feature: %r" % feature
        return provider(*args, **kwargs)

# Create a global instance we can use in all components. Tests can override
# features as desired and that change should trickle out to all components.
FEATURES = FeatureBroker()


#class RequireFeature(object):

#    def __init__(self, feature):
#        self.feature = feature

#    def __get__(self, obj, T):
#        # Requests the
#        return self.result # <-- will request the feature upon first call

#    def __getattr__(self, name):
#        if name != 'result':
#            raise Exception("Unexpected feature attribute "
#                    "requested: %s" % name)
#        self.result = self.Request()
#        return self.result

#    def Request(self):
#        obj = FEATURES[self.feature]
#        return obj

