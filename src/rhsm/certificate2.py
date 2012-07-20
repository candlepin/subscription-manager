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

import os
import base64
import zlib
import logging

log = logging.getLogger(__name__)

from datetime import datetime
import simplejson as json

from rhsm import _certificate

from rhsm.connection import safe_int
from rhsm.certificate import Extensions, OID, DateRange, GMT, \
        get_datetime_from_x509, parse_tags, CertificateException

REDHAT_OID_NAMESPACE = "1.3.6.1.4.1.2312.9"
ORDER_NAMESPACE = "4"

EXT_ORDER_NAME = "4.1"
EXT_CERT_VERSION = "6"
EXT_ENT_PAYLOAD = "7"

# Constants representing the type of certificates:
PRODUCT_CERT = 1
ENTITLEMENT_CERT = 2
IDENTITY_CERT = 3


class CertFactory(object):
    """
    Factory for creating certificate objects.

    Examines the incoming file or PEM text, parses the OID structure,
    from the server, and returns the correct implementation class.
    determines the type of certificate we're dealing with
    (entitlement/product), as well as the version of the certificate

    NOTE: Please use the factory methods that leverage this class in
    certificate.py instead of this class.
    """

    def create_from_file(self, path):
        """
        Create appropriate certificate object from a PEM file on disk.
        """
        return self._read_x509(_certificate.load(path), path)

    def create_from_pem(self, pem, path=None):
        """
        Create appropriate certificate object from a PEM string.
        """
        return self._read_x509(_certificate.load(pem=pem), path)

    def _read_x509(self, x509, path):
        if not x509:
            raise CertificateException("Error loading certificate")
        # Load the X509 extensions so we can determine what we're dealing with:
        try:
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
                return self._create_v1_cert(version, extensions, x509, path)
            if version.major == 2:
                return self._create_v2_cert(version, extensions, x509, path)

        except CertificateException, e:
            raise e
        except Exception, e:
            raise CertificateException(e.message)

    def _create_v1_cert(self, version, extensions, x509, path):

        cert_type = self._get_v1_cert_type(extensions)

        if cert_type == IDENTITY_CERT:
            return self._create_identity_cert(extensions, x509, path)
        elif cert_type == ENTITLEMENT_CERT:
            return self._create_v1_ent_cert(version, extensions, x509, path)
        elif cert_type == PRODUCT_CERT:
            return self._create_v1_prod_cert(version, extensions, x509, path)

    def _read_alt_name(self, x509):
        return x509.get_extension(name='subjectAltName')

    def _read_subject(self, x509):
        return x509.get_subject()

    def _create_identity_cert(self, extensions, x509, path):
        cert = IdentityCertificate(
                x509=x509,
                path=path,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                alt_name=self._read_alt_name(x509),
                subject=self._read_subject(x509),
            )
        return cert

    def _create_v1_prod_cert(self, version, extensions, x509, path):
        products = self._parse_v1_products(extensions)
        cert = ProductCertificate(
                x509=x509,
                path=path,
                version=version,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                products=products,
            )
        return cert

    def _create_v1_ent_cert(self, version, extensions, x509, path):
        order = self._parse_v1_order(extensions)
        content = self._parse_v1_content(extensions)
        products = self._parse_v1_products(extensions)

        cert = EntitlementCertificate(
                x509=x509,
                path=path,
                version=version,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                order=order,
                content=content,
                products=products,
            )
        return cert

    def _parse_v1_products(self, extensions):
        """
        Returns an ordered list of all the product data in the
        certificate.
        """
        products = []
        for prod_namespace in extensions.find('1.*.1'):
            oid = prod_namespace[0]
            root = oid.rtrim(1)
            product_id = oid[1]
            ext = extensions.branch(root)
            products.append(Product(
                id=product_id,
                name=ext.get('1'),
                version=ext.get('2'),
                architectures=ext.get('3'),
                provided_tags=parse_tags(ext.get('4')),
                ))
        return products

    def _parse_v1_order(self, extensions):
        order_extensions = extensions.branch(ORDER_NAMESPACE)
        order = Order(
                name=order_extensions.get('1'),
                number=order_extensions.get('2'),
                sku=order_extensions.get('3'),
                subscription=order_extensions.get('4'),
                quantity=order_extensions.get('5'),
                virt_limit=order_extensions.get('8'),
                socket_limit=order_extensions.get('9'),
                contract=order_extensions.get('10'),
                quantity_used=order_extensions.get('11'),
                warning_period=order_extensions.get('12'),
                account=order_extensions.get('13'),
                provides_management=order_extensions.get('14'),
                service_level=order_extensions.get('15'),
                service_type=order_extensions.get('16'),
                stacking_id=order_extensions.get('17'),
                virt_only=order_extensions.get('18')
            )
        return order

    def _parse_v1_content(self, extensions):
        content = []
        ents = extensions.find("2.*.1.1")
        for ent in ents:
            oid = ent[0]
            content_ext = extensions.branch(oid.rtrim(1))
            content.append(Content(
                name=content_ext.get('1'),
                label=content_ext.get('2'),
                quantity=content_ext.get('3'),
                flex_quantity=content_ext.get('4'),
                vendor=content_ext.get('5'),
                url=content_ext.get('6'),
                gpg=content_ext.get('7'),
                enabled=content_ext.get('8'),
                metadata_expire=content_ext.get('9'),
                required_tags=parse_tags(content_ext.get('10')),
            ))
        return content

    def _get_v1_cert_type(self, extensions):
        # Assume if there is an order name, it must be an entitlement cert:
        if EXT_ORDER_NAME in extensions:
            return ENTITLEMENT_CERT
        # If there is no order, but there are products, must be a product cert:
        elif len(extensions.find('1.*.1')) > 0:
            return PRODUCT_CERT
        # Otherwise we assume it's a plain identity certificate:
        else:
            return IDENTITY_CERT

    def _create_v2_cert(self, version, extensions, x509, path):
        # At this time, we only support v2 entitlement certificates:
        if not EXT_ENT_PAYLOAD in extensions:
            raise CertificateException("Unable to parse non-entitlement "
                    "v2 certificates")

        payload = self._decompress_payload(extensions[EXT_ENT_PAYLOAD])

        order = self._parse_v2_order(payload)
        content = self._parse_v2_content(payload)
        products = self._parse_v2_products(payload)

        cert = EntitlementCertificate(
                x509=x509,
                path=path,
                version=version,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                order=order,
                content=content,
                products=products,
            )
        return cert

    def _parse_v2_order(self, payload):
        sub = payload['subscription']
        order = payload['order']

        service_level = None
        service_type = None
        if 'service' in sub:
            service_level = sub['service'].get('level', None)
            service_level = sub['service'].get('type', None)

        return Order(
                name=sub['name'],
                number=order.get('number', None),
                sku=sub.get('sku', None),
                quantity=order.get('quantity', None),
                socket_limit=sub.get('sockets', None),
                contract=order.get('contract', None),
                quantity_used=payload.get('quantity', 1),
                warning_period=sub.get('warning', 0),
                account=order.get('account', None),
                provides_management=sub.get('management', False),
                service_level=service_level,
                service_type=service_type,
                stacking_id=sub.get('stacking_id', None),
                virt_only=sub.get('virt_only', False),
            )

    def _parse_v2_products(self, payload):
        """
        Returns an ordered list of all the product data in the
        certificate.
        """
        product_payload = payload['products']
        products = []
        for product in product_payload:

            products.append(Product(
                id=product['id'],
                name=product['name'],
                version=product.get('version', None),
                architectures=product.get('architectures', []),
                ))
            # TODO: skipping provided tags here, we don't yet generate
            # v2 product certs, we may never, which is the only place provided
            # tags can exist.
        return products

    def _parse_v2_content(self, payload):
        content = []
        for product in payload['products']:
            for c in product['content']:
                content.append(Content(
                    name=c['name'],
                    label=c['label'],
                    vendor=c.get('vendor', None),
                    url=c.get('path', None),
                    gpg=c.get('gpg_url', None),
                    enabled=c.get('enabled', True),
                    metadata_expire=c.get('metadata_expire', None),
                    required_tags=c.get('required_tags', []),
                ))
        return content

    def _decompress_payload(self, payload):
        """
        Certificate payloads arrive in base64 encoded zlib compressed strings
        of JSON.
        This method decodes, de-compressed, parses the JSON and returns the
        resulting dict.
        """
        try:
            decoded = base64.decodestring(payload)
            decompressed = zlib.decompress(decoded)
        except Exception, e:
            log.exception(e)
            raise CertificateException("Error decoding/decompressing "
                    "certificate payload.")
        return json.loads(decompressed)


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
    """ Parent class of all x509 certificate types. """
    def __init__(self, x509=None, path=None, version=None, serial=None, start=None,
            end=None):

        # The X509 M2crypto object for this certificate.
        # WARNING: May be None in tests
        self.x509 = x509

        # Full file path to the certificate on disk. May be None if the cert
        # hasn't yet been written to disk.
        self.path = path

        # Version of the certificate sent by Candlepin:
        self.version = version

        if serial is None:
            raise CertificateException("Certificate has no serial")

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

    def is_expired(self, on_date=None):
        gmt = datetime.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return self.valid_range.end() < gmt

    def __cmp__(self, other):
        if self.end < other.end:
            return -1
        if self.end > other.end:
            return 1
        return 0

    def write(self, path):
        """
        Write the certificate to disk.
        """
        f = open(path, 'w')
        f.write(self.x509.as_pem())
        f.close()
        self.path = path

    def delete(self):
        """
        Delete the file associated with this certificate.
        """
        if self.path:
            os.unlink(self.path)


class IdentityCertificate(Certificate):
    def __init__(self, alt_name=None, subject=None, **kwargs):
        Certificate.__init__(self, **kwargs)

        self.subject = subject
        self.alt_name = alt_name


class ProductCertificate(Certificate):
    def __init__(self, products=None, **kwargs):
        Certificate.__init__(self, **kwargs)
        # The products in this certificate. The first is treated as the
        # primary or "marketing" product.
        if products is None:
            products = []
        self.products = products


class EntitlementCertificate(ProductCertificate):

    def __init__(self, order=None, content=None, **kwargs):
        ProductCertificate.__init__(self, **kwargs)
        self.order = order
        self.content = content


class Product(object):
    """
    Represents the product information from a certificate.
    """
    def __init__(self, id=None, name=None, version=None, architectures=None,
            provided_tags=None):

        if name is None:
            raise CertificateException("Product missing name")
        if id is None:
            raise CertificateException("Product missing ID")

        self.id = id
        self.name = name
        self.version = version

        self.architectures = architectures
        # If this is sent in as a string split it, as the field
        # can technically be multi-valued:
        if isinstance(self.architectures, str):
            self.architectures = parse_tags(self.architectures)

        self.provided_tags = provided_tags
        if self.provided_tags is None:
            self.provided_tags = []

    def __eq__(self, other):
        return (self.id == other.id)


class Order(object):
    """
    Represents the order information for the subscription an entitlement
    originated from.
    """

    def __init__(self, name=None, number=None, sku=None, subscription=None,
            quantity=None, virt_limit=None, socket_limit=None,
            contract=None, quantity_used=None, warning_period=None,
            account=None, provides_management=None, service_level=None,
            service_type=None, stacking_id=None, virt_only=None):

        self.name = name
        self.number = number  # order number
        self.sku = sku  # aka the marketing product

        self.subscription = subscription  # seems to be unused

        # total quantity on the order:
        self.quantity = safe_int(quantity, None)  # rarely used

        # actual quantity used by this entitlement:
        self.quantity_used = safe_int(quantity_used, 1)

        self.virt_limit = virt_limit  # unused

        self.stacking_id = stacking_id

        self.socket_limit = safe_int(socket_limit, None)
        self.warning_period = safe_int(warning_period, 0)

        self.contract = contract
        self.account = account

        self.provides_management = provides_management or False

        self.service_level = service_level
        self.service_type = service_type

        self.virt_only = virt_only or False

    def __str__(self):
        return "<Order: name=%s number=%s sku=%s>" % \
                (self.name, self.number, self.sku)


class Content(object):

    def __init__(self, name=None, label=None, quantity=None, flex_quantity=None,
            vendor=None, url=None, gpg=None, enabled=None, metadata_expire=None,
            required_tags=None):

        if (name is None) or (label is None):
            raise CertificateException("Content missing name/label")

        self.name = name
        self.label = label
        self.vendor = vendor
        self.url = url
        self.gpg = gpg

        if (enabled not in (None, 0, 1, "0", "1")):
            raise CertificateException("Invalid content enabled setting: %s"
                % enabled)

        # Convert possible incoming None or string (0/1) to a boolean:
        # If enabled isn't specified in cert we assume True.
        self.enabled = True if \
                (enabled is None or enabled == "1" or enabled == True) \
                else False

        self.metadata_expire = metadata_expire
        self.required_tags = required_tags or []

        # Suspect both of these are unused:
        self.quantity = int(quantity) if quantity else None
        self.flex_quantity = int(flex_quantity) if flex_quantity else None

    def __eq__(self, other):
        return (self.label == other.label)

    def __str__(self):
        return "<Content: name=%s label=%s enabled=%s>" % \
                (self.name, self.label, self.enabled)
