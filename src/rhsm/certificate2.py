from __future__ import print_function, division, absolute_import

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
import base64
import logging
import os
import posixpath
import re
import six
import zlib

log = logging.getLogger(__name__)

from datetime import datetime, timedelta

from rhsm import _certificate

from rhsm.connection import safe_int
from rhsm.certificate import Extensions, OID, DateRange, GMT, \
        get_datetime_from_x509, parse_tags, CertificateException
from rhsm.pathtree import PathTree
from rhsm import ourjson as json

REDHAT_OID_NAMESPACE = "1.3.6.1.4.1.2312.9"
ORDER_NAMESPACE = "4"

EXT_ORDER_NAME = "4.1"
EXT_CERT_VERSION = "6"
EXT_ENT_PAYLOAD = "7"
EXT_ENT_TYPE = "8"

# Constants representing the type of certificates:
PRODUCT_CERT = 1
ENTITLEMENT_CERT = 2
IDENTITY_CERT = 3

CONTENT_ACCESS_CERT_TYPE = "OrgLevel"


class _CertFactory(object):
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
        try:
            pem = open(path, 'r').read()
        except IOError as err:
            raise CertificateException("Error loading certificate: %s" % err)
        return self._read_x509(_certificate.load(path), path, pem)

    def create_from_pem(self, pem, path=None):
        """
        Create appropriate certificate object from a PEM string.
        """
        if not pem:
            raise CertificateException("Empty certificate")
        return self._read_x509(_certificate.load(pem=pem), path, pem)

    def _read_x509(self, x509, path, pem):
        if not x509:
            if path is not None:
                raise CertificateException("Error loading certificate: %s" % path)
            elif pem is not None:
                raise CertificateException("Error loading certificate from string: %s" % pem)
            else:
                raise CertificateException("Error: none certificate data offered")
        # Load the X509 extensions so we can determine what we're dealing with:
        try:
            extensions = _Extensions2(x509)
            redhat_oid = OID(REDHAT_OID_NAMESPACE)
            # Trim down to only the extensions in the Red Hat namespace:
            extensions = extensions.branch(redhat_oid)
            # Check the certificate version, absence of the extension implies v1.0:
            cert_version_str = "1.0"
            if EXT_CERT_VERSION in extensions:
                cert_version_str = extensions[EXT_CERT_VERSION].decode('utf-8')

            version = Version(cert_version_str)
            if version.major == 1:
                return self._create_v1_cert(version, extensions, x509, path)
            if version.major == 3:
                return self._create_v3_cert(version, extensions, x509, path, pem)

        except CertificateException as e:
            raise e
        except Exception as e:
            log.exception(e)
            raise CertificateException(str(e))

    def _create_v1_cert(self, version, extensions, x509, path):

        cert_type = self._get_v1_cert_type(extensions)

        if cert_type == IDENTITY_CERT:
            return self._create_identity_cert(version, extensions, x509, path)
        elif cert_type == ENTITLEMENT_CERT:
            return self._create_v1_ent_cert(version, extensions, x509, path)
        elif cert_type == PRODUCT_CERT:
            return self._create_v1_prod_cert(version, extensions, x509, path)

    def _read_alt_name(self, x509):
        """Try to read subjectAltName from certificate"""
        alt_name = x509.get_extension(name='subjectAltName')
        # When certificate does not include subjectAltName, then
        # return emtpy string
        if alt_name is None:
            return ''
        else:
            return alt_name.decode('utf-8')

    def _read_issuer(self, x509):
        return x509.get_issuer()

    def _read_subject(self, x509):
        return x509.get_subject()

    def _create_identity_cert(self, version, extensions, x509, path):
        cert = IdentityCertificate(
                x509=x509,
                path=path,
                version=version,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                alt_name=self._read_alt_name(x509),
                subject=self._read_subject(x509),
                issuer=self._read_issuer(x509),
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
                subject=self._read_subject(x509),
                issuer=self._read_issuer(x509),
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
                subject=self._read_subject(x509),
                order=order,
                content=content,
                products=products,
                extensions=extensions,
                issuer=self._read_issuer(x509),
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
            product_data = {
                'name': ext.get('1'),
                'version': ext.get('2'),
                'architectures': ext.get('3'),
                'provided_tags': ext.get('4'),
                # not populated, only added for parity with
                # v3 product objects
                'brand_type': ext.get('5'),
                'brand_name': ext.get('6'),
            }
            for key, value in list(product_data.items()):
                if value is not None:
                    product_data[key] = value.decode('utf-8')
            product_data['provided_tags'] = parse_tags(product_data['provided_tags'])
            products.append(Product(id=product_id, **product_data))
        return products

    def _parse_v1_order(self, extensions):
        order_extensions = extensions.branch(ORDER_NAMESPACE)
        # TODO: implement reading syspurpose attributes: usage, roles and addons, when they are implemented
        order_data = {
            'name': order_extensions.get('1'),
            'number': order_extensions.get('2'),
            'sku': order_extensions.get('3'),
            'subscription': order_extensions.get('4'),
            'quantity': order_extensions.get('5'),
            'virt_limit': order_extensions.get('8'),
            'socket_limit': order_extensions.get('9'),
            'contract': order_extensions.get('10'),
            'quantity_used': order_extensions.get('11'),
            'warning_period': order_extensions.get('12'),
            'account': order_extensions.get('13'),
            'provides_management': order_extensions.get('14'),
            'service_level': order_extensions.get('15'),
            'service_type': order_extensions.get('16'),
            'stacking_id': order_extensions.get('17'),
            'virt_only': order_extensions.get('18'),
        }
        for key, value in list(order_data.items()):
            if value is not None:
                order_data[key] = value.decode('utf-8')
        order = Order(**order_data)
        return order

    def _parse_v1_content(self, extensions):
        content = []
        ents = extensions.find("2.*.*.1")
        for ent in ents:
            oid = ent[0].rtrim(1)
            content_ext = extensions.branch(oid)
            content_data = {
                'content_type': extensions.get(oid),
                'name': content_ext.get('1'),
                'label': content_ext.get('2'),
                'vendor': content_ext.get('5'),
                'url': content_ext.get('6'),
                'gpg': content_ext.get('7'),
                'enabled': content_ext.get('8'),
                'metadata_expire': content_ext.get('9'),
                'required_tags': content_ext.get('10'),
            }
            for key, value in list(content_data.items()):
                if value is not None:
                    content_data[key] = value.decode('utf-8')
            content_data['required_tags'] = parse_tags(content_data['required_tags'])
            content.append(Content(**content_data))
        return content

    def _get_v1_cert_type(self, extensions):
        # Assume if there is an order name, it must be an entitlement cert:
        if EXT_ORDER_NAME in extensions:
            return ENTITLEMENT_CERT
        # If there is no order, but there are products, must be a product cert:
        elif len(extensions.find('1.*.1', 1, True)) > 0:
            return PRODUCT_CERT
        # Otherwise we assume it's a plain identity certificate:
        else:
            return IDENTITY_CERT

    def _create_v3_cert(self, version, extensions, x509, path, pem):
        # At this time, we only support v3 entitlement certificates
        try:
            # this is only expected to be available on the client side
            entitlement_data = pem.split("-----BEGIN ENTITLEMENT DATA-----")[1]
            entitlement_data = entitlement_data.split("-----END ENTITLEMENT DATA-----")[0].strip()
        except IndexError:
            entitlement_data = None

        if entitlement_data:
            payload = self._decompress_payload(base64.b64decode(entitlement_data))
            order = self._parse_v3_order(payload)
            content = self._parse_v3_content(payload)
            products = self._parse_v3_products(payload)
            pool = self._parse_v3_pool(payload)
        else:
            order = None
            content = None
            products = None
            pool = None

        cert = EntitlementCertificate(
                x509=x509,
                path=path,
                version=version,
                extensions=extensions,
                serial=x509.get_serial_number(),
                start=get_datetime_from_x509(x509.get_not_before()),
                end=get_datetime_from_x509(x509.get_not_after()),
                subject=self._read_subject(x509),
                order=order,
                content=content,
                products=products,
                pool=pool,
                pem=pem,
                issuer=self._read_issuer(x509),
            )
        return cert

    def _parse_v3_order(self, payload):
        sub = payload['subscription']
        order = payload['order']

        service_level = None
        service_type = None
        if 'service' in sub:
            service_level = sub['service'].get('level', None)
            service_type = sub['service'].get('type', None)

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
                ram_limit=sub.get('ram', None),
                core_limit=sub.get('cores', None)
            )

    def _parse_v3_products(self, payload):
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
                brand_type=product.get('brand_type', None),
                brand_name=product.get('brand_name', None)
                ))
            # TODO: skipping provided tags here, we don't yet generate
            # v3 product certs, we may never, which is the only place provided
            # tags can exist.
        return products

    def _parse_v3_content(self, payload):
        content = []
        for product in payload['products']:
            for c in product['content']:
                content.append(Content(
                    content_type=c['type'],
                    name=c['name'],
                    label=c['label'],
                    vendor=c.get('vendor', None),
                    url=c.get('path', None),
                    gpg=c.get('gpg_url', None),
                    enabled=c.get('enabled', True),
                    metadata_expire=c.get('metadata_expire', None),
                    required_tags=c.get('required_tags', []),
                    arches=c.get('arches', []),
                ))
        return content

    def _parse_v3_pool(self, payload):
        pool = payload.get('pool', None)
        if pool:
            return Pool(id=pool['id'])
        return None

    def _decompress_payload(self, payload):
        """
        Certificate payloads arrive in zlib compressed strings
        of JSON.
        This method de-compresses and parses the JSON and returns the
        resulting dict.
        """
        try:
            decompressed = zlib.decompress(payload).decode('utf-8')
            return json.loads(decompressed)
        except Exception as e:
            log.exception(e)
            raise CertificateException("Error decompressing/parsing "
                    "certificate payload.")


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


class _Extensions2(Extensions):

    def _parse(self, x509):
        """
        Override parent method for an X509 object from the new C wrapper.
        """
        extensions = x509.get_all_extensions()
        for (key, value) in list(extensions.items()):
            oid = OID(key)
            self[oid] = value


class Certificate(object):
    """ Parent class of all x509 certificate types. """
    def __init__(self, x509=None, path=None, version=None, serial=None, start=None,
            end=None, subject=None, pem=None, issuer=None):

        # The rhsm._certificate X509 object for this certificate.
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
        self.pem = pem

        self.subject = subject
        self.issuer = issuer

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

    def __lt__(self, other):
        return self.end < other.end

    def __le__(self, other):
        return self.end < other.end

    def __gt__(self, other):
        return self.end > other.end

    def __ge__(self, other):
        return self.end > other.end

    def __eq__(self, other):
        return self.serial == other.serial

    def __ne__(self, other):
        return self.serial != other.serial

    def __hash__(self):
        return self.serial

    def write(self, path):
        """
        Write the certificate to disk.
        """
        f = open(path, 'w')
        # if we were given the original pem, preserve it
        # ie for certv3 detached format.
        if self.pem is not None:
            f.write(self.pem)
        else:
            f.write(self.x509.as_pem())
        f.close()
        self.path = path

    def delete(self):
        """
        Delete the file associated with this certificate.
        """
        if self.path:
            os.unlink(self.path)
        else:
            raise CertificateException('Certificate has no path, cannot delete.')


class IdentityCertificate(Certificate):
    def __init__(self, alt_name=None, **kwargs):
        Certificate.__init__(self, **kwargs)
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

    def __init__(self, order=None, content=None, pool=None, extensions=None, **kwargs):
        ProductCertificate.__init__(self, **kwargs)
        self.order = order
        self.content = content
        self.pool = pool
        self.extensions = extensions
        self._path_tree_object = None

    @property
    def entitlement_type(self):
        if self.extensions.get(EXT_ENT_TYPE):
            return self.extensions.get(EXT_ENT_TYPE).decode('utf-8')
        else:
            return 'Basic'

    @property
    def _path_tree(self):
        """
        :return:    PathTree object built from this cert's extensions
        :rtype:     rhsm.pathtree.PathTree

        :raise: AttributeError if self.version.major < 3
        """
        # This data was not present in certificates prior to v3.
        if self.version.major < 3:
            raise AttributeError(
                'path tree not used for v%d certs' % self.version.major)
        if not self._path_tree_object:
            # generate and cache the tree
            data = self.extensions[EXT_ENT_PAYLOAD]
            if not data:
                raise AttributeError("Certificate has empty entitlement data extension")
            self._path_tree_object = PathTree(data)
        return self._path_tree_object

    @property
    def provided_paths(self):
        paths = []
        self._path_tree.build_path_list(paths)
        return paths

    def is_expiring(self, on_date=None):
        gmt = datetime.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        warning_time = timedelta(days=int(self.order.warning_period))
        return self.valid_range.end() - warning_time < gmt

    def check_path(self, path):
        """
        Checks the given path against the list of entitled paths as encoded in
        extensions. See PathTree for more detailed docs.

        :param path:    path to which access is being requested
        :type  path:    basestring

        :return:    True iff the path matches, else False
        :rtype:     bool

        :raise:    ValueError when self.version.major < 3
        """

        # squash double '//' if we get it in a content path
        # NOTE: according to http://tools.ietf.org/html/rfc3986#section-3.3
        # I think this technically changes the semantics of the url
        path = posixpath.normpath(path)
        if self.version.major < 3:
            return self._check_v1_path(path)
        else:
            return self._path_tree.match_path(path)

    def _check_v1_path(self, path):
        """
        Check the requested path against a v1 certificate

        :param path:    requested path
        :type  path:    basestring
        :return:    True iff the path matches, else False
        :rtype:     bool
        """
        path = path.strip('/')
        valid = False
        for ext_oid, oid_url in list(self.extensions.items()):
            oid_url = oid_url.decode('utf-8')
            # if this is a download URL
            if ext_oid.match(OID('2.')) and ext_oid.match(OID('.1.6')):
                if self._validate_v1_url(oid_url, path):
                    valid = True
                    break
        return valid

    @staticmethod
    def _validate_v1_url(oid_url, dest):
        """
        Determines if the destination URL matches the OID's URL.

        Swaps out all $ variables (e.g. $basearch, $version) for a reg ex
        wildcard in that location. For example, the following entitlement:
          content/dist/rhel/server/$version/$basearch/os

        Should allow any value for the variables:
          content/dist/rhel/server/.+?/.+?/os

        :param oid_url: path associated with an entitlement OID, as pulled from
                        the cert's extensions.
        :type  oid_url: basestring
        :param dest:    path requested by a client
        :type  dest:    basestring

        :return: True iff the OID permits the destination else False
        :rtype:  bool
        """
        # Remove initial and trailing '/', and substitute the $variables for
        # equivalent regular expressions in oid_url.
        oid_re = re.sub(r'\$[^/]+(/|$)', '[^/]+/', oid_url.strip('/'))
        return re.match(oid_re, dest) is not None

    def delete(self):
        """
        Override parent to also delete certificate key.
        """
        Certificate.delete(self)

        # Can assume we have a path here, super method would have thrown
        # Exception if we didn't:
        key_path = self.key_path()
        os.unlink(key_path)

    def key_path(self):
        """
        Returns the full path to the cert key's pem.
        """
        dir_path, cert_filename = os.path.split(self.path)
        try:
            key_filename = "%s-key.%s" % tuple(cert_filename.rsplit(".", 1))
        except TypeError as e:
            log.exception(e)
            raise CertificateException("Entitlement certificate path \"%s\" is not in "
                                       "in the expected format so the key file path "
                                       "could not be based on it." % self.path)
        key_path = os.path.join(dir_path, key_filename)
        return key_path


class Product(object):
    """
    Represents the product information from a certificate.
    """
    def __init__(self, id=None, name=None, version=None, architectures=None,
            provided_tags=None, brand_type=None, brand_name=None):

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
        if isinstance(self.architectures, six.string_types):
            self.architectures = parse_tags(self.architectures)
        if self.architectures is None:
            self.architectures = []

        self.provided_tags = provided_tags
        if self.provided_tags is None:
            self.provided_tags = []

        self.brand_type = brand_type
        self.brand_name = brand_name

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
            service_type=None, stacking_id=None, virt_only=None,
            ram_limit=None, core_limit=None, roles=None, usage=None,
            addons=None):

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
        self.usage = usage
        self.roles = roles
        self.addons = addons

        self.virt_only = virt_only or False

        self.ram_limit = safe_int(ram_limit, None)
        self.core_limit = safe_int(core_limit, None)

    def __str__(self):
        return "<Order: name=%s number=%s sku=%s>" % \
                (self.name, self.number, self.sku)


class Content(object):

    def __init__(self, content_type=None, name=None, label=None, vendor=None, url=None,
            gpg=None, enabled=None, metadata_expire=None, required_tags=None, arches=None):

        if (name is None) or (label is None):
            raise CertificateException("Content missing name/label")

        self.content_type = content_type
        self.name = name
        self.label = label
        self.vendor = vendor
        self.url = url
        self.gpg = gpg

        if not content_type:
            raise CertificateException("Content does not have a type set.")

        if (enabled not in (None, 0, 1, "0", "1")):
            raise CertificateException("Invalid content enabled setting: %s"
                % enabled)

        # Convert possible incoming None or string (0/1) to a boolean:
        # If enabled isn't specified in cert we assume True.
        self.enabled = False
        if enabled is None or enabled == "1" or enabled is True:
            self.enabled = True

        self.metadata_expire = metadata_expire
        self.required_tags = required_tags or []

        self.arches = arches or []

    def __eq__(self, other):
        return isinstance(other, self.__class__) and (self.label == other.label)

    def __str__(self):
        return "<Content: content_type=%s name=%s label=%s enabled=%s>" % \
                (self.content_type, self.name, self.label, self.enabled)

    def __hash__(self):
        return hash(self.label)


class Pool(object):
    """
    Represents the pool an entitlement originates from.
    """
    def __init__(self, id=None):
        if id is None:
            raise CertificateException("Pool is missing ID")
        self.id = id

    def __eq__(self, other):
        return (self.id == other.id)
