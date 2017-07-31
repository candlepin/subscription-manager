from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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
import collections
import datetime
import logging
import six

from subscription_manager import injection as inj
from subscription_manager.i18n import ugettext as _
from subscription_manager import managerlib, utils

from rhsm import certificate
from rhsmlib.services import exceptions, products

log = logging.getLogger(__name__)


class EntitlementService(object):
    def __init__(self, cp=None):
        self.cp = cp
        self.identity = inj.require(inj.IDENTITY)
        self.product_dir = inj.require(inj.PROD_DIR)
        self.entitlement_dir = inj.require(inj.ENT_DIR)

    def get_status(self, on_date=None):
        sorter = inj.require(inj.CERT_SORTER, on_date)
        if self.identity.is_valid():
            overall_status = sorter.get_system_status()
            reasons = sorter.reasons.get_name_message_map()
            valid = sorter.is_valid()
            return {'status': overall_status, 'reasons': reasons, 'valid': valid}
        else:
            return {'status': 'Unknown', 'reasons': {}, 'valid': False}

    def get_pools(self, pool_subsets=None, matches=None, pool_only=None, match_installed=None,
            no_overlap=None, service_level=None, show_all=None, on_date=None, **kwargs):
        # We accept a **kwargs argument so that the DBus object can pass whatever dictionary it receives
        # via keyword expansion.
        if kwargs:
            raise exceptions.ValidationError(_("Unknown arguments: %s") % kwargs.keys())

        if isinstance(pool_subsets, six.string_types):
            pool_subsets = [pool_subsets]

        # [] or None means look at all pools
        if not pool_subsets:
            pool_subsets = ['installed', 'consumed', 'available']

        options = {
            'pool_subsets': pool_subsets,
            'matches': matches,
            'pool_only': pool_only,
            'match_installed': match_installed,
            'no_overlap': no_overlap,
            'service_level': service_level,
            'show_all': show_all,
            'on_date': on_date,
        }
        self.validate_options(options)
        results = {}
        if 'installed' in pool_subsets:
            installed = products.InstalledProducts(self.cp).list(options['matches'])
            results['installed'] = [x._asdict() for x in installed]
        if 'consumed' in pool_subsets:
            consumed = self.get_consumed_product_pools(**options)
            results['consumed'] = [x._asdict() for x in consumed]
        if 'available' in pool_subsets:
            results['available'] = self.get_available_pools(**options)

        return results

    def get_consumed_product_pools(self, service_level=None, matches=None, **kwargs):
        # Use a named tuple so that the result can be unpacked into other functions
        ConsumedStatus = collections.namedtuple('ConsumedStatus', [
            'subscription_name',
            'provides',
            'sku',
            'contract',
            'account',
            'serial',
            'pool_id',
            'provides_management',
            'active',
            'quantity_used',
            'service_level',
            'service_type',
            'status_details',
            'subscription_type',
            'starts',
            'ends',
            'system_type',
        ])
        sorter = inj.require(inj.CERT_SORTER)
        cert_reasons_map = sorter.reasons.get_subscription_reasons_map()
        pooltype_cache = inj.require(inj.POOLTYPE_CACHE)

        consumed_statuses = []
        certs = self.entitlement_dir.list()
        cert_filter = utils.EntitlementCertificateFilter(filter_string=matches, service_level=service_level)

        if service_level is not None or matches is not None:
            certs = list(filter(cert_filter.match, certs))

        # Now we need to transform the EntitlementCertificate object into
        # something JSON-like for consumption
        for cert in certs:
            # for some certs, order can be empty
            # so we default the values and populate them if
            # they exist. BZ974587
            name = ""
            sku = ""
            contract = ""
            account = ""
            quantity_used = ""
            service_level = ""
            service_type = ""
            system_type = ""
            provides_management = "No"

            order = cert.order

            if order:
                service_level = order.service_level or ""
                service_type = order.service_type or ""
                name = order.name
                sku = order.sku
                contract = order.contract or ""
                account = order.account or ""
                quantity_used = order.quantity_used
                if order.virt_only:
                    system_type = _("Virtual")
                else:
                    system_type = _("Physical")

                if order.provides_management:
                    provides_management = _("Yes")
                else:
                    provides_management = _("No")

            pool_id = _("Not Available")
            if hasattr(cert.pool, "id"):
                pool_id = cert.pool.id

            product_names = [p.name for p in cert.products]

            reasons = []
            pool_type = ''

            if inj.require(inj.CERT_SORTER).are_reasons_supported():
                if cert.subject and 'CN' in cert.subject:
                    if cert.subject['CN'] in cert_reasons_map:
                        reasons = cert_reasons_map[cert.subject['CN']]
                    pool_type = pooltype_cache.get(pool_id)

                # 1180400: Status details is empty when GUI is not
                if not reasons:
                    if cert in sorter.valid_entitlement_certs:
                        reasons.append(_("Subscription is current"))
                    else:
                        if cert.valid_range.end() < datetime.datetime.now(certificate.GMT()):
                            reasons.append(_("Subscription is expired"))
                        else:
                            reasons.append(_("Subscription has not begun"))
            else:
                reasons.append(_("Subscription management service doesn't support Status Details."))

            consumed_statuses.append(ConsumedStatus(
                name,
                product_names,
                sku,
                contract,
                account,
                cert.serial,
                pool_id,
                provides_management,
                cert.is_valid(),
                quantity_used,
                service_level,
                service_type,
                reasons,
                pool_type,
                managerlib.format_date(cert.valid_range.begin()),
                managerlib.format_date(cert.valid_range.end()),
                system_type))
        return consumed_statuses

    def get_available_pools(self, show_all=None, on_date=None, no_overlap=None,
            match_installed=None, matches=None, service_level=None, **kwargs):
        available_pools = managerlib.get_available_entitlements(
            get_all=show_all,
            active_on=on_date,
            overlapping=no_overlap,
            uninstalled=match_installed,
            filter_string=matches
        )

        def filter_pool_by_service_level(pool_data):
            pool_level = ""
            if pool_data['service_level']:
                pool_level = pool_data['service_level']
            return service_level.lower() == pool_level.lower()

        if service_level is not None:
            available_pools = list(filter(filter_pool_by_service_level, available_pools))

        return available_pools

    def validate_options(self, options):
        if not set(['installed', 'consumed', 'available']).issuperset(options['pool_subsets']):
            raise exceptions.ValidationError(_('Error: invalid listing type provided.  Only "installed", '
                '"consumed", or "available" are allowed'))
        if options['show_all'] and 'available' not in options['pool_subsets']:
            raise exceptions.ValidationError(_("Error: --all is only applicable with --available"))
        elif options['on_date'] and 'available' not in options['pool_subsets']:
            raise exceptions.ValidationError(_("Error: --ondate is only applicable with --available"))
        elif options['service_level'] is not None \
                and not set(['consumed', 'available']).intersection(options['pool_subsets']):
            raise exceptions.ValidationError(_("Error: --servicelevel is only applicable with --available "
                "or --consumed"))
        elif options['match_installed'] and 'available' not in options['pool_subsets']:
            raise exceptions.ValidationError(_("Error: --match-installed is only applicable with "
                "--available"))
        elif options['no_overlap'] and 'available' not in options['pool_subsets']:
            raise exceptions.ValidationError(_("Error: --no-overlap is only applicable with --available"))
        elif options['pool_only'] \
                and not set(['consumed', 'available']).intersection(options['pool_subsets']):
            raise exceptions.ValidationError(_("Error: --pool-only is only applicable with --available "
                "and/or --consumed"))
        elif not self.identity.is_valid() and 'available' in options['pool_subsets']:
            raise exceptions.ValidationError(_("Error: this system is not registered"))
