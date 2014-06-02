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




# These containerish iterables could share a
# base class, though, it should probably just
# be based on containers.abc.Iterable
class ContentSet(object):
    """Represent a container of Content objects."""
    def __init__(self, contents=None):
        self._contents = contents or []

    def __iter__(self):
        return iter(self._contents)

    def __len__(self):
        return len(self._contents)

    def __getitem__(self, key):
        return self._contents[key]

    def add(self, content):
        """Add content.

        Note add here does not neccasarily mean the same as
        add() on a set(). Subclasses are welcome to enforce
        uniqiness, etc. This base version appends to self._contents.
        """
        self._contents.append(content)


class EntCertEntitledContent(object):
    """Associate a Content with it's entitlement cert."""
    def __init__(self, content=None, cert=None):
        self.content = content
        self.cert = cert
        if self.content:
            self.content_type = self.content.content_type


class EntCertEntitledContentSet(ContentSet):
    """Represent a container of entitled Content."""
    pass


class Entitlement(object):
    """Represent an entitlement.

    Has a 'contents' attribute that is an
    iterable of EntitledContent objects.

    Note 'contents' that differs from the 'content'naming the
    rhsm EntitlementCertificate object uses.
    """

    def __init__(self, contents=None):
        self.contents = contents


class EntitlementCertEntitlement(Entitlement):
    """A Entitlement created from an EntitlementCertificate."""
    @classmethod
    def from_ent_cert(cls, ent_cert):
        content_set = EntCertEntitledContentSet()
        for ent_cert_content in ent_cert.content:
            ent_cert_ent_content = EntCertEntitledContent(content=ent_cert_content,
                                                          cert=ent_cert)
            content_set.add(ent_cert_ent_content)

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
