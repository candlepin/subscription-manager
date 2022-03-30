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
import time
from typing import Union, Callable

from subscription_manager import injection as inj
from subscription_manager.i18n import ugettext as _
from subscription_manager import managerlib, utils
from subscription_manager.entcertlib import EntCertActionInvoker

from rhsm import certificate
from rhsmlib.services import exceptions, products
import rhsm.connection as connection

log = logging.getLogger(__name__)


class EntitlementService:
    def __init__(self, cp: connection.UEPConnection = None) -> None:
        self.cp = cp
        self.identity = inj.require(inj.IDENTITY)
        self.product_dir = inj.require(inj.PROD_DIR)
        self.entitlement_dir = inj.require(inj.ENT_DIR)
        self.entcertlib = EntCertActionInvoker()

    @classmethod
    def parse_date(cls, on_date: str) -> datetime.datetime:
        """
        Return new datetime parsed from date
        :param on_date: String representing date
        :return It returns datetime.datetime structure representing date
        """
        try:
            on_date = datetime.datetime.strptime(on_date, "%Y-%m-%d")
        except ValueError:
            local_date = time.strftime("%Y-%m-%d", time.localtime())
            raise ValueError(
                _("Date entered is invalid. Date should be in YYYY-MM-DD format (example: {date})").format(
                    date=local_date
                )
            )
        if on_date.date() < datetime.datetime.now().date():
            raise ValueError(_("Past dates are not allowed"))
        return on_date

    def get_status(self, on_date: str = None, force: bool = False) -> dict:
        sorter = inj.require(inj.CERT_SORTER, on_date)
        # When singleton CertSorter was created with different argument on_date, then
        # it is necessary to update corresponding attribute in object (dependency
        # injection doesn't do it automatically).
        if sorter.on_date != on_date:
            sorter.on_date = on_date

        # Force reload status from the server to be sure that we get valid status for new date.
        # It is necessary to do it for rhsm.service, because it can run for very long time without
        # restart.
        if force is True:
            log.debug("Deleting cache entitlement status cache")
            status_cache = inj.require(inj.ENTITLEMENT_STATUS_CACHE)
            status_cache.server_status = None
            status_cache.delete_cache()

        sorter.load()

        if self.identity.is_valid():
            overall_status = sorter.get_system_status()
            overall_status_id = sorter.get_system_status_id()
            reasons = sorter.reasons.get_name_message_map()
            reason_ids = sorter.reasons.get_reason_ids_map()
            valid = sorter.is_valid()
            status = {
                "status": overall_status,
                "status_id": overall_status_id,
                "reasons": reasons,
                "reason_ids": reason_ids,
                "valid": valid,
            }
        else:
            status = {
                "status": _("Unknown"),
                "status_id": "unknown",
                "reasons": {},
                "reason_ids": {},
                "valid": False,
            }
        log.debug("entitlement status: %s" % str(status))
        return status

    # FIXME: Many None default values are suspicious. It looks like that type of e.g. show_all
    # pool_only, match_installed, etc. is bool and default value should be False (not None).
    def get_pools(
        self,
        pool_subsets: Union[str, list] = None,
        matches: str = None,
        pool_only: bool = None,
        match_installed: bool = None,
        no_overlap: bool = None,
        service_level: str = None,
        show_all: bool = None,
        on_date: datetime.datetime = None,
        future: str = None,
        after_date: datetime.datetime = None,
        page: int = 0,
        items_per_page: int = 0,
        **kwargs: dict
    ) -> dict:
        # We accept a **kwargs argument so that the DBus object can pass whatever dictionary it receives
        # via keyword expansion.
        if kwargs:
            raise exceptions.ValidationError(_("Unknown arguments: %s") % kwargs.keys())

        if isinstance(pool_subsets, str):
            pool_subsets = [pool_subsets]

        # [] or None means look at all pools
        if not pool_subsets:
            pool_subsets = ["installed", "consumed", "available"]

        options = {
            "pool_subsets": pool_subsets,
            "matches": matches,
            "pool_only": pool_only,
            "match_installed": match_installed,
            "no_overlap": no_overlap,
            "service_level": service_level,
            "show_all": show_all,
            "on_date": on_date,
            "future": future,
            "after_date": after_date,
        }
        self.validate_options(options)
        results = {}
        if "installed" in pool_subsets:
            installed = products.InstalledProducts(self.cp).list(matches, iso_dates=True)
            results["installed"] = [x._asdict() for x in installed]
        if "consumed" in pool_subsets:
            consumed = self.get_consumed_product_pools(
                service_level=service_level, matches=matches, iso_dates=True
            )
            if pool_only:
                results["consumed"] = [x._asdict()["pool_id"] for x in consumed]
            else:
                results["consumed"] = [x._asdict() for x in consumed]
        if "available" in pool_subsets:
            available = self.get_available_pools(
                show_all=show_all,
                on_date=on_date,
                no_overlap=no_overlap,
                match_installed=match_installed,
                matches=matches,
                service_level=service_level,
                future=future,
                after_date=after_date,
                page=int(page),
                items_per_page=int(items_per_page),
                iso_dates=True,
            )
            if pool_only:
                results["available"] = [x["id"] for x in available]
            else:
                results["available"] = available

        return results

    def get_consumed_product_pools(
        self, service_level: str = None, matches: str = None, iso_dates: bool = False
    ) -> list:
        # Use a named tuple so that the result can be unpacked into other functions
        OldConsumedStatus = collections.namedtuple(
            "OldConsumedStatus",
            [
                "subscription_name",
                "provides",
                "sku",
                "contract",
                "account",
                "serial",
                "pool_id",
                "provides_management",
                "active",
                "quantity_used",
                "service_type",
                "service_level",
                "status_details",
                "subscription_type",
                "starts",
                "ends",
                "system_type",
            ],
        )
        # Use a named tuple so that the result can be unpacked into other functions
        ConsumedStatus = collections.namedtuple(
            "ConsumedStatus",
            [
                "subscription_name",
                "provides",
                "sku",
                "contract",
                "account",
                "serial",
                "pool_id",
                "provides_management",
                "active",
                "quantity_used",
                "service_type",
                "roles",
                "service_level",
                "usage",
                "addons",
                "status_details",
                "subscription_type",
                "starts",
                "ends",
                "system_type",
            ],
        )
        sorter = inj.require(inj.CERT_SORTER)
        cert_reasons_map = sorter.reasons.get_subscription_reasons_map()
        pooltype_cache = inj.require(inj.POOLTYPE_CACHE)

        consumed_statuses = []
        # FIXME: the cache of CertificateDirectory should be smart enough and refreshing
        # should not be necessary. When new certificate is installed/deleted and rhsm-service
        # is running, then list of certificate is not automatically refreshed ATM.
        self.entitlement_dir.refresh()
        certs = self.entitlement_dir.list()
        cert_filter = utils.EntitlementCertificateFilter(filter_string=matches, service_level=service_level)

        if service_level is not None or matches is not None:
            certs = list(filter(cert_filter.match, certs))

        if iso_dates:
            date_formatter = managerlib.format_iso8601_date
        else:
            date_formatter = managerlib.format_date

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
            service_type = ""
            roles = ""
            service_level = ""
            usage = ""
            addons = ""
            system_type = ""
            provides_management = "No"

            order = cert.order

            if order:
                service_type = order.service_type or ""
                service_level = order.service_level or ""
                if cert.version.major >= 3 and cert.version.minor >= 4:
                    roles = order.roles or ""
                    usage = order.usage or ""
                    addons = order.addons or ""
                else:
                    roles = None
                    usage = None
                    addons = None
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

            provided_products = {p.id: p.name for p in cert.products}

            reasons = []
            pool_type = ""

            if inj.require(inj.CERT_SORTER).are_reasons_supported():
                if cert.subject and "CN" in cert.subject:
                    if cert.subject["CN"] in cert_reasons_map:
                        reasons = cert_reasons_map[cert.subject["CN"]]
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

            if roles is None and usage is None and addons is None:
                consumed_statuses.append(
                    OldConsumedStatus(
                        name,
                        provided_products,
                        sku,
                        contract,
                        account,
                        cert.serial,
                        pool_id,
                        provides_management,
                        cert.is_valid(),
                        quantity_used,
                        service_type,
                        service_level,
                        reasons,
                        pool_type,
                        date_formatter(cert.valid_range.begin()),
                        date_formatter(cert.valid_range.end()),
                        system_type,
                    )
                )
            else:
                consumed_statuses.append(
                    ConsumedStatus(
                        name,
                        provided_products,
                        sku,
                        contract,
                        account,
                        cert.serial,
                        pool_id,
                        provides_management,
                        cert.is_valid(),
                        quantity_used,
                        service_type,
                        roles,
                        service_level,
                        usage,
                        addons,
                        reasons,
                        pool_type,
                        date_formatter(cert.valid_range.begin()),
                        date_formatter(cert.valid_range.end()),
                        system_type,
                    )
                )
        return consumed_statuses

    # FIXME: Many None default values are suspicious. Type of some arguments is probably bool. Thus
    # default value should be False, not None.
    @staticmethod
    def get_available_pools(
        show_all: bool = None,
        on_date: datetime.datetime = None,
        no_overlap: bool = None,
        match_installed: bool = None,
        matches: str = None,
        service_level: str = None,
        future: str = None,
        after_date: datetime.datetime = None,
        page: int = 0,
        items_per_page: int = 0,
        iso_dates: bool = False,
    ) -> dict:
        """
        Get list of available pools
        :param show_all:
        :param on_date:
        :param no_overlap:
        :param match_installed:
        :param matches:
        :param service_level:
        :param future:
        :param after_date:
        :param page:
        :param items_per_page:
        :param iso_dates:
        :return:
        """

        # Values used for REST API calls and caching are bigger, because it makes using of cache and
        # API more efficient
        if show_all is not True:
            _page = int(page / 4)
            _items_per_page = 4 * items_per_page
        else:
            page = items_per_page = 0
            _page = _items_per_page = 0

        filter_options = {
            "show_all": show_all,
            "on_date": on_date,
            "no_overlap": no_overlap,
            "match_installed": match_installed,
            "matches": matches,
            "service_level": service_level,
            "future": future,
            "after_date": after_date,
            "page": _page,
            "items_per_page": _items_per_page,
        }

        # Try to get identity
        identity = inj.require(inj.IDENTITY)

        # Try to get available pools from cache
        cache = inj.require(inj.AVAILABLE_ENTITLEMENT_CACHE)
        available_pools = cache.get_not_obsolete_data(identity, filter_options)

        if len(available_pools) == 0:
            available_pools = managerlib.get_available_entitlements(
                get_all=show_all,
                active_on=on_date,
                overlapping=no_overlap,
                uninstalled=match_installed,
                filter_string=matches,
                future=future,
                after_date=after_date,
                page=_page,
                items_per_page=_items_per_page,
                iso_dates=iso_dates,
            )

            timeout = cache.timeout()

            data = {
                identity.uuid: {
                    "filter_options": filter_options,
                    "pools": available_pools,
                    "timeout": time.time() + timeout,
                }
            }
            cache.available_entitlements = data
            cache.write_cache()

        def filter_pool_by_service_level(pool_data: dict) -> bool:
            pool_level = ""
            if pool_data["service_level"]:
                pool_level = pool_data["service_level"]
            return service_level.lower() == pool_level.lower()

        if service_level is not None:
            available_pools = list(filter(filter_pool_by_service_level, available_pools))

        # When pagination result of available pools is requested, then reduce too long list
        if items_per_page > 0:
            # Reduce too long list to requested "page"
            lo_idx = (page * items_per_page) % _items_per_page
            hi_idx = ((page + 1) * items_per_page) % _items_per_page
            if hi_idx == 0:
                hi_idx = _items_per_page

            # Own filtering of the list
            available_pools = available_pools[lo_idx:hi_idx]

            # Add requested page and number of items per page to the result too
            for item in available_pools:
                item["page"] = page
                item["items_per_page"] = items_per_page

        return available_pools

    def validate_options(self, options: dict) -> None:
        if not set(["installed", "consumed", "available"]).issuperset(options["pool_subsets"]):
            raise exceptions.ValidationError(
                _(
                    'Error: invalid listing type provided.  Only "installed", '
                    '"consumed", or "available" are allowed'
                )
            )
        if options["show_all"] and "available" not in options["pool_subsets"]:
            raise exceptions.ValidationError(_("Error: --all is only applicable with --available"))
        elif options["on_date"] and "available" not in options["pool_subsets"]:
            raise exceptions.ValidationError(_("Error: --ondate is only applicable with --available"))
        elif options["service_level"] is not None and not set(["consumed", "available"]).intersection(
            options["pool_subsets"]
        ):
            raise exceptions.ValidationError(
                _("Error: --servicelevel is only applicable with --available or --consumed")
            )
        elif options["match_installed"] and "available" not in options["pool_subsets"]:
            raise exceptions.ValidationError(
                _("Error: --match-installed is only applicable with --available")
            )
        elif options["no_overlap"] and "available" not in options["pool_subsets"]:
            raise exceptions.ValidationError(_("Error: --no-overlap is only applicable with --available"))
        elif options["pool_only"] and not set(["consumed", "available"]).intersection(
            options["pool_subsets"]
        ):
            raise exceptions.ValidationError(
                _("Error: --pool-only is only applicable with --available and/or --consumed")
            )
        elif not self.identity.is_valid() and "available" in options["pool_subsets"]:
            raise exceptions.ValidationError(_("Error: this system is not registered"))

    def _unbind_ids(self, unbind_method: Callable, consumer_uuid: str, ids: list) -> tuple:
        """
        Method for unbinding entitlements
        :param unbind_method: unbindByPoolId or unbindBySerial
        :param consumer_uuid: UUID of consumer
        :param ids: List of serials or pool_ids
        :return: Tuple of two lists containing unbinded and not-unbinded subscriptions
        """
        success = []
        failure = []
        for id_ in ids:
            try:
                unbind_method(consumer_uuid, id_)
                success.append(id_)
            except connection.RestlibException as re:
                if re.code == 410:
                    raise
                failure.append(id_)
                log.error(re)
        return success, failure

    def remove_all_entitlements(self) -> dict:
        """
        Try to remove all entitlements
        :return: Result of REST API call
        """

        response = self.cp.unbindAll(self.identity.uuid)
        self.entcertlib.update()

        return response

    def remove_entitlements_by_pool_ids(self, pool_ids: list) -> tuple:
        """
        Try to remove entitlements by pool IDs
        :param pool_ids: List of pool IDs
        :return: List of serial numbers of removed subscriptions
        """

        removed_serials = []
        _pool_ids = utils.unique_list_items(pool_ids)  # Don't allow duplicates
        # FIXME: the cache of CertificateDirectory should be smart enough and refreshing
        # should not be necessary. I vote for i-notify to be used there somehow.
        self.entitlement_dir.refresh()
        pool_id_to_serials = self.entitlement_dir.list_serials_for_pool_ids(_pool_ids)
        removed_pools, unremoved_pools = self._unbind_ids(
            self.cp.unbindByPoolId, self.identity.uuid, _pool_ids
        )
        if removed_pools:
            for pool_id in removed_pools:
                removed_serials.extend(pool_id_to_serials[pool_id])
        self.entcertlib.update()

        return removed_pools, unremoved_pools, removed_serials

    def remove_entitlements_by_serials(self, serials: list) -> tuple:
        """
        Try to remove pools by Serial numbers
        :param serials: List of serial numbers
        :return: Tuple of two items: list of serial numbers of already removed subscriptions and list
            of not removed serials
        """

        _serials = utils.unique_list_items(serials)  # Don't allow duplicates
        removed_serials, unremoved_serials = self._unbind_ids(
            self.cp.unbindBySerial, self.identity.uuid, _serials
        )
        self.entcertlib.update()

        return removed_serials, unremoved_serials

    @staticmethod
    def reload() -> None:
        """
        This callback function is called, when there is detected any change in directory with entitlement
        certificates (e.g. certificate is installed or removed)
        """
        sorter = inj.require(inj.CERT_SORTER, on_date=None)
        status_cache = inj.require(inj.ENTITLEMENT_STATUS_CACHE)
        log.debug("Clearing in-memory cache of file %s" % status_cache.CACHE_FILE)
        status_cache.server_status = None
        sorter.load()

    def refresh(self, remove_cache: bool = False, force: bool = False) -> None:
        """
        Try to refresh entitlement certificate(s) from candlepin server
        :return: Report of EntCertActionInvoker
        """

        if remove_cache is True:
            # remove content_access cache, ensuring we get it fresh
            content_access = inj.require(inj.CONTENT_ACCESS_CACHE)
            if content_access.exists():
                content_access.remove()
            # Also remove the content access mode cache to be sure we display
            # SCA or regular mode correctly
            content_access_mode = inj.require(inj.CONTENT_ACCESS_MODE_CACHE)
            if content_access_mode.exists():
                content_access_mode.delete_cache()

        if force is True:
            # Force a regen of the entitlement certs for this consumer
            if not self.cp.regenEntitlementCertificates(self.identity.uuid, True):
                log.debug("Warning: Unable to refresh entitlement certificates; service likely unavailable")

        # FIXME: It looks like that the method update() always return None
        return self.entcertlib.update()
