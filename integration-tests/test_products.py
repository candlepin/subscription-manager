# Copyright (c) 2025 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

from constants import RHSM, RHSM_PRODUCTS, TEST_PRODUCT_CERT_PATHS, RHSM_PRODUCT_CERT_DIRS
from utils import loop_until, installed_products, product_ids_in_dir
import json
import logging
import pytest
import shutil
from pathlib import Path
from funcy import first, cat

logger = logging.getLogger(__name__)

"""
Integration test for DBus RHSM Products Object.

See https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html#products
for more details.

Main usecases are presented in this file.
"""

# each call uses standard english locale
locale = "en_US.UTF-8"


def test_products_list_installed_products(any_candlepin, subman, test_config):
    """
    https://www.candlepinproject.org/docs/subscription-manager/dbus_objects.html
    a method Products.ListInstalledProducts

    - The method returns a list of installed products.
    - it is a content of /etc/pki/product* directories.

    This test verifies tha DBus method Products/ListIntalledProducts returns a list of installed products.
    """
    subman.register(
        username=test_config.get("candlepin", "username"),
        password=test_config.get("candlepin", "password"),
        org=test_config.get("candlepin", "org"),
    )
    loop_until(lambda: subman.is_registered)

    # copy product certificate to ensure that at least one exists in the dir /etc/pki/product
    for src_cert_path in TEST_PRODUCT_CERT_PATHS:
        dst_cert_path = Path("/etc/pki/product") / src_cert_path.name
        shutil.copyfile(src_cert_path, dst_cert_path)

    proxy = RHSM.get_proxy(RHSM_PRODUCTS)
    response = json.loads(proxy.ListInstalledProducts("", {}, locale))
    #
    # [["Red Hat Enterprise Linux for x86_64 Beta", "486", "10.1 Beta", "x86_64", "unknown", [], "", ""]]
    #

    def values_with_keys(product_values: list[str]) -> dict[str, str]:
        """
        Convert into a dict using given keys.
        It takes just the first keys in a list
         - ie. it ignores the rest of the list of values
        """
        keys_in_response = ("Product Name", "Product ID", "Version", "Arch")
        return dict(zip(keys_in_response, product_values))

    products_in_response = [values_with_keys(product_values) for product_values in response]
    product_ids_in_config_dirs = list(cat(product_ids_in_dir(certdir) for certdir in RHSM_PRODUCT_CERT_DIRS))
    products = installed_products(subman)

    # a content of product directories is the main source of the truth
    assert set(product_ids_in_config_dirs) == set(
        [int(product["Product ID"]) for product in products_in_response]
    )
    assert set(product_ids_in_config_dirs) == set([int(product["Product ID"]) for product in products])

    # subscription-manager return the same list of installed products
    assert len(products) == len(products_in_response)
    for product_from_dbus_response, product_from_subman_response in zip(
        sorted(products_in_response, key=lambda p: p.get("Product ID", "")),
        sorted(products, key=lambda p: p.get("Product ID", "")),
    ):
        assert product_from_dbus_response == product_from_subman_response


@pytest.mark.xfail(
    reason="a testware support for dbus signals listening is not implemented yet - see PR #3585"
)
def test_products_signal_installed_products_changed(any_candlepin, subman, test_config):
    """
    We will install a package from High Availability product - spausedd
    The package is not installed yet and the product is not installed too.
    - ie. it is the first package from this product to install ever

    yum install spausedd --enablerepo='rhel-*-for-x86_64-highavailability-beta-rpms' --disablerepo='beaker*' \
        --disablerepo='testing-farm*'

    After the installation is done
       - new product cert appears in /etc/pki/product/
       - a DBus signal InstalledProductsChanged is emitted
    """

    subman.register(
        username=test_config.get("candlepin", "username"),
        password=test_config.get("candlepin", "password"),
        org=test_config.get("candlepin", "org"),
    )
    loop_until(lambda: subman.is_registered)

    # testing certificates are in the same dir as test files (in a directory 'files/product')
    src_cert_path = Path(__file__).parent / first(test_config.get("candlepin", "product_certs"))
    dst_cert_path = Path("/etc/pki/product") / src_cert_path.name

    # remove the test certificate - if already installed
    dst_cert_path.unlink(missing_ok=True)

    products_before = installed_products(subman)

    # copy product certificate to ensure that at least one exists in the dir /etc/pki/product
    shutil.copyfile(src_cert_path, dst_cert_path)

    products_after = installed_products(subman)
    assert len(products_after) > len(products_before)

    # TODO - to write an assert a dbus signal appears
    # - after dbus events monitor support is available in the testware
    dst_cert_path.unlink()
