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

import logging

log = logging.getLogger('rhsm-app.' + __name__)

# These containerish iterables could share a
# base class, though, it should probably just
# be based on containers.abc.Iterable


class Content(object):
    """
    A generic representation of entitled content.
    """
    def __init__(self, content_type, name, label, url=None,
        gpg=None, cert=None):
        self.content_type = content_type
        self.name = name
        self.label = label
        self.url = url
        self.gpg = gpg
        self.cert = cert


class Entitlement(object):
    """Represent an entitlement.

    Has a 'contents' attribute that is an
    iterable of EntitledContent objects. (currently EntCertEntitledContent)

    Note 'contents' that differs from the 'content'naming the
    rhsm EntitlementCertificate object uses.
    """

    def __init__(self, contents=None):
        self.contents = contents


class EntitlementSource(object):
    """Populate with info needed for plugins to find content.

    Acts as a iterable over entitlements.
    """
    def __init__(self):
        self._entitlements = []

    def __iter__(self):
        return iter(self._entitlements)

    def __len__(self):
        return len(self._entitlements)

    def __getitem__(self, key):
        return self._entitlements[key]

    def find_content(self, content_type=None):
        """
        Scan all entitlements looking for content of the given type. (string)

        Returns a list of EntCertEntitledContent.
        """
        entitled_content = []
        log.debug("Searching for content of type: %s" % content_type)
        for entitlement in self._entitlements:
            for content in entitlement.contents:
                if content.content_type == content_type:
                    log.debug("found content: %s" % content.label)
                    # no unique constraint atm
                    entitled_content.append(content)
        return entitled_content
