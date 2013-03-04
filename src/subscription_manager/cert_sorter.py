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

from injection import FEATURES, IDENTITY
from datetime import datetime, timedelta
import logging

from rhsm.certificate import GMT
from rhsm.connection import safe_int

from subscription_manager.utils import parseDate

log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = gettext.gettext

FUTURE_SUBSCRIBED = "future_subscribed"
SUBSCRIBED = "subscribed"
NOT_SUBSCRIBED = "not_subscribed"
EXPIRED = "expired"
PARTIALLY_SUBSCRIBED = "partially_subscribed"

# Used when we are unregistered, or offline for a long period of time:
UNKNOWN = "unknown"

SOCKET_FACT = 'cpu.cpu_socket(s)'
RAM_FACT = 'memory.memtotal'


class CertSorter(object):
    """
    Queries the server for compliance information and breaks out the response
    for use in the client code.

    Originally this class actually sorted certificates and calculated status,
    but this is handled by the server today.

    If unregistered we report status as unknown.

    On every successful server fetch (for *right now*), we cache the results.
    In the event we are unable to reach the server periodically, we will
    re-use this cached data for a period of time, before falling back to
    reporting unknown.
    """
    def __init__(self, product_dir, entitlement_dir, uep):
        self.identity = FEATURES.require(IDENTITY)
        self.product_dir = product_dir
        self.entitlement_dir = entitlement_dir

        # Warning: could be None if we're not registered, we will check before
        # we use it, but if connection is still none we will let this error out
        # as it is programmer error.
        self.uep = uep

        # All products installed on this machine, regardless of status. Maps
        # installed product ID to product certificate.
        self.installed_products = self.product_dir.get_installed_products()

        # Installed products which do not have an entitlement that is valid,
        # or expired. They may however have entitlements for the future.
        # Maps installed product ID to the product certificate.
        self.unentitled_products = {}

        # Products which are installed, there are entitlements, but they have
        # expired on the date in question. If another valid or partially valid
        # entitlement provides the installed product, that product should not
        # appear in this dict.
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

        # Maps stack ID to a list of the entitlement certs composing a
        # partially valid stack:
        self.partial_stacks = {}

        # Products which are installed and entitled sometime in the future.
        # Maps product ID to future entitlements.
        # TODO: not in server call, calc locally?
        self.future_products = {}

        # The first date we're completely invalid from midnight to midnight:
        # Will be None if we're not currently valid for the date requested.
        self.first_invalid_date = None

        # TODO: Not in server status call but can be calculated locally
        # or just let the one place it's used figure it out on it's own
        self.valid_entitlement_certs = []

        self._parse_server_status()

    def _parse_server_status(self):
        """ Fetch entitlement status info from server and parse. """

        if not self.is_registered():
            log.debug("Unregistered, skipping server compliance check.")
            return
        # TODO: handle temporarily disconnected use case / caching

        status = self.uep.getCompliance(self.identity.uuid)

        # TODO: we're now mapping product IDs to entitlement cert JSON,
        # previously we mapped to actual entitlement cert objects. However,
        # nothing seems to actually use these, so it may not matter for now.
        self.valid_products = status['compliantProducts']

        self.partially_valid_products = status['partiallyCompliantProducts']

        self.partial_stacks = status['partialStacks']

        # For backward compatability with old find first invalid date,
        # we drop one second from the compliant until from server (as
        # it is returning the first second we are invalid), then add a full
        # 24 hours giving us the first date where we know we're completely
        # invalid from midnight to midnight.
        self.compliant_until = None
        if status['compliantUntil'] is not None:
            self.compliant_until = parseDate(status['compliantUntil'])
            self.first_invalid_date = self.compliant_until + \
                    timedelta(seconds=60 * 60 * 24 - 1)

        # Lookup product certs for each unentitled product returned by
        # the server:
        unentitled_pids = status['nonCompliantProducts']
        # Add in any installed products not in the server response. This
        # could happen if something changes before the certd runs. Log
        # a warning if it does, and treat it like an unentitled product.
        for pid in self.installed_products.keys():
            if pid not in self.valid_products and pid not in \
                    self.partially_valid_products and pid not in \
                    self.unentitled_products:
                log.warn("Installed product %s not present in response from "
                        "server." % pid)
                unentitled_pids.append(pid)

        for unentitled_pid in unentitled_pids:
            prod_cert = self.product_dir.findByProduct(unentitled_pid)
            # Ignore anything server thinks we have but we don't.
            if prod_cert is None:
                log.warn("Server reported installed product not on system: %s" %
                        unentitled_pid)
                continue
            self.unentitled_products[unentitled_pid] = prod_cert

        #self.facts_dict = facts_dict

        ## Number of sockets on this system:
        #self.socket_count = 1
        #if SOCKET_FACT in self.facts_dict:
        #    self.socket_count = safe_int(self.facts_dict[SOCKET_FACT], 1)
        #else:
        #    log.warn("System has no socket fact, assuming 1.")

        ## Amount of RAM on this system - default is 1GB
        #self.total_ram = 1
        #if RAM_FACT in self.facts_dict:
        #    self.total_ram = self._convert_system_ram_to_gb(
        #                        safe_int(self.facts_dict[RAM_FACT], self.total_ram))
        #else:
        #    log.warn("System has no %s fact, assuming 1GB" % RAM_FACT)

        #log.debug("Sorting product and entitlement cert status for: %s" %
        #        on_date)

        #self._scan_entitlement_certs()
        #self._scan_for_unentitled_products()

        self._scan_for_expired_or_future_products()

        log.debug("valid entitled products: %s" % self.valid_products.keys())
        log.debug("expired entitled products: %s" % self.expired_products.keys())
        log.debug("partially entitled products: %s" % self.partially_valid_products.keys())
        log.debug("unentitled products: %s" % self.unentitled_products.keys())
        log.debug("future products: %s" % self.future_products.keys())
        log.debug("partial stacks: %s" % self.partial_stacks.keys())
        log.debug("entitlements valid until: %s" % self.compliant_until)

    def is_valid(self):
        """
        Return true if the results of this cert sort indicate our
        entitlements are completely valid.
        """
        if self.partially_valid_products or self.expired_products or \
                self.partial_stacks or self.unentitled_products:
            return False

        return True

    def is_registered(self):
        return self.identity.is_valid()

    def get_status(self, product_id):
        """Return the status of a given product"""
        if not self.is_registered():
            return UNKNOWN
        if product_id in self.partially_valid_products:
            return PARTIALLY_SUBSCRIBED
        if product_id in self.valid_products:
            return SUBSCRIBED
        if product_id in self.future_products:
            return FUTURE_SUBSCRIBED
        if product_id in self.expired_products:
            return EXPIRED
        if product_id in self.unentitled_products:
            return NOT_SUBSCRIBED

    # TODO: moved to entitlement directory, see if we can remove this
    def get_entitlements_for_product(self, product_hash):
        entitlements = []
        for cert in self.entitlement_dir.list():
            for cert_product in cert.products:
                if product_hash == cert_product.id:
                    entitlements.append(cert)
        return entitlements

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
            if ent_cert.valid_range.begin() > self.on_date:
                log.debug("  future entitled: %s" % ent_cert.valid_range.begin())
                self._add_products_to_hash(ent_cert, self.future_products)

            # Check if entitlement has already expired:
            elif ent_cert.valid_range.end() < self.on_date:
                log.debug("  expired: %s" % ent_cert.valid_range.end())
                self._add_products_to_hash(ent_cert, self.expired_products)

            # Current entitlements:
            elif ent_cert.is_valid(on_date=self.on_date):
                self.valid_entitlement_certs.append(ent_cert)

                order = ent_cert.order
                stack_id = order.stacking_id

                partially_stacked = False
                if stack_id:
                    log.debug("  stack ID: %s" % stack_id)

                    # Just add to the correct list if we've already checked this stack:
                    if stack_id in self.partial_stacks:
                        log.debug("  stack already found to be invalid")
                        partially_stacked = True
                        self.partial_stacks[stack_id].append(ent_cert)
                    elif not self.stack_id_valid(stack_id, ent_certs):
                        log.debug("  stack is invalid")
                        partially_stacked = True
                        self.partial_stacks[stack_id] = [ent_cert]

                if partially_stacked:
                    self._add_products_to_hash(ent_cert, self.partially_valid_products)
                # Check for non-stacked entitlements which do not provide enough
                # socket coverage for the system:
                elif not stack_id and not self.ent_cert_sockets_valid(ent_cert):
                    self._add_products_to_hash(ent_cert, self.partially_valid_products)
                elif not stack_id and not self._ent_cert_ram_valid(ent_cert):
                    self._add_products_to_hash(ent_cert, self.partially_valid_products)
                # Anything else must be valid:
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

    def stack_id_valid(self, stack_id, ent_certs, on_date=None):
        """
        Returns True if the given stack ID is valid.

        Assumes that the certificate is valid on the date we're sorting for.
        Future and expired certs are filtered out before this is called.
        """
        sockets_covered = 0
        log.debug("Checking stack validity: %s" % stack_id)

        date_to_check = on_date or self.on_date

        for ent in ent_certs:
            if ent.order.stacking_id == stack_id and \
              ent.valid_range.begin() <= date_to_check and \
              ent.valid_range.end() >= date_to_check:
                quantity = safe_int(ent.order.quantity_used, 1)
                sockets = safe_int(ent.order.socket_limit, 1)
                sockets_covered += sockets * quantity

        log.debug("  system has %s sockets, %s covered by entitlements" %
                (self.socket_count, sockets_covered))
        if sockets_covered >= self.socket_count or sockets_covered == 0:
            return True
        return False

    def ent_cert_sockets_valid(self, ent, on_date=None):
        """
        Returns True if the given entitlement covers enough sockets for this
        system.

        If the entitlement has no socket restriction, True will always be
        returned.
        """
        if ent.order.socket_limit is None:
            return True

        # We do not check quantity here, as this is not a stacked
        # subscription:
        sockets_covered = safe_int(ent.order.socket_limit, 1)

        log.debug("  system has %s sockets, %s covered by entitlement" %
                (self.socket_count, sockets_covered))
        if sockets_covered >= self.socket_count or sockets_covered == 0:
            return True
        return False

    def _ent_cert_ram_valid(self, ent_cert):
        """
        Determines if the given entitlement covers the amount of RAM for
        this system.

        If the entitlement has no RAM restriction, then it is considered
        valid.
        """
        if ent_cert.order.ram_limit is None:
            return True

        entitlement_ram = ent_cert.order.ram_limit
        log.debug("  system has %s GB of RAM, %d GB covered by entitlement" %
                (self.total_ram, entitlement_ram))

        covered = self.total_ram <= entitlement_ram
        return covered

    def _add_products_to_hash(self, ent_cert, product_dict):
        """
        Adds any installed product IDs provided by the entitlement cert to
        the given dict. Maps product ID to entitlement certificate.
        """
        for product in ent_cert.products:
            product_id = product.id

            if product_id in self.installed_products:
                if product_id not in product_dict:
                    product_dict[product_id] = []
                product_dict[product_id].append(ent_cert)

    def _scan_for_expired_or_future_products(self):
        # Subtract out the valid and partially valid items from the
        # list of installed products
        unknown_products = dict((k, v) for (k, v) in self.installed_products.items() \
            if k not in self.valid_products.keys() \
            and k not in self.partially_valid_products.keys())
        ent_certs = self.entitlement_dir.list()

        on_date = datetime.now(GMT())
        for ent_cert in ent_certs:
            for product in ent_cert.products:
                if product.id in unknown_products.keys():
                    # If the entitlement starts after the date we're checking, we
                    # consider this a future entitlement. Technically it could be
                    # partially stacked on that date, but we cannot determine that
                    # without recursively cert sorting again on that date.
                    if ent_cert.valid_range.begin() > on_date:
                        product_dict = self.future_products
                    # Check if entitlement has already expired:
                    elif ent_cert.valid_range.end() < on_date:
                        product_dict = self.expired_products
                    else:
                        continue

                    product_dict.setdefault(product.id, []).append(ent_cert)

    def _scan_for_unentitled_products(self):
        # For all installed products, if not in valid or partially valid hash, it
        # must be completely unentitled
        for product_id in self.installed_products.keys():
            if (product_id in self.valid_products) or \
                    (product_id in self.expired_products) or \
                    (product_id in self.partially_valid_products):
                continue
            self.unentitled_products[product_id] = self.installed_products[product_id]

    def _convert_system_ram_to_gb(self, system_ram):
        """
        Convert system ram from kilobyes to Gigabytes.

        System RAM will be rounded to the nearest full
        GB value (i.e 1.3 GB == 1 GB). This is so that
        we can deal with a common base.
        """
        return int(round(system_ram / 1024.0 / 1024.0))


class StackingGroupSorter(object):
    def __init__(self, entitlements):
        self.groups = []
        stacking_groups = {}

        for entitlement in entitlements:
            stacking_id = self._get_stacking_id(entitlement)
            if stacking_id:
                if stacking_id not in stacking_groups:
                    group = EntitlementGroup(entitlement,
                            self._get_identity_name(entitlement))
                    self.groups.append(group)
                    stacking_groups[stacking_id] = group
                else:
                    group = stacking_groups[stacking_id]
                    group.add_entitlement_cert(entitlement)
            else:
                self.groups.append(EntitlementGroup(entitlement))

    def _get_stacking_id(self, entitlement):
        raise NotImplementedError("Subclasses must implement: _get_stacking_id")

    def _get_identity_name(self, entitlement):
        raise NotImplementedError(
                "Subclasses must implement: _get_identity_name")


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
        return cert.order.stacking_id

    def _get_identity_name(self, cert):
        return cert.order.name
