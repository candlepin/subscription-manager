from __future__ import print_function, division, absolute_import

#
# Subscription manager command line utility. This script is a modified version of
# cp_client.py from candlepin scripts
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

import logging
import socket
import six

import six.moves.http_client
from rhsm.https import ssl
from rhsm.connection import NoValidEntitlement

import rhsm.config

from subscription_manager import injection as inj
from subscription_manager import listing
from subscription_manager import rhelproduct
from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

cfg = rhsm.config.initConfig()


class MultipleReleaseProductsError(ValueError):
    def __init__(self, certificates):
        self.certificates = certificates
        self.certificate_paths = ", ".join([certificate.path for certificate in certificates])
        super(ValueError, self).__init__(("More than one release product certificate installed. Certificate paths: %s"
                                          % self.certificate_paths))

    def translated_message(self):
        return (_("Error: More than one release product certificate installed. Certificate paths: %s")
                % ", ".join([certificate.path for certificate in self.certificates]))


class ContentConnectionProvider(object):
    def __init__(self):
        pass


class ReleaseBackend(object):

    def get_releases(self):
        provider = self._get_release_version_provider()
        return provider.get_releases()

    def _get_release_version_provider(self):
        release_provider = ApiReleaseVersionProvider()
        if release_provider.api_supported():
            return release_provider
        return CdnReleaseVersionProvider()


class ApiReleaseVersionProvider(object):

    def __init__(self):
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.identity = inj.require(inj.IDENTITY)

    def api_supported(self):
        return self._conn().supports_resource("available_releases")

    def get_releases(self):
        return self._conn().getAvailableReleases(self.identity.uuid)

    def _conn(self):
        return self.cp_provider.get_consumer_auth_cp()


class CdnReleaseVersionProvider(object):

    def __init__(self):
        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.product_dir = inj.require(inj.PROD_DIR)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.content_connection = self.cp_provider.get_content_connection()

    def get_releases(self):
        # cdn base url

        # Find the rhel products
        release_products = []
        certificates = set()
        installed_products = self.product_dir.get_installed_products()
        for product_hash in installed_products:
            product_cert = installed_products[product_hash]
            products = product_cert.products
            for product in products:
                rhel_matcher = rhelproduct.RHELProductMatcher(product)
                if rhel_matcher.is_rhel():
                    release_products.append(product)
                    certificates.add(product_cert)

        if len(release_products) == 0:
            log.debug("No products with RHEL product tags found")
            return []
        elif len(release_products) > 1:
            raise MultipleReleaseProductsError(certificates=certificates)

        # Note: only release_products with one item can pass previous if-elif
        release_product = release_products[0]
        entitlements = self.entitlement_dir.list_for_product(release_product.id)

        listings = []
        ent_cert_key_pairs = set()
        for entitlement in entitlements:
            contents = entitlement.content
            for content in contents:
                # ignore content that is not enabled
                # see bz #820639
                if not content.enabled:
                    continue
                if self._is_correct_rhel(release_product.provided_tags,
                                         content.required_tags):
                    listing_path = self._build_listing_path(content.url)
                    listings.append(listing_path)
                    ent_cert_key_pairs.add((entitlement.path, entitlement.key_path()))

        # FIXME: not sure how to get the "base" content if we have multiple
        # entitlements for a product

        # for a entitlement, grant the corresponding entitlement cert
        # use it for this connection

        # hmm. We are really only supposed to have one product
        # with one content with one listing file. We shall see.
        releases = []
        listings = sorted(set(listings))
        for listing_path in listings:
            try:
                data = self.content_connection.get_versions(listing_path, list(ent_cert_key_pairs))
            except (socket.error,
                    six.moves.http_client.HTTPException,
                    ssl.SSLError,
                    NoValidEntitlement) as e:
                # content connection doesn't handle any exceptions
                # and the code that invokes this doesn't either, so
                # swallow them here.
                log.exception(e)
                continue

            # any non 200 response on fetching the release version
            # listing file returns a None here
            if not data:
                continue

            ver_listing = listing.ListingFile(data=data)

            # ver_listing.releases can be empty
            releases = releases + ver_listing.get_releases()

        releases_set = sorted(set(releases))
        return releases_set

    def _build_listing_path(self, content_url):
        listing_parts = content_url.split('$releasever', 1)
        listing_base = listing_parts[0]
        # FIXME: cleanup paths ("//"'s, etc)
        return u"%s/listing" % listing_base  # FIXME(khowell): ensure that my changes here don't break earlier fix

    # require tags provided by installed products?

    def _is_correct_rhel(self, product_tags, content_tags):
        # easy to pass a string instead of a list
        assert not isinstance(product_tags, six.string_types)
        assert not isinstance(content_tags, six.string_types)

        for product_tag in product_tags:
            # we are comparing the lists to see if they
            # have a matching rhel-#
            product_split = product_tag.split('-', 2)
            if product_split[0] == "rhel":
                # look for match in content tags
                for content_tag in content_tags:
                    content_split = content_tag.split('-', 2)

                    # ignore non rhel content tags
                    if content_split[0] != "rhel":
                        continue

                    # exact match
                    if product_tag == content_tag:
                        return True

                    # is this content for a base of this variant
                    if product_tag.startswith(content_tag):
                        return True
                    # else, we don't match, keep looking

        log.debug("Ignoring content with tags [%s] because it does not match installed product tags [%s]" % (
            ','.join(content_tags),
            ','.join(product_tags)
        ))
        return False
