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

import gettext
_ = gettext.gettext

import rhsm.config
import logging

from subscription_manager.facts import Facts
from subscription_manager.cert_sorter import CertSorter
from subscription_manager import listing

log = logging.getLogger('rhsm-app.' + __name__)
cfg = rhsm.config.initConfig()


class ReleaseBackend(object):

    # all the proxy info too?
    def __init__(self, ent_dir=None, prod_dir=None,
                 content_connection=None, facts=None):
        self.entitlement_dir = ent_dir
        self.product_dir = prod_dir
        self.content_connection = content_connection
        self.facts = facts

    def get_releases(self):
        # cdn base url

        # let us pass in a facts object for testing
        if not self.facts:
            self.facts = Facts(ent_dir=self.entitlement_dir,
                               prod_dir=self.product_dir)

        # find entitlements for rhel product? (or vice versa)
        sorter = CertSorter(self.product_dir,
                            self.entitlement_dir,
                            self.facts.get_facts())

        # find the rhel product
        rhel_product = None
        for product_hash in sorter.installed_products:
            product_cert = sorter.installed_products[product_hash]
            products = product_cert.products
            for product in products:
                product_tags = product.provided_tags

                if self._is_rhel(product_tags):
                    rhel_product = product

        if rhel_product is None:
            return []

        entitlements = sorter.get_entitlements_for_product(rhel_product.id)
        listings = []
        for entitlement in entitlements:
            contents = entitlement.content
            for content in contents:
                # ignore content that is not enabled
                # see bz #820639
                if not content.enabled:
                    continue
                if self._is_correct_rhel(rhel_product.provided_tags,
                                         content.required_tags):
                    content_url = content.url
                    listing_parts = content_url.split('$releasever', 1)
                    listing_base = listing_parts[0]
                    listing_path = "%s/listing" % listing_base
                    listings.append(listing_path)

        # FIXME: not sure how to get the "base" content if we have multiple
        # entitlements for a product

        # for a entitlement, grant the corresponding entitlement cert
        # use it for this connection

        # hmm. We are really only supposed to have one product
        # with one content with one listing file. We shall see.
        releases = []
        listings = sorted(set(listings))
        for listing_path in listings:
            data = self.content_connection.get_versions(listing_path)
            ver_listing = listing.ListingFile(data=data)
            releases = releases + ver_listing.get_releases()

        releases_set = sorted(set(releases))
        return releases_set

    def _is_rhel(self, product_tags):
        #easy to pass a string instead of a list
        assert not isinstance(product_tags, basestring)

        for product_tag in product_tags:
            # so in theory, we should only have one rhel
            # product. Not sure what to do if we have
            # more than one. Probably throw an error
            # TESTME
            if product_tag.split('-', 1)[0] == "rhel":
                # we only need to match the first hit
                return True
        log.info("No products with RHEL product tags found")
        return False

    # require tags provided by installed products?
    def _is_correct_rhel(self, product_tags, content_tags):
        # easy to pass a string instead of a list
        assert not isinstance(product_tags, basestring)
        assert not isinstance(content_tags, basestring)

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

        log.info("No matching products with RHEL product tags found")
        return False
