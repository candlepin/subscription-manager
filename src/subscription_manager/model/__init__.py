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

import logging

from rhsm.certificate2 import CONTENT_ACCESS_CERT_TYPE

log = logging.getLogger(__name__)

# These containerish iterables could share a
# base class, though, it should probably just
# be based on containers.abc.Iterable


class Content(object):
    """
    A generic representation of entitled content.
    """
    def __init__(self, content_type, name, label,
                 url=None, gpg=None, tags=None, cert=None,
                 enabled=None, metadata_expire=None):
        self.content_type = content_type
        self.name = name
        self.label = label

        self.url = url
        self.gpg = gpg
        self.tags = tags or []
        self.cert = cert
        self.enabled = enabled
        self.metadata_expire = metadata_expire


class Entitlement(object):
    """Represent an entitlement.

    Has a 'contents' attribute that is an
    iterable of EntitledContent objects. (currently EntCertEntitledContent)

    Note 'contents' that differs from the 'content'naming the
    rhsm EntitlementCertificate object uses.
    """

    def __init__(self, contents=None, entitlement_type=None):
        self.contents = contents
        self.entitlement_type = entitlement_type


class EntitlementSource(object):
    """Populate with info needed for plugins to find content.

    Acts as a iterable over entitlements.
    """
    def __init__(self):
        self._entitlements = []
        self.product_tags = []

    def __iter__(self):
        return iter(self._entitlements)

    def __len__(self):
        return len(self._entitlements)

    def __getitem__(self, key):
        return self._entitlements[key]


def find_content(ent_source, content_type=None):
    """
    Scan all entitlements looking for content of the given type. (string)
    Type will be compared case insensitive.

    Returns a list of model.Content.
    """
    entitled_content = []
    content_access_entitlement_content = {}
    content_labels = set()
    log.debug("Searching for content of type: %s" % content_type)
    for entitlement in ent_source:
        for content in entitlement.contents:
            # this is basically matching_content from repolib
            if content.content_type.lower() == content_type.lower() and \
                    content_tag_match(content.tags, ent_source.product_tags):
                if entitlement.entitlement_type == CONTENT_ACCESS_CERT_TYPE:
                    content_access_entitlement_content[content.label] = content
                else:
                    entitled_content.append(content)
                    content_labels.add(content.label)

    # now add content that wasn't covered by basic entitlement certs
    for label, content in list(content_access_entitlement_content.items()):
        if label not in content_labels:
            entitled_content.append(content)
    return entitled_content


def content_tag_match(content_tags, product_tags):
    """See if content required tags are provided by installed products.

    Note: this is skipped if the content does not have any required tags.
    """

    all_tags_found = True
    for content_tag in content_tags:
        if content_tag not in product_tags:
            all_tags_found = False
    return all_tags_found
