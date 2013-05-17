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

from datetime import datetime, timedelta
import logging

from rhsm.certificate import GMT
import subscription_manager.injection as inj

log = logging.getLogger('rhsm-app.' + __name__)

from subscription_manager.isodate import parse_date
from subscription_manager.reasons import Reasons

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

STATUS_MAP = {'valid': _('Current'),
        'partial': _('Insufficient'),
        'invalid': _('Invalid')}


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
        self.identity = inj.require(inj.IDENTITY)
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
        self.future_products = {}

        # The first date we're completely invalid from midnight to midnight:
        # Will be None if we're not currently valid for the date requested.
        self.first_invalid_date = None

        # Reasons that products aren't fully compliant
        self.reasons = Reasons([], self)

        self.valid_entitlement_certs = []

        self._parse_server_status()

    def _parse_server_status(self):
        """ Fetch entitlement status info from server and parse. """

        if not self.is_registered():
            log.debug("Unregistered, skipping server compliance check.")
            return
        # TODO: handle temporarily disconnected use case / caching

        status_cache = inj.require(inj.STATUS_CACHE)
        status = status_cache.load_status(self.uep, self.identity.uuid)
        if status is None:
            return

        # TODO: we're now mapping product IDs to entitlement cert JSON,
        # previously we mapped to actual entitlement cert objects. However,
        # nothing seems to actually use these, so it may not matter for now.
        self.valid_products = status['compliantProducts']

        self.partially_valid_products = status['partiallyCompliantProducts']

        self.partial_stacks = status['partialStacks']

        if 'reasons' in status:
            self.reasons = Reasons(status['reasons'], self)

        if 'status' in status and len(status['status']):
            self.system_status = status['status']
        else:
            self.system_status = None

        # For backward compatability with old find first invalid date,
        # we drop one second from the compliant until from server (as
        # it is returning the first second we are invalid), then add a full
        # 24 hours giving us the first date where we know we're completely
        # invalid from midnight to midnight.
        self.compliant_until = None
        if status['compliantUntil'] is not None:
            self.compliant_until = parse_date(status['compliantUntil'])
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
                    unentitled_pids:
                log.warn("Installed product %s not present in response from "
                        "server." % pid)
                unentitled_pids.append(pid)

        for unentitled_pid in unentitled_pids:
            prod_cert = self.product_dir.find_by_product(unentitled_pid)
            # Ignore anything server thinks we have but we don't.
            if prod_cert is None:
                log.warn("Server reported installed product not on system: %s" %
                        unentitled_pid)
                continue
            self.unentitled_products[unentitled_pid] = prod_cert

        self._scan_entitlement_certs()

        log.debug("valid entitled products: %s" % self.valid_products.keys())
        log.debug("expired entitled products: %s" % self.expired_products.keys())
        log.debug("partially entitled products: %s" % self.partially_valid_products.keys())
        log.debug("unentitled products: %s" % self.unentitled_products.keys())
        log.debug("future products: %s" % self.future_products.keys())
        log.debug("partial stacks: %s" % self.partial_stacks.keys())
        log.debug("entitlements valid until: %s" % self.compliant_until)

    def _scan_entitlement_certs(self):
        """
        Scan entitlement certs looking for unentitled products which may
        have expired, or be entitled in future.

        Also builds up a list of valid certs today. (used when determining
        if anything is in it's warning period)
        """
        # Subtract out the valid and partially valid items from the
        # list of installed products
        unknown_products = dict((k, v) for (k, v) in self.installed_products.items()
                                if k not in self.valid_products.keys()
                                and k not in self.partially_valid_products.keys())
        ent_certs = self.entitlement_dir.list()

        on_date = datetime.now(GMT())
        for ent_cert in ent_certs:

            # Builds the list of valid entitlement certs today:
            if ent_cert.is_valid():
                self.valid_entitlement_certs.append(ent_cert)

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

    def get_system_status(self):
        return STATUS_MAP.get(self.system_status, _('Unknown'))

    def is_valid(self):
        """
        Return true if the results of this cert sort indicate our
        entitlements are completely valid.
        """
        if self.system_status:
            return self.system_status == 'valid'

        #Some old candlepin versions do not return 'status' with information
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
        else:
            # Can only really happen if server doesn't support compliance
            # API call:
            return UNKNOWN


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
