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

log = logging.getLogger(__name__)

class EntitlementService(object):
    def __init__(self):
        self.identity = inj.require(inj.IDENTITY)
        self.sorter = inj.require(inj.CERT_SORTER)

    def get_status(self):
        system_is_registered = self.identity.is_valid()
        overall_status = system_is_registered \
                         and self.sorter.get_system_status() \
                         or "Unknown"

        result = 1
        if system_is_registered and self.sorter.is_valid():
            result = 0

        reasons = system_is_registered \
                  and self.sorter.reasons.get_name_message_map() \
                  or {}

        return {"status": result,
                "reasons": reasons,
                "overall_status": overall_status}

    def get_pools(self,**kwargs):
        return self.get_consumed_pools()

    def get_available_pools(self, matches=None, service_level=None):
        pass

    def get_consumed_pools(self, matches=None, service_level=None):

        def no_filter(x):
            return True

        certs_filter = (service_level is not None or matches is not None) \
                       and EntitlementCertificateFilter(filter_string=matches,
                                                        service_level=service_level).match \
                       or no_filter

        certs = filter(certs_filter, self.entitlement_dir.list())
        def get_cert_data(cert):
            result= {"subscription_name":"",
                     "provides": [],
                     "sku": "",
                     "contract":0,
                     "account": "",
                     "serial": "",
                     "pool_id": "",
                     "provides_management": false,
                     "active": false,
                     "quantity_used": 0,
                     "service_level": "",
                     "service_type":  "",
                     "status_detail": "",
                     "subscription_type": "",
                     "starts": "",
                     "ends":  "",
                     "system_type": ""}
            return result
                
        return map(get_cert_data,certs)
