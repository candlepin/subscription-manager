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

log = logging.getLogger('rhsm-app.' + __name__)


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
    def __init__(self, product_dir, entitlement_dir, on_date=None, facts_dict=None):
        self.product_dir = product_dir
        self.entitlement_dir = entitlement_dir
        if not on_date:
            on_date = datetime.now()
        self.on_date = on_date

        self.expired_entitlement_certs = []
        self.valid_entitlement_certs = []

        # All products installed on this machine, regardless of status. Maps
        # product ID to certlib.Product object.
        self.all_products = {}

        # the specific products that are not entitled in the above certs,
        # dict maps product ID to product certificate.
        self.unentitled_products = {}

        # specific products which are installed, we're entitled, but have expired
        # on the date in question. this must watch out for possibility some other
        # entitlement certificate provides this product. Certificates which are
        # within their grace period will appear in this dict. maps product ID
        # to the expired entitlement certificate:
        self.expired_products = {}

        # products that are only partially entitled (aka, "yellow"
        self.partially_valid_products = {}

        # specific products which are installed, and entitled on the given date.
        # maps product ID to the valid entitlement certificate:
        self.valid_products = {}

        # products that we have entitlements for but no product cert for.
        self.not_installed_products = {}

        self.facts_dict = facts_dict

        log.debug("Sorting product and entitlement cert status for: %s" %
                on_date)

        self._populate_all_products()

        self._scan_entitlement_certs()

        self._scan_ent_cert_stackable_products()

        self._scan_for_unentitled_products()

        self._remove_expired_if_valid_elsewhere()
        log.debug("valid entitled products: %s" % self.valid_products.keys())
        log.debug("expired entitled products: %s" % self.expired_products.keys())
	log.debug("partially entitled products: %s" % self.partially_valid_products.keys())
	log.debug("unentitled products: %s" % self.unentitled_products.keys())

    def _populate_all_products(self):
        """ Build the dict of all installed products. """
        prod_certs = self.product_dir.list()
        for product_cert in prod_certs:
            product = product_cert.getProduct()
            self.all_products[product.getHash()] = product_cert

        log.debug("Installed product IDs: %s" % self.all_products.keys())

    def _scan_entitlement_certs(self):
        ent_certs = self.entitlement_dir.list()

        for ent_cert in ent_certs:

            if ent_cert.valid(on_date=self.on_date):
                self.valid_entitlement_certs.append(ent_cert)

                self._scan_ent_cert_products(ent_cert, self.valid_products,
                                             self.not_installed_products)
            else:
                self.expired_entitlement_certs.append(ent_cert)
                log.debug("expired:")
                log.debug(ent_cert.getProduct().getHash())
                self._scan_ent_cert_products(ent_cert, self.expired_products)

    def _scan_ent_cert_products(self, ent_cert, product_dict, uninstalled_dict=None):
        """
        Scans this ent certs products, checks if they are installed, and
        adds them to the provided dict (expired/valid) if so:
        """
        for product in ent_cert.getProducts():
            product_id = product.getHash()

            # Is this an installed product?
            if product_id in self.all_products:
                if product_id not in product_dict:
                    product_dict[product_id] = []
                product_dict[product_id].append(ent_cert)
            elif uninstalled_dict != None:
                if product_id not in uninstalled_dict:
                    uninstalled_dict[product_id] = []
                uninstalled_dict[product_id].append(ent_cert)

    def _scan_ent_cert_stackable_products(self):
        ent_certs = self.entitlement_dir.list()
        stackable_ents = {}

        for ent_cert in ent_certs:
            for product in [ent_cert.getProduct()]:
                product_id = product.getHash()
                order = ent_cert.getOrder()
                stacking_id = order.getStackingId()
                quantity = order.getQuantityUsed()
                if stacking_id:
                    if stacking_id not in stackable_ents:
                        stackable_ents[stacking_id] = []
                    stackable_ents[stacking_id].append({'ent_cert': ent_cert,
                                                        'product_id': product_id,
                                                        'quantity': quantity,
                                                        'sockets_provided': None,
                                                        'valid': None})

        for stackable_id in stackable_ents.keys():
            socket_total = 0
            system_sockets = 1
            if self.facts_dict:
                system_sockets = int(self.facts_dict['cpu.cpu_socket(s)'])

            for stackable_ent in stackable_ents[stackable_id]:
                socket_count = stackable_ent['ent_cert'].getOrder().getSocketLimit()
                quantity = stackable_ent['quantity']
                if socket_count:
                    socket_total = socket_total + (int(socket_count) * int(quantity))

            for i in stackable_ents[stackable_id]:
                i['sockets_provided'] = socket_total
                if socket_total >= system_sockets:
                    i['valid'] = True
                elif self.all_products.has_key(product_id):
                    # for cases where we have an ent but no prod cert
                    self.partially_valid_products[product_id] = self.all_products[product_id]

    def _scan_for_unentitled_products(self):
        # For all installed products, if not in valid or expired hash, it
        # must be completely unentitled
        for product_id in self.all_products.keys():
            if (product_id in self.valid_products) or (product_id in self.expired_products) \
               or (product_id in self.partially_valid_products):
                   continue
            self.unentitled_products[product_id] = self.all_products[product_id]

    def _remove_expired_if_valid_elsewhere(self):
        """
        Scan the expired products, if any are showing up also in the valid dict,
        remove them from expired.

        This catches situations where an entitlement for a product expires, but
        another still valid entitlement already provides the missing product.
        """
        for product_id in self.expired_products.keys():
            if product_id in self.valid_products:
                del self.expired_products[product_id]

class StackingGroupSorter(object):
    def __init__(self, entitlements):
        self.groups = []
        stacking_groups = {}

        for entitlement in entitlements:
            stacking_id = self._get_stacking_id(entitlement)
            if stacking_id:
                if stacking_id not in stacking_groups:
                    group = EntitlementGroup(entitlement, str(stacking_id))
                    self.groups.append(group)
                    stacking_groups[stacking_id] = group
                else:
                    group = stacking_groups[stacking_id]
                    group.add_entitlement_cert(entitlement)
            else:
                self.groups.append(EntitlementGroup(entitlement))

    def _get_stacking_id(self, entitlement):
        raise NotImplementedError("Subclasses must implement: _get_stacking_id")

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
