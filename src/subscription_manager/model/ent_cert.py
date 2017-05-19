from __future__ import print_function, division, absolute_import

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

import subscription_manager.injection as inj

from subscription_manager.model import Content, Entitlement, EntitlementSource


class EntitlementCertContent(Content):
    @classmethod
    def from_cert_content(cls, ent_cert_content, cert=None):
        """
        Creates a generic subscription_manager.model.Content from an
        rhsm.certificate2.Content.

        Because the rhsm Content does not carry a cert (it originates
        from one), we have to pass this in separately.
        """
        return cls(content_type=ent_cert_content.content_type,
            name=ent_cert_content.name, label=ent_cert_content.label,
            url=ent_cert_content.url, gpg=ent_cert_content.gpg,
            tags=ent_cert_content.required_tags, cert=cert,
            enabled=ent_cert_content.enabled,
            metadata_expire=ent_cert_content.metadata_expire)


class EntitlementCertEntitlement(Entitlement):
    """A Entitlement created from an EntitlementCertificate."""
    @classmethod
    def from_ent_cert(cls, ent_cert):
        content_set = []
        for ent_cert_content in ent_cert.content:
            ent_cert_ent_content = EntitlementCertContent.from_cert_content(
                ent_cert_content, ent_cert)
            content_set.append(ent_cert_ent_content)

        # create a :EntitlementCertEntitlement with a EntitledContents
        # as the content Iterables
        ent_cert_ent = cls(content_set, ent_cert.entitlement_type)

        # could populate more info here, but
        # we don't actually seem to use it anywhere
        # here or in repolib
        return ent_cert_ent


class EntitlementDirEntitlementSource(EntitlementSource):
    """Populate with entitlement info from ent dir of ent certs."""

    def __init__(self):
        ent_dir = inj.require(inj.ENT_DIR)
        prod_dir = inj.require(inj.PROD_DIR)

        self.product_tags = prod_dir.get_provided_tags()

        # populate from ent certs
        self._entitlements = []
        for ent_cert in ent_dir.list_valid_with_content_access():
            self._entitlements.append(
                EntitlementCertEntitlement.from_ent_cert(ent_cert))
