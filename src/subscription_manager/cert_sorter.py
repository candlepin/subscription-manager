# Copyright (c) 2011 Red Hat, Inc.
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

from datetime import datetime
import logging

from rhsm.certificate import GMT
log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = gettext.gettext

FUTURE_SUBSCRIBED = "future_subscribed"
SUBSCRIBED = "subscribed"
NOT_SUBSCRIBED = "not_subscribed"
EXPIRED = "expired"
PARTIALLY_SUBSCRIBED = "partially_subscribed"

SOCKET_FACT = 'cpu.cpu_socket(s)'


class CertSorter(object):
    """
    Class used to sort all certificates in the given Entitlement and Product
    directories into status for a particular date.

    Certs will be sorted into: installed, entitled, installed + entitled,
    installed + unentitled, expired.
    When looking for the products we need, only installed products will be
    considered. (i.e. we do not concern ourselves with products that are
    entitled but not installed)

    The date can be used to examine the state this system will likely be in
    at some point in the future.
    """
    def __init__(self, product_dir, entitlement_dir, facts_dict, on_date=None):
        self.product_dir = product_dir
        self.entitlement_dir = entitlement_dir
        if not on_date:
            on_date = datetime.now(GMT())
        self.on_date = on_date

        self.expired_entitlement_certs = []
        self.valid_entitlement_certs = []

        # All products installed on this machine, regardless of status. Maps
        # installed product ID to product certificate.
        self.installed_products = {}

        # Installed products which do not have an entitlement that is valid,
        # or expired. They may however have entitlements for the future.
        # Maps installed product ID to the product certificate.
        self.unentitled_products = {}

        # Products which are installed, there are entitlements, but they have
        # expired on the date in question. If another valid or partially valid
        # entitlement provides the installed product, that product should not
        # appear in this dict.
        # Certificates which are within their grace period will appear in this dict.
        # Maps product ID to the expired entitlement certificate:
        self.expired_products = {}

        # Products that are only partially entitled (aka, "yellow"). If another
        # non-stacked entitlement is valid and provides the installed product,
        # it will not appear in this dict.
        # Maps installed product ID to the stacked entitlement certificates
        # providing it.
        self.partially_valid_products = {}

        # Products which are installed, and entitled on the given date.
        # Maps product ID to a list of all valid entitlement certificates:
        self.valid_products = {}

        # Products which are installed and entitled sometime in the future.
        # Maps product ID to future entitlements.
        self.future_products = {}

        # Maps stack ID to a list of the entitlement certs composing a
        # partially valid stack:
        self.partial_stacks = {}

        # Maps stack ID to a list of the entitlement certs composing a
        # valid stack:
        self.valid_stacks = {}

        self.facts_dict = facts_dict

        # Number of sockets on this system:
        self.socket_count = 1
        if SOCKET_FACT in self.facts_dict:
            self.socket_count = int(self.facts_dict[SOCKET_FACT])
        else:
            log.warn("System has no socket fact, assuming 1.")

        log.debug("Sorting product and entitlement cert status for: %s" %
                on_date)

        self._populate_installed_products()
        self._scan_entitlement_certs()
        self._scan_for_unentitled_products()

        log.debug("valid entitled products: %s" % self.valid_products.keys())
        log.debug("expired entitled products: %s" % self.expired_products.keys())
        log.debug("partially entitled products: %s" % self.partially_valid_products.keys())
        log.debug("unentitled products: %s" % self.unentitled_products.keys())
        log.debug("future products: %s" % self.future_products.keys())
        log.debug("partial stacks: %s" % self.partial_stacks.keys())
        log.debug("valid stacks: %s" % self.valid_stacks.keys())

    def is_valid(self):
        """
        Return true if the results of this cert sort indicate our
        entitlements are completely valid.
        """
        if self.partially_valid_products or self.expired_products or \
                self.partial_stacks or self.unentitled_products:
            return False

        return True

    def get_status(self, product_id):
        """Return the status of a given product"""
        if product_id in self.valid_products:
            return SUBSCRIBED
        if product_id in self.future_products:
            return FUTURE_SUBSCRIBED
        if product_id in self.expired_products:
            return EXPIRED
        if product_id in self.unentitled_products:
            return NOT_SUBSCRIBED
        if product_id in self.partially_valid_products:
            return PARTIALLY_SUBSCRIBED

    # TODO: get_begin_date and get_end_date don't look right, I think
    # we're showing earliest start date through last end date, without
    # considering that we might be invalid somewhere in the
    # middle. Figuring out how to show this on the CLI where this is used
    # will not be easy.

    # find the display start date for this product id
    def get_begin_date(self, product_hash):
        begin_dates = []
        ent_certs = self.get_entitlements_for_product(product_hash)
        for ent_cert in ent_certs:
            begin_date = ent_cert.validRange().begin()
            begin_dates.append(begin_date)
        begin_dates.sort()
        return begin_dates[0]

    # find the display end date for this product id
    def get_end_date(self, product_hash):
        end_dates = []
        ent_certs = self.get_entitlements_for_product(product_hash)
        for ent_cert in ent_certs:
            end_date = ent_cert.validRange().end()
            end_dates.append(end_date)
        end_dates.sort()
        return end_dates[0]

    def get_entitlements_for_product(self, product_hash):
        entitlements = []
        for cert in self.entitlement_dir.list():
            for cert_product in cert.getProducts():
                if product_hash == cert_product.getHash():
                    entitlements.append(cert)
        return entitlements

    def _populate_installed_products(self):
        """ Build the dict of all installed products. """
        prod_certs = self.product_dir.list()
        for product_cert in prod_certs:
            product = product_cert.getProduct()
            self.installed_products[product.getHash()] = product_cert

        log.debug("Installed product IDs: %s" % self.installed_products.keys())

    # pass in list to update, like installed_products
    # keep duplicate lists for future dates, to find first_invalid
    # see validity.find_first_invalid_date
    def _scan_entitlement_certs(self):
        """
        Main method used to scan all entitlement certs on the machine, and
        sort them into the appropriate lists.

        Iterates all entitlement certs once, plus an single additional pass for
        each unique stack ID found.
        """
        ent_certs = self.entitlement_dir.list()

        for ent_cert in ent_certs:
            log.debug("Checking certificate: %s" % ent_cert.serial)

            # If the entitlement starts after the date we're checking, we
            # consider this a future entitlement. Technically it could be
            # partially stacked on that date, but we cannot determine that
            # without recursively cert sorting again on that date.
            if ent_cert.validRange().begin() > self.on_date:
                log.debug("  future entitled: %s" % ent_cert.validRange().begin())
                self._add_products_to_hash(ent_cert, self.future_products)

            # Check if entitlement has already expired:
            elif ent_cert.validRange().end() < self.on_date:
                log.debug("  expired: %s" % ent_cert.validRange().end())
                self.expired_entitlement_certs.append(ent_cert)
                self._add_products_to_hash(ent_cert, self.expired_products)

            # Current entitlements:
            elif ent_cert.valid(on_date=self.on_date):
                self.valid_entitlement_certs.append(ent_cert)

                order = ent_cert.getOrder()
                stack_id = order.getStackingId()

                partially_stacked = False
                if stack_id:
                    log.debug("  stack ID: %s" % stack_id)

                    # Just add to the correct list if we've already checked this stack:
                    if stack_id in self.partial_stacks:
                        log.debug("  stack already found to be invalid")
                        partially_stacked = True
                        self.partial_stacks[stack_id].append(ent_cert)
                    elif stack_id in self.valid_stacks:
                        log.debug("  stack already found to be valid")
                        self.valid_stacks[stack_id].append(ent_cert)

                    elif not self._stack_id_valid(stack_id, ent_certs):
                        log.debug("  stack is invalid")
                        partially_stacked = True
                        self.partial_stacks[stack_id] = [ent_cert]
                    else:
                        log.debug("  stack is valid")
                        self.valid_stacks[stack_id] = [ent_cert]

                if partially_stacked:
                    self._add_products_to_hash(ent_cert, self.partially_valid_products)
                else:
                    self._add_products_to_hash(ent_cert, self.valid_products)

        # Remove any partially valid products if we have a regular
        # entitlement that provides them:
        for pid in self.partially_valid_products.keys():
            if pid in self.valid_products:
                self.partially_valid_products.pop(pid)

        # Remove any expired products if we have a valid entitlement
        # that provides them:
        for pid in self.expired_products.keys():
            if pid in self.valid_products or pid in \
                    self.partially_valid_products:
                self.expired_products.pop(pid)

        # NOTE: unentitled_products will be detected in another method call

    def _stack_id_valid(self, stack_id, ent_certs):
        """
        Returns True if the given stack ID is valid.

        Assumes that the certificate is valid on the date we're sorting for.
        Future and expired certs are filtered out before this is called.
        """
        sockets_covered = 0
        log.debug("Checking stack validity: %s" % stack_id)

        for ent in ent_certs:
            if ent.getOrder().getStackingId() == stack_id:
                quantity = int(ent.getOrder().getQuantityUsed())
                sockets = int(ent.getOrder().getSocketLimit())
                sockets_covered += sockets * quantity

        log.debug("  system has %s sockets, %s covered by entitlements" %
                (self.socket_count, sockets_covered))
        if sockets_covered >= self.socket_count:
            return True
        return False

    def _add_products_to_hash(self, ent_cert, product_dict):
        """
        Adds any installed product IDs provided by the entitlement cert to
        the given dict. Maps product ID to entitlement certificate.
        """
        for product in ent_cert.getProducts():
            product_id = product.getHash()

            if product_id in self.installed_products:
                if product_id not in product_dict:
                    product_dict[product_id] = []
                product_dict[product_id].append(ent_cert)

    def _scan_for_unentitled_products(self):
        # For all installed products, if not in valid or partially valid hash, it
        # must be completely unentitled
        for product_id in self.installed_products.keys():
            if (product_id in self.valid_products) or \
                    (product_id in self.expired_products) or \
                    (product_id in self.partially_valid_products):
                continue
            self.unentitled_products[product_id] = self.installed_products[product_id]


class StackingGroupSorter(object):
    def __init__(self, entitlements):
        self.groups = []
        stacking_groups = {}

        for entitlement in entitlements:
            stacking_id = self._get_stacking_id(entitlement)
            if stacking_id:
                if stacking_id not in stacking_groups:
                    group = EntitlementGroup(entitlement,
                            self._get_product_name(entitlement))
                    self.groups.append(group)
                    stacking_groups[stacking_id] = group
                else:
                    group = stacking_groups[stacking_id]
                    group.add_entitlement_cert(entitlement)
            else:
                self.groups.append(EntitlementGroup(entitlement))

    def _get_stacking_id(self, entitlement):
        raise NotImplementedError("Subclasses must implement: _get_stacking_id")

    def _get_product_name(self, entitlement):
        raise NotImplementedError(
                "Subclasses must implement: _get_product_name")


class EntitlementGroup(object):
    def __init__(self, entitlement, name=''):
        self.name = name
        self.entitlements = []
        self.add_entitlement_cert(entitlement)

    def add_entitlement_cert(self, entitlement):
        self.entitlements.append(entitlement)


class EntitlementCertStackingGroupSorter(StackingGroupSorter):
    def __init__(self, certs):
        StackingGroupSorter.__init__(self, certs)

    def _get_stacking_id(self, cert):
        return cert.getOrder().getStackingId()

    def _get_product_name(self, cert):
        return cert.getProduct().getName()
