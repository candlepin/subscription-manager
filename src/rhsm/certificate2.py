#
# Copyright (c) 2012 Red Hat, Inc.
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

from M2Crypto import X509

from rhsm.connection import safe_int
from rhsm.certificate import Extensions, OID, DateRange, GMT, \
        get_datetime_from_x509

REDHAT_OID_NAMESPACE = "1.3.6.1.4.1.2312.9"
ORDER_NAMESPACE = "4"

EXT_ORDER_NAME = "4.1"
EXT_CERT_VERSION = "6"

# Constants representing the type of certificates:
PRODUCT_CERT = 1
ENTITLEMENT_CERT = 2

class CertFactory(object):
    """
    Factory for creating certificate objects.

    Examines the incoming file or PEM text, parses the OID structure,
    determines the type of certificate we're dealing with
    (entitlement/product), as well as the version of the certificate
    from the server, and returns the correct implementation class.
    """

    def create_from_file(self, path):
        """
        Create appropriate certificate object from a PEM file on disk.
        """
        if from_file:
            f = open(from_file)
            contents = f.read()
            f.close()
        return self.create_from_pem(contents)

    def create_from_pem(self, pem):
        """
        Create appropriate certificate object from a PEM string.
        """
        # Load the X509 extensions so we can determine what we're dealing with:
        x509 = X509.load_cert_string(pem)
        extensions = Extensions(x509)
        redhat_oid = OID(REDHAT_OID_NAMESPACE)
        # Trim down to only the extensions in the Red Hat namespace:
        extensions = extensions.ltrim(len(redhat_oid))

        # Check the certificate version, absence of the extension implies v1.0:
        cert_version_str = "1.0"
        if EXT_CERT_VERSION in extensions:
            cert_version_str = extensions[EXT_CERT_VERSION]

        version = Version(cert_version_str)
        if version.major == 1:
            return self._create_v1_cert(version, extensions, x509)
        return cert

    def _create_v1_cert(self, version, extensions, x509):

        order_extensions = extensions.branch(ORDER_NAMESPACE)
        print order_extensions
        order = Order(
                name=order_extensions.get('1'),
                number=order_extensions.get('2'),
                sku=order_extensions.get('3'),
                subscription=order_extensions.get('4'),
                quantity=safe_int(order_extensions.get('5')),
                virt_limit=order_extensions.get('8'),
                socket_limit=order_extensions.get('9'),
                contract_number=order_extensions.get('10'),
                quantity_used=order_extensions.get('11'),
                warning_period=order_extensions.get('12'),
                account_number=order_extensions.get('13'),
                provides_management=order_extensions.get('14'),
                support_level=order_extensions.get('15'),
                support_type=order_extensions.get('16'),
                stacking_id=order_extensions.get('17'),
                virt_only=order_extensions.get('18')
            )

        cert_type = self._get_cert_type(extensions)
        if cert_type == ENTITLEMENT_CERT:
            cert = EntitlementCertificate1(
                    version=version,
                    serial=x509.get_serial_number(),
                    start=get_datetime_from_x509(x509.get_not_before()),
                    end=get_datetime_from_x509(x509.get_not_after()),
                    order=order,
                )
        elif cert_type == PRODUCT_CERT:
            cert = ProductCertificate1(
                    version=version,
                    serial=x509.get_serial_number(),
                    start=get_datetime_from_x509(x509.get_not_before()),
                    end=get_datetime_from_x509(x509.get_not_after()),
                )
        return cert

    def _get_cert_type(self, extensions):
        # Assume if there is an order name, it must be an entitlement cert:
        if EXT_ORDER_NAME in extensions:
            return ENTITLEMENT_CERT
        else:
            return PRODUCT_CERT
        # TODO: as soon as we have a v2 cert to play with, we need to look
        # for the new json OID, decompress it, parse it, and then look for an
        # order namespace in that as well.


class Version(object):
    """ Small wrapper for version string comparisons. """
    def __init__(self, version_str):
        self.version_str = version_str
        self.segments = version_str.split(".")
        for i in range(len(self.segments)):
            self.segments[i] = int(self.segments[i])

        self.major = self.segments[0]
        self.minor = 0
        if len(self.segments) > 1:
            self.minor = self.segments[1]

    # TODO: comparator might be useful someday
    def __str__(self):
        return self.version_str


class Certificate(object):
    """ Parent class of all certificate types. """
    def __init__(self, version=None, serial=None, start=None, end=None):
        # Version of the certificate sent by Candlepin:
        self.version = version

        self.serial = serial

        # Certificate start/end datetimes:
        self.start = start
        self.end = end

        self.valid_range = DateRange(self.start, self.end)

    def is_valid(self, on_date=None):
        gmt = datetime.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return self.valid_range.has_date(gmt)


class ProductCertificate1(Certificate):
    pass


class EntitlementCertificate1(Certificate):

    def __init__(self, order=None, **kwargs):
        Certificate.__init__(self, **kwargs)
        self.order = order


class ProductCertificate2(Certificate):
    pass


class EntitlementCertificate2(Certificate):
    pass


class Order(object):
    """
    Represents the order information for the subscription an entitlement
    originated from.
    """

    def __init__(self, name, number, sku, subscription, quantity,
            virt_limit, socket_limit, contract_number,
            quantity_used, warning_period, account_number,
            provides_management, support_level, support_type,
            stacking_id, virt_only):

        self.name = name
        self.number = number # order number
        self.sku = sku
        self.subscription = subscription

        # This is the total quantity on the order:
        self.quantity = quantity

        self.virt_limit = virt_limit
        self.socket_limit = socket_limit
        self.contract_number = contract_number

        # The actual quantity used by this entitlement:
        self.quantity_used = quantity_used

        self.warning_period = warning_period
        self.account_number = account_number
        self.provides_management = provides_management
        self.support_level = support_level
        self.support_type = support_type
        self.stacking_id = stacking_id
        self.virt_only = virt_only


class CertificateException(Exception):
    pass

# Maps a major cert version to the class implementations to use for
# each certificate type:
# TODO: may not be needed if we can go to just one set of classes
VERSION_IMPLEMENTATIONS = {
    1: {
        ENTITLEMENT_CERT: EntitlementCertificate1,
        PRODUCT_CERT: ProductCertificate1,
    },
    2: {
        ENTITLEMENT_CERT: EntitlementCertificate2,
        PRODUCT_CERT: ProductCertificate2,
    },
}

