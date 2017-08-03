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
import dbus
import json
import logging

from rhsmlib.dbus import constants, base_object, util, dbus_utils
from rhsmlib.services.products import InstalledProducts

from subscription_manager.injectioninit import init_dep_injection

init_dep_injection()

log = logging.getLogger(__name__)


class ProductsDBusObject(base_object.BaseObject):
    """
    A D-Bus object interacting with subscription-manager to list
    all installed products.
    """
    default_dbus_path = constants.PRODUCTS_DBUS_PATH
    interface_name = constants.PRODUCTS_INTERFACE

    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(ProductsDBusObject, self).__init__(conn=conn, object_path=object_path, bus_name=bus_name)

    @util.dbus_service_method(
        constants.PRODUCTS_INTERFACE,
        in_signature='sa{sv}',
        out_signature='s')
    @util.dbus_handle_exceptions
    def ListInstalledProducts(self, filter_string, proxy_options, sender=None):

        # FIXME: it is probably not necessary to reinitialize whole deep injection here.
        # We reinitialize CertSorter here for following reason. When new product certificate
        # is installed (or existing is removed), then this change is not propagated to
        # CertSorter and calling installed_products.list(filter_string) without reinitialization
        # of dependency injection would return old (cached) list of installed products.
        init_dep_injection()

        self.ensure_registered()
        filter_string = dbus_utils.dbus_to_python(filter_string, str)

        cp = self.build_uep(proxy_options, proxy_only=True)

        installed_products = InstalledProducts(cp)

        try:
            response = installed_products.list(filter_string)
        except Exception as err:
            raise dbus.DBusException(str(err))

        return json.dumps(response)
