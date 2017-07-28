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

import logging

from subscription_manager import injection as inj
from .certificate_filter import EntitlementCertificateFilter
from dateutil.tz import tzlocal
from .methods import get_available_entitlements
from .pool_wrapper import PoolWrapper

log = logging.getLogger(__name__)

def format_date(dt):
    if not dt:
        return ""
    try:
        return dt.astimezone(tzlocal()).strftime("%x")
    except ValueError:
        log.warn("Datetime does not contain timezone information")
        return dt.strftime("%x")

class EntitlementService(object):
    def __init__(self):
        self.identity = inj.require(inj.IDENTITY)
        self.sorter = inj.require(inj.CERT_SORTER)
        self.pooltype_cache = inj.require(inj.POOLTYPE_CACHE)
        self.entitlement_dir = inj.require(inj.ENT_DIR)

    def get_status(self):
        system_is_registered = self.identity.is_valid()
        overall_status = system_is_registered \
                         and self.sorter.get_system_status() \
                         or "Unknown"

        status = 1
        if system_is_registered and self.sorter.is_valid():
            status = 0

        reasons = system_is_registered \
                  and self.sorter.reasons.get_name_message_map() \
                  or {}

        return {"status": status,
                "reasons": reasons,
                "overall_status": overall_status}

    def get_pools(self,**kwargs):
        #return self.get_consumed_pools()
        return self.get_available_pools(**kwargs)

    def get_available_pools(self, matches=None, service_level=None, no_overlap=False, on_date=None):
        system_is_registered = self.identity.is_valid()
        if not system_is_registered:
            return []

        if on_date:
            try:
                # doing it this ugly way for pre python 2.5
                on_date = datetime.datetime(
                    *(strptime(on_date, '%Y-%m-%d')[0:6]))
            except Exception:
                # Translators: dateexample is current date in format like 2014-11-31
                msg = _("Date entered is invalid. Date should be in YYYY-MM-DD format (example: {dateexample})")
                dateexample = strftime("%Y-%m-%d", localtime())
                raise Exception(msg.format(dateexample=dateexample))

        epools = get_available_entitlements(get_all=True,
                                            active_on=on_date,
                                            overlapping=no_overlap,
                                            uninstalled=False,
                                            filter_string=matches)
        # Filter certs by service level, if specified.
        # Allowing "" here.
        if service_level is not None:
            epools = self._filter_pool_json_by_service_level(epools, service_level)

        def wrapp_pool(pool):
            #print(pool.keys())
            machine_type = PoolWrapper(pool).is_virt_only() and "Virtual" \
                           or "Physical"
            result = { "subscription_name": pool['productName'] or "",
                       "provides": pool['providedProducts'] or [],
                       "sku":"",
                       "contract": pool['contractNumber'] or "",
                       "account": "",
                       "serial": "",
                       "pool_id": pool['id'],
                       "provides_management": pool.get('management_enabled',False),
                       "active": True,
                       "quantity_used": pool['quantity'] or 0,
                       "service_level": pool['service_level'] or "",
                       "service_type": pool['service_type'] or "",
                       "subscription_type": self.pooltype_cache.get(pool['id']) or "",
                       "starts":"", # format_date(pool['endDate']),
                       "ends": "", #format_date(pool['endDate']),
                       "system_type": machine_type}
            return result

        pools_data = map(wrapp_pool,epools)
        return pools_data

    def get_consumed_pools(self, matches=None, service_level=None):
        def no_filter(x):
            return True

        certs_filter = (service_level is not None or matches is not None) \
                       and EntitlementCertificateFilter(filter_string=matches,
                                                        service_level=service_level).match \
                       or no_filter

        certs = filter(certs_filter, self.entitlement_dir.list())
        cert_reasons_map = self.sorter.reasons.get_subscription_reasons_map()

        def get_cert_reasons(cert):
            if not self.sorter.are_reasons_supported():
                return ["Subscription management service doesn't support Status Details",]
            cert_subject = getattr(cert,"subject",{})
            reasons = ('CN' in cert_subject) and cert_reasons_map[cert_subject['CN']] \
                      or (cert in self.sorter.valid_entitlement_certs) and ["Subscription is current",] \
                      or (cert.valid_rande.ent() < datatime.datetime.now(GMT())) and ["Subscription is expired",] \
                      or ["Subscription has not begun",]
            
            return reasons

        def get_cert_data(cert):
            order = cert.order or Object()
            cert_subject = getattr(cert,"subject",{}) or {}
            pool_id = getattr(order,"pool_id","") or ""
            result= {"subscription_name": getattr(order,"name","") or "",
                     "provides": [p.name for p in cert.products],
                     "sku": getattr(order,"sku","") or "",
                     "contract": getattr(order,"contract","") or "",
                     "account": getattr(order,"account","") or "",
                     "serial": getattr(order,"serial","") or "",
                     "pool_id":  pool_id,
                     "provides_management": getattr(order,"provides_management",False),
                     "active": cert.is_valid(),
                     "quantity_used": getattr(order,"quantity_used",0) or 0,
                     "service_level": getattr(order,"service_level","") or "",
                     "service_type":  getattr(order,"service_type","") or "",
                     "status_detail": get_cert_reasons(cert),
                     "subscription_type": ('CN' in cert_subject) \
                                           and self.pooltype_cache.get(pool_id) \
                                           or "",
                     "starts": format_date(cert.valid_range.begin()),
                     "ends":  format_date(cert.valid_range.end()),
                     "system_type": getattr(order,"virt_only",False) and "Virtual" or "Physical"}
            return result

        cert_data = map(get_cert_data,certs)
        return cert_data
