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

import subscription_manager.injection as inj

log = logging.getLogger('rhsm-app.' + __name__)

# These containerish iterables could share a
# base class, though, it should probably just
# be based on containers.abc.Iterable


# TODO: rename to Content?
class EntCertEntitledContent(object):
    """
    A representation of entitled content.

    Very similar to an rhsm.certificate2.Content object and exposes some
    of the same information, but may expose additional things in the future.
    """
    def __init__(self, content=None, cert=None):
        self.cert = cert
        if content:
            self.content_type = content.content_type
            self.label = content.label
            self.name = content.name
            self.url = content.url
            self.gpg = content.gpg


class Entitlement(object):
    """Represent an entitlement.

    Has a 'contents' attribute that is an
    iterable of EntitledContent objects. (currently EntCertEntitledContent)

    Note 'contents' that differs from the 'content'naming the
    rhsm EntitlementCertificate object uses.
    """

    def __init__(self, contents=None):
        self.contents = contents


class EntitlementCertEntitlement(Entitlement):
    """A Entitlement created from an EntitlementCertificate."""
    @classmethod
    def from_ent_cert(cls, ent_cert):
        content_set = []
        for ent_cert_content in ent_cert.content:
            ent_cert_ent_content = EntCertEntitledContent(content=ent_cert_content,
                                                          cert=ent_cert)
            content_set.append(ent_cert_ent_content)

        # create a :EntitlementCertEntitlement with a EntitledContents
        # as the content Iterables
        ent_cert_ent = cls(content_set)

        # could populate more info here, but
        # we don't actually seem to use it anywhere
        # here or in repolib
        return ent_cert_ent


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

    def find_content_of_type(self, find_type):
        """
        Scan all entitlements looking for content of the given type. (string)

        Returns a list of EntCertEntitledContent.
        """
        entitled_content = []
        log.debug("Searching for content of type: %s" % find_type)
        for entitlement in self._entitlements:
            for content in entitlement.contents:
                if content.content_type == find_type:
                    log.debug("found content: %s" % content.label)
                    # no unique constraint atm
                    entitled_content.append(content)
        return entitled_content


class EntitlementDirEntitlementSource(EntitlementSource):
    """Populate with entitlement info from ent dir of ent certs."""

    def __init__(self):
        ent_dir = inj.require(inj.ENT_DIR)

        # populate from ent certs
        self._entitlements = []
        for ent_cert in ent_dir.list_valid():
            self._entitlements.append(
                EntitlementCertEntitlement.from_ent_cert(ent_cert))
