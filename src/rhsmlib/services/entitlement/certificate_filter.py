from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2012 Red Hat, Inc.
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

import re


class CertificateFilter(object):
    def match(self, cert):
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        raise NotImplementedError


class ProductCertificateFilter(CertificateFilter):
    def __init__(self, filter_string=None):
        super(ProductCertificateFilter, self).__init__()

        self._fs_regex = None

        if filter_string is not None:
            self.set_filter_string(filter_string)

    def set_filter_string(self, filter_string):
        """
        Sets this filter's filter string to the specified string. The filter string may use ? or *
        for wildcards, representing one or any characters, respectively.

        Returns True if the specified filter string was processed and assigned successfully; False
        otherwise.
        """
        literals = []
        wildcards = []
        translated = []
        output = False

        wildcard_map = {
            '*': '.*',
            '?': '.',
        }

        expression = ur"""
            ((?:                # A captured, non-capture group :)
                [^*?\\]*        # Character literals and other uninteresting junk (greedy)
                (?:\\.?)*       # Anything escaped with a backslash, or just a trailing backslash
            )*)                 # Repeat the above sequence 0+ times, greedily
            ([*?]|\Z)           # Any of our wildcards (* or ?) not preceded by a backslash OR end of input
        """

        if filter_string is not None:
            try:
                # Break it up based on our special characters...
                for match in re.finditer(expression, filter_string, re.VERBOSE):
                    literals.append(match.group(1))

                    if match.group(2):
                        wildcards.append(match.group(2))

                # ...and put it all back together.
                for literal in literals:
                    # Impl note:
                    # Unfortunately we need to unescape the literals so they can be safely re-escaped by the
                    # re.escape method; lest we risk doubly-escaping some stuff and breaking our regex
                    # horribly.
                    literal = re.sub(r"\\([*?\\])", r"\1", literal)
                    literal = re.escape(literal)

                    translated.append(literal)
                    if len(wildcards):
                        translated.append(wildcard_map.get(wildcards.pop(0)))

                self._fs_regex = re.compile("^%s$" % ''.join(translated), re.IGNORECASE)
                output = True
            except TypeError:
                # Invalid filter string type. Rethrow with a proper message and backtrace?
                pass
        else:
            self._fs_regex = None
            output = True

        return output

    def match(self, cert):
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        # Check filter string (contains-text)
        if self._fs_regex is not None:
            # Perhaps we should be validating our input object here...?
            for product in cert.products:
                if (product.name and self._fs_regex.match(product.name) is not None) or (product.id and self._fs_regex.match(product.id) is not None):
                    return True

        return False


class EntitlementCertificateFilter(ProductCertificateFilter):
    def __init__(self, filter_string=None, service_level=None):
        super(EntitlementCertificateFilter, self).__init__(filter_string=filter_string)

        self._sl_filter = None

        if service_level is not None:
            self.set_service_level(service_level)

    def set_service_level(self, service_level):
        """
        Sets this filter's required service level to the level specified. Service level filters are
        case insensitive.

        Returns True if the service level filter was set successfully; False otherwise.
        """

        output = False

        if service_level is not None:
            try:
                self._sl_filter = '' + service_level.lower()
                output = True
            except:
                # Likely not a string or otherwise bad input.
                pass

        else:
            self._sl_filter = None
            output = True

        return output

    def match(self, cert):
        """
        Checks if the specified certificate matches this filter's restrictions.
        Returns True if the specified certificate matches this filter's restrictions ; False
        otherwise.
        """
        # Again: perhaps we should be validating our input object here...?

        # Check for exact match on service level:
        cert_service_level = ""  # No service level should match "".
        if cert.order and cert.order.service_level:
            cert_service_level = cert.order.service_level
        sl_check = self._sl_filter is None or \
            cert_service_level.lower() == self._sl_filter.lower()

        # Check filter string (contains-text)
        fs_check = self._fs_regex is None or (
            super(EntitlementCertificateFilter, self).match(cert) or
            (cert.order.name and self._fs_regex.match(cert.order.name) is not None) or
            (cert.order.sku and self._fs_regex.match(cert.order.sku) is not None) or
            (cert.order.service_level and self._fs_regex.match(cert.order.service_level) is not None) or
            (cert.order.contract and self._fs_regex.match(cert.order.contract) is not None)
        )

        return sl_check and fs_check and (self._sl_filter is not None or self._fs_regex is not None)
