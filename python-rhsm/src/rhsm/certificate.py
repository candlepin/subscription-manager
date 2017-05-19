from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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

"""
Contains classes for working with x.509 certificates.

Several of the classes in this module are now marked deprecated in favor
of their new counterparts in certificate2 module. However, rather than
depending on either specifically, you can use the create methods below to
automatically create the correct object for any given certificate.

Eventually the deprecated classes below will be removed, and the new classes
will be relocated into this module.
"""
import dateutil
import os
import re
from datetime import datetime as dt
from datetime import tzinfo, timedelta
from rhsm import _certificate
import logging
import warnings

log = logging.getLogger(__name__)


# Regex used to scan for OIDs:
OID_PATTERN = re.compile('([0-9]+\.)+[0-9]+:')


# Regex used to parse OID values such as:
#    0:d=0  hl=2 l=   3 prim: UTF8STRING        :2.0
VALUE_PATTERN = re.compile('.*prim:\s(\w*)\s*:*(.*)')


# NOTE: These factory methods create new style certificate objects from
# the certificate2 module. They are placed here to abstract the fact that
# we're using two modules for the time being. Eventually the certificate2 code
# should be moved here.
def create_from_file(path):
    from rhsm.certificate2 import _CertFactory  # prevent circular deps
    return _CertFactory().create_from_file(path)


def create_from_pem(pem):
    from rhsm.certificate2 import _CertFactory  # prevent circular deps
    return _CertFactory().create_from_pem(pem)


def parse_tags(tag_str):
    """
    Split a comma separated list of tags from a certificate into a list.
    """
    tags = []
    if tag_str:
        tags = tag_str.split(",")
    return tags


class UTC(tzinfo):
    """UTC"""

    _ZERO = timedelta(0)

    def utcoffset(self, dt):
        return self._ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self._ZERO


def get_datetime_from_x509(date):
    return dateutil.parser.parse(date)


def deprecated(func):
    """
    A decorator that marks a function as deprecated. This will cause a
    warning to be emitted any time that function is used by a caller.
    """
    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function: %s" % func.__name__,
                category=DeprecationWarning)
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


class Certificate(object):
    """
    Represents and x.509 certificate.

    :ivar x509: The :obj:`X509` backing object.
    :type x509: :class:`X509`
    :ivar __ext: A dictionary of extensions `OID`:value
    :type __ext: dict of :obj:`Extensions`
    """

    @deprecated
    def __init__(self, content=None):
        """
        :param content: The (optional) PEM encoded content.
        :type content: str
        """
        self._update(content)

    def _update(self, content):
        if content:
            x509 = _certificate.load(pem=content)
            if x509 is None:
                raise CertificateException("Error loading certificate")
        else:
            x509 = _certificate.X509()
        self.__ext = Extensions(x509)
        self.x509 = x509

        self.subj = self.x509.get_subject()
        self.serial = self.x509.get_serial_number()

        self.altName = x509.get_extension(name='subjectAltName')

    def serialNumber(self):
        """
        Get the serial number

        :return: The x.509 serial number
        :rtype:  str
        """
        return self.serial

    def subject(self):
        """
        Get the certificate subject.

        note: Missing NID mapping for UID added to patch openssl.

        :return: A dictionary of subject fields.
        :rtype: dict
        """
        return self.subj

    def alternateName(self):
        """
        Return the alternate name of the certificate.

        :return: A string representation of the alternate name
        :rtype: str
        """
        return self.altName

    def validRange(self):
        """
        Get the valid date range.

        :return: The valid date range.
        :rtype: :class:`DateRange`
        """
        return DateRange(get_datetime_from_x509(self.x509.get_not_before()),
                get_datetime_from_x509(self.x509.get_not_after()))

    def valid(self, on_date=None):
        """
        Get whether the certificate is valid based on date.

        :return: True if valid.
        :rtype: boolean
        """
        valid_range = self.validRange()
        gmt = dt.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return valid_range.has_date(gmt)

    def expired(self, on_date=None):
        """
        Get whether the certificate is expired based on date.

        :return: True if valid.
        :rtype: boolean
        """
        valid_range = self.validRange()
        gmt = dt.utcnow()
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return valid_range.end() < gmt

    def bogus(self):
        """
        Get whether the certificate contains bogus data or is otherwise unsuitable.

        The certificate may be valid but still be considered bogus.

        :return: List of reasons if bogus
        :rtype: list
        """
        return []

    def extensions(self):
        """
        Get custom extensions.

        :return: An extensions object.
        :rtype: :class:`Extensions`
        """
        return self.__ext

    # TODO: This looks like it should be in the c-tor:
    def read(self, pem_path):
        """
        Read a certificate file.

        :param pem_path: The path to a .pem file.
        :type pem_path: str
        :return: A certificate
        :rtype: :class:`Certificate`
        """
        f = open(pem_path)
        content = f.read()
        try:
            self._update(content)
        finally:
            f.close()
        self.path = pem_path

    def write(self, pem_path):
        """
        Write the certificate.

        :param pem_path: The path to the .pem file.
        :type pem_path: str
        :return: self
        :rtype :class:`Certificate`
        """
        f = open(pem_path, 'w')
        f.write(self.toPEM())
        self.path = pem_path
        f.close()
        return self

    def delete(self):
        """
        Delete the file associated with this certificate.
        """
        if hasattr(self, 'path'):
            os.unlink(self.path)
        else:
            raise Exception('no path, not deleted')

    def toPEM(self):
        """
        Get PEM representation of the certificate.

        :return: A PEM string
        :rtype: str
        """
        return self.x509.as_pem()

    def __str__(self):
        return self.x509.as_text()

    def __repr__(self):
        sn = self.serialNumber()
        cert_path = None
        if hasattr(self, 'path'):
            cert_path = self.path
        return '[sn: %d, path: "%s"]' % (sn, cert_path)

    def __cmp__(self, other):
        valid_range = self.validRange()
        exp1 = valid_range.end()
        other_valid_range = other.validRange()
        exp2 = other_valid_range.end()
        if exp1 < exp2:
            return -1
        if exp1 > exp2:
            return 1
        return 0


class RedhatCertificate(Certificate):
    """
    Represents a Red Hat certificate.

    :cvar REDHAT: The Red Hat base OID.
    :type REDHAT: str
    """

    REDHAT = '1.3.6.1.4.1.2312.9'

    def __init__(self, *args, **kwargs):
        super(RedhatCertificate, self).__init__(*args, **kwargs)
        self._extract_redhat_extensions()

    def _extract_redhat_extensions(self):
        self.__redhat = self.extensions().branch(self.REDHAT)

    def _update(self, content):
        Certificate._update(self, content)
        self._extract_redhat_extensions()

    def redhat(self):
        """
        Get the extension subtree for the `redhat` namespace.

        :return: The extensions with the Red Hat namespace trimmed.
        :rtype: :class:`Extensions`
        """
        return self.__redhat

    def bogus(self):
        bogus = Certificate.bogus(self)
        if self.serialNumber() < 1:
            bogus.append('Serial number must be > 0')
        cn = self.subject().get('CN')
        if not cn:
            bogus.append('Invalid common name: %s' % cn)
        return bogus


class ProductCertificate(RedhatCertificate):
    """
    Represents a Red Hat product/entitlement certificate.

    It is OID schema aware and provides methods to
    get product information.
    """

    def getProduct(self):
        """
        Get the product defined in the certificate.

        :return: A product object.
        :rtype: :class:`Product`
        """
        rhns = self.redhat()
        products = rhns.find('1.*.1', 1)
        if products:
            p = products[0]
            oid = p[0]
            root = oid.rtrim(1)
            product_id = oid[1]
            ext = rhns.branch(root)
            return Product(product_id, ext)

    def getProducts(self):
        """
        Get a list products defined in the certificate.

        :return: A list of product objects.
        :rtype: list of :class:`Product`
        """
        lst = []
        rhns = self.redhat()
        for p in rhns.find('1.*.1'):
            oid = p[0]
            root = oid.rtrim(1)
            product_id = oid[1]
            ext = rhns.branch(root)
            lst.append(Product(product_id, ext))
        return lst

    def bogus(self):
        bogus = RedhatCertificate.bogus(self)
        return bogus

    def __str__(self):
        s = []
        s.append('RAW:')
        s.append('===================================')
        s.append(Certificate.__str__(self))
        s.append('MODEL:')
        s.append('===================================')
        s.append('Serial#: %s' % self.serialNumber())
        s.append('Subject (CN): %s' % self.subject().get('CN'))
        for p in self.getProducts():
            s.append(str(p))
        return '\n'.join(s)


class EntitlementCertificate(ProductCertificate):
    """
    Represents an entitlement certificate.
    """
    def _update(self, content):
        ProductCertificate._update(self, content)

        rhns = self.redhat()
        order = rhns.find('4.1', 1, True)
        if order:
            p = order[0]
            oid = p[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            self.order = Order(ext)
        else:
            self.order = None

    def delete(self):
        """
        Delete the file associated with this certificate.
        """
        if hasattr(self, 'path'):
            os.unlink(self.path)
            # we should keep the key path around, but
            # we dont seem to, but it's consistent
            parts = self.path.split('.')
            key_path = "%s-key.pem" % parts[0]
            os.unlink(key_path)
        else:
            raise Exception('no path, not deleted')

    def getOrder(self):
        """
        Get the :obj:`order` object defined in the certificate.

        :return: An order object.
        :rtype: :class:`Order`
        """
        return self.order

    def getEntitlements(self):
        """
        Get all entitlements defined in the certificate.

        :return: A list of entitlement object.
        :rtype: List of :class:`Entitlement`
        """
        return self.getContentEntitlements() \
             + self.getRoleEntitlements()

    # TODO: Not a great name, this is just getting content, self is
    # the entitlement.
    def getContentEntitlements(self):
        """
        Get the B{content} entitlements defined in the certificate.

        :return: A list of entitlement object.
        :rtype: [:obj:`Content`,..]
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find('2.*.1.1')
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            lst.append(Content(ext))
        return lst

    def getRoleEntitlements(self):
        """
        Get the *role* entitlements defined in the certificate.

        :return: A list of entitlement object.
        :rtype: [:obj:`Role`,..]
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find('3.*.1')
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            lst.append(Role(ext))
        return lst

    @deprecated
    def validRangeWithGracePeriod(self):
        return super(EntitlementCertificate, self).validRange()

    @deprecated
    def validWithGracePeriod(self):
        return self.validRangeWithGracePeriod().has_now()

    def bogus(self):
        bogus = ProductCertificate.bogus(self)
        if self.getOrder() is None:
            bogus.append('No order infomation')
        return bogus

    def __str__(self):
        s = []
        order = self.getOrder()
        s.append(ProductCertificate.__str__(self))
        for ent in self.getEntitlements():
            s.append(str(ent))
        s.append(str(order))
        return '\n'.join(s)


class Key(object):
    """
    The (private|public) key.

    :ivar content: The PEM encoded key.
    :type content: str
    """

    @classmethod
    def read(cls, pem_path):
        """
        Read the key.

        :param pem_path: The path to the .pem file.
        :type path: str
        """
        f = open(pem_path)
        content = f.read()
        f.close()
        key = Key(content)
        key.path = pem_path
        return key

    def __init__(self, content):
        """
        :param content: The PEM encoded key.
        :type content: str
        """
        self.content = content

    def bogus(self):
        bogus = []
        if self.content:
            # TODO handle public keys too? class docstring seems to indicate so
            key = _certificate.load_private_key(pem=self.content)
            if not key:
                bogus.append("Invalid key data")
        else:
            bogus.append("No key data provided")

        return bogus

    def write(self, pem_path):
        """
        Write the key.

        :param path: The path to the .pem file.
        :type path: str
        :return: self
        """
        f = open(pem_path, 'w')
        f.write(self.content)
        self.path = pem_path
        f.close()
        os.chmod(pem_path, 0o600)
        return self

    def delete(self):
        """
        Delete the file associated with this key.
        """
        if hasattr(self, 'path'):
            os.unlink(self.path)
        else:
            raise Exception('no path, not deleted')

    def __str__(self):
        return self.content


class DateRange(object):
    """
    Date range object.

    :ivar begin_date: The begining date
    :type begin_date: :class:`datetime`
    :ivar end_date: The ending date
    :type end_date: :class:`datetime`
    """

    def __init__(self, begin_date, end_date):
        self._begin = self._convert_to_utc(begin_date)
        self._end = self._convert_to_utc(end_date)

    def _convert_to_utc(self, timestamp):
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=GMT())
        else:
            return timestamp.astimezone(GMT())

    def begin(self):
        """
        Get range beginning.

        :return: The beginning date in UTC.
        :rtype: :class:`datatime.datetime`
        """
        return self._begin

    def end(self):
        """
        Get range end.

        :return: The end date in UTC.
        :rtype: :class:`datetime.datetime`
        """
        return self._end

    def has_now(self):
        """
        Get whether the certificate is valid based on the date now.

        :return: True if valid.
        :rtype: boolean
        """
        gmt = dt.utcnow()
        gmt = gmt.replace(tzinfo=GMT())
        return self.has_date(gmt)

    def has_date(self, date):
        """
        Get whether the certificate is valid based on the date.

        :param: date
        :type: :class:`datetime.datetime`
        :return: True if valid.
        :rtype: boolean
        """
        return (date >= self.begin() and date <= self.end())

    @deprecated
    def hasDate(self, date):
        return self.has_date(date)

    @deprecated
    def hasNow(self):
        return self.has_now()

    def __str__(self):
        return '\n\t%s\n\t%s' % (self._begin, self._end)


class GMT(tzinfo):
    """GMT"""

    def utcoffset(self, date_time):
        return timedelta(seconds=0)

    def tzname(self, date_time):
        return 'GMT'

    def dst(self, date_time):
        return timedelta(seconds=0)


class Extensions(dict):
    """
    Represents x.509 (v3) custom extensions.
    """

    def __init__(self, x509):
        """
        :param x509: An :module:`rhsm._certificate` :class:`X509` object or dict.
        :type x509: :obj:`X509`
        """
        if isinstance(x509, dict):
            self.update(x509)
        else:
            self._parse(x509)

    def ltrim(self, n):
        """
        Left trim *n* parts.

        :param n: The number of parts to trim.
        :type n: int
        :return: The trimmed OID
        :rtype: :class:`Extensions`
        """
        d = {}
        for oid, v in list(self.items()):
            d[oid.ltrim(n)] = v
        return Extensions(d)

    def get(self, oid, default=None):
        """
        Get the value of an extension by *oid*.

        Note: The *oid* may contain (*) wildcards.

        :param oid: An `OID` that may contain (*) wildcards.
        :type oid: str|`OID`
        :return: The value of the first extension matched.
        :rtype: str
        """
        ext = self.find(oid, 1, True)
        if ext:
            return ext[0][1]
        else:
            return default

    def find(self, oid, limit=0, ignoreOrder=False):
        """
        Find all extensions matching the oid.

        Note: The oid may contain (*) wildcards.

        :param oid: An OID that may contain (*) wildcards.
        :type oid: str|`OID`
        :param limit: Limit the number returned, 0=unlimited
        :type limit: int
        :param ignoreOrder Should oids be ordered
        :type ignoreOrder: bool
        :return: A list of matching items.
        :rtype: (`OID`, value)
        :see: OID.match()
        """
        ext = []
        found = 0
        if isinstance(oid, str):
            oid = OID(oid)

        # Only order the keys if we want more than a singel return avalue
        if ignoreOrder:
            keyset = list(self.keys())
        else:
            keyset = sorted(self.keys())

        for k in keyset:
            if k.match(oid):
                v = self[k]
                ext.append((k, v))
                found = found + 1
            if limit and found == limit:
                break
        return ext

    def branch(self, root):
        """
        Find a subtree by matching the oid.

        :param root: An `OID` that may contain (*) wildcards.
        :type root: str|`OID`
        :return: A subtree.
        :rtype: :class:`Extensions`
        """
        d = {}
        if isinstance(root, str):
            root = OID(root)
        if root[-1]:
            root = root.append('')
        ln = len(root) - 1
        for oid, v in self.find(root):
            trimmed = oid.ltrim(ln)
            d[trimmed] = v
        return Extensions(d)

    def _parse(self, x509):
        """
        Parse the extensions. Expects an :module:`rhsm._certificate` :class:`X509` object.
        """
        for oid, value in list(x509.get_all_extensions().items()):
            oid = OID(oid)
            self[oid] = value

    def __str__(self):
        s = []
        for item in list(self.items()):
            s.append('%s = "%s"' % item)
        return '\n'.join(s)


class OID(object):
    """
    The Object Identifier object.

    :ivar part: The oid parts.
    :type part: [str,]
    :cvar WILDCARD: The wildcard character.
    :type WILDCARD: str
    """

    WILDCARD = '*'

    @classmethod
    def join(cls, *oid):
        return '.'.join(oid)

    @classmethod
    def split(cls, s):
        """
        Split an OID string.

        :param s: An OID string Eg: (1.2.3)
        :type s: str
        :return: A list of OID parts.
        :rtype: [str,]
        """
        return s.split('.')

    def __init__(self, oid):
        """
        :param oid: The OID value.
        :type oid: str|[str,]
        """
        if isinstance(oid, str):
            self.part = self.split(oid)
        else:
            self.part = oid

        self._len = None
        self._str = None
        self._hash = None

    def parent(self):
        """
        Get the parent OID.

        :return: The parent OID.
        :rtype: L{OID}
        """
        p = self.part[:-1]
        if p:
            return OID(p)

    def ltrim(self, n):
        """
        Left trim I{n} parts.

        :param n: The number of parts to trim.
        :type n: int
        :return: The trimmed OID
        :rtype: :class:`OID`
        """
        return OID(self.part[n:])

    def rtrim(self, n):
        """
        Right trim I{n} parts.

        :param n: The number of parts to trim.
        :type n: int
        :return: The trimmed OID
        :rtype: :class:`OID`
        """
        return OID(self.part[:-n])

    def append(self, oid):
        """
        Append the specified OID fragment.

        :param oid: An OID fragment.
        :type oid: str|`OID`
        :return: The concatenated OID.
        "rtype: :class:`OID`
        """
        if isinstance(oid, str):
            oid = OID(oid)
        part = self.part + oid.part
        return OID(part)

    def match(self, oid):
        """
        Match the specified OID considering wildcards.

        Patterns:
          - 1.4.5.6.74 (not wildcarded)
          -    .5.6.74 (match on only last 4)
          -    5.6.74. (match only first 4)
          - 1.4.*.6.*  (wildcard pattern)

        :param oid: An OID string or object.
        :type oid: `OID`
        :return: True if matched
        :rtype: boolean
        """
        i = 0

        # Matching the end
        if not oid[0]:
            #oid = OID(oid[1:])
            oid = oid[1:]
            parts = self.part[-len(oid):]
        # Matching the beginning
        elif not oid[-1]:
            #oid = OID(oid[:-1])
            oid = oid[:-1]
            parts = self.part[:len(oid)]
        # Full on match
        else:
            parts = self.part

        # The lengths do not match, fail.
        if len(parts) != len(oid):
            return False

        for x in parts:
            val = oid[i]
            if (x == val or val == self.WILDCARD):
                i += 1
            else:
                return False

        return True

    def __len__(self):
        if not self._len:
            self._len = len(self.part)

        return self._len

    def __getitem__(self, index):
        return self.part[index]

    def __repr__(self):
        return str(self)

    def __hash__(self):
        if not self._hash:
            self._hash = hash(str(self))

        return self._hash

    def __eq__(self, other):
        return (str(self) == str(other))

    def __lt__(self, other):
        return str(self) < str(other)

    def __str__(self):
        if not self._str:
            self._str = '.'.join(self.part)

        return self._str


class Order(object):

    @deprecated
    def __init__(self, ext):
        self.ext = ext

    def getName(self):
        return self.ext.get('1')

    def getNumber(self):
        return self.ext.get('2')

    def getSku(self):
        return self.ext.get('3')

    def getSubscription(self):
        return self.ext.get('4')

    def getQuantity(self):
        return self.ext.get('5')

    def getStart(self):
        return self.ext.get('6')

    def getEnd(self):
        return self.ext.get('7')

    def getVirtLimit(self):
        return self.ext.get('8')

    def getSocketLimit(self):
        return self.ext.get('9')

    def getContract(self):
        return self.ext.get('10')

    def getQuantityUsed(self):
        """
        Returns the quantity of the subscription that *this* entitlement is using.

        WARNING: a little misleading as it (a) is part of the order namespace
        and (b) sounds suspiciously like the total consumed quantity of the
        subscription.
        """
        return self.ext.get('11')

    def getWarningPeriod(self):
        return self.ext.get('12')

    def getAccountNumber(self):
        return self.ext.get('13')

    def getProvidesManagement(self):
        return self.ext.get('14')

    def getSupportLevel(self):
        return self.ext.get('15')

    def getSupportType(self):
        return self.ext.get('16')

    def getStackingId(self):
        return self.ext.get('17')

    def getVirtOnly(self):
        return self.ext.get('18')

    def __str__(self):
        s = []
        s.append('Order {')
        s.append('\tName .............. = %s' % self.getName())
        s.append('\tNumber ............ = %s' % self.getNumber())
        s.append('\tSKU ............... = %s' % self.getSku())
        s.append('\tSubscription ...... = %s' % self.getSubscription())
        s.append('\tQuantity .......... = %s' % self.getQuantity())
        s.append('\tStart (Ent) ....... = %s' % self.getStart())
        s.append('\tEnd (Ent) ......... = %s' % self.getEnd())
        s.append('\tVirt Limit ........ = %s' % self.getVirtLimit())
        s.append('\tSocket Limit ...... = %s' % self.getSocketLimit())
        s.append('\tContract .......... = %s' % self.getContract())
        s.append('\tWarning Period .... = %s' % self.getWarningPeriod())
        s.append('\tAccount Number .... = %s' % self.getAccountNumber())
        s.append('\tProvides Management = %s' % self.getProvidesManagement())
        s.append('\tSupport Level ..... = %s' % self.getSupportLevel())
        s.append('\tSupport Type ...... = %s' % self.getSupportType())
        s.append('\tStacking Id ....... = %s' % self.getStackingId())
        s.append('\tVirt Only ......... = %s' % self.getVirtOnly())
        s.append('}')
        return '\n'.join(s)


class Product(object):

    @deprecated
    def __init__(self, p_hash, ext):
        self.hash = p_hash
        self.ext = ext
        self.name = self.ext.get('1')
        self.version = self.ext.get('2')
        self.arch = self.ext.get('3')
        self.provided_tags = parse_tags(self.ext.get('4'))
        self.brand_type = self.ext.get('5')
        self.brand_name = self.ext.get('6')

    def getHash(self):
        return self.hash

    def getName(self):
        return self.name

    def getArch(self):
        return self.arch

    def getVersion(self):
        return self.version

    def getProvidedTags(self):
        return self.provided_tags

    def getBrandType(self):
        return self.brand_type

    def getBrandName(self):
        return self.brand_name

    def __eq__(self, rhs):
        return (self.getHash() == rhs.getHash())

    def __str__(self):
        s = []
        s.append('Product {')
        s.append('\tHash ......... = %s' % self.getHash())
        s.append('\tName ......... = %s' % self.getName())
        s.append('\tVersion ...... = %s' % self.getVersion())
        s.append('\tArchitecture . = %s' % self.getArch())
        s.append('\tProvided Tags  = %s' % self.getProvidedTags())
        s.append('\tBrand Type     = %s' % self.getBrandType())
        s.append('\tBrand Name     = %s' % self.getBrandName())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


class Entitlement(object):

    def __init__(self, ext):
        self.ext = ext


class Content(Entitlement):

    def __init__(self, ext):
        Entitlement.__init__(self, ext)
        self.name = self.ext.get('1')
        self.label = self.ext.get('2')
        self.quantity = self.ext.get('3')
        self.flex_quantity = self.ext.get('4')
        self.vendor = self.ext.get('5')
        self.url = self.ext.get('6')
        self.gpg = self.ext.get('7')
        self.enabled = self.ext.get('8')
        self.metadata_expire = self.ext.get('9')
        self.required_tags = parse_tags(self.ext.get('10'))

    def getName(self):
        return self.name

    def getLabel(self):
        return self.label

    def getQuantity(self):
        return self.quantity

    def getFlexQuantity(self):
        return self.flex_quantity

    def getVendor(self):
        return self.vendor

    def getUrl(self):
        return self.url

    def getGpg(self):
        return self.gpg

    def getEnabled(self):
        return self.enabled

    def getMetadataExpire(self):
        return self.metadata_expire

    def getRequiredTags(self):
        return self.required_tags

    def __eq__(self, rhs):
        return isinstance(rhs, self.__class__) and (self.label == rhs.label)

    def __str__(self):
        s = []
        s.append('Entitlement (content) {')
        s.append('\tName .......... = %s' % self.getName())
        s.append('\tLabel ......... = %s' % self.getLabel())
        s.append('\tQuantity ...... = %s' % self.getQuantity())
        s.append('\tFlex Quantity . = %s' % self.getFlexQuantity())
        s.append('\tVendor ........ = %s' % self.getVendor())
        s.append('\tURL ........... = %s' % self.getUrl())
        s.append('\tGPG Key ....... = %s' % self.getGpg())
        s.append('\tEnabled ....... = %s' % self.getEnabled())
        s.append('\tMetadata Expire = %s' % self.getMetadataExpire())
        s.append('\tRequired Tags . = %s' % self.getRequiredTags())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.label)


class Role(Entitlement):

    def getName(self):
        return self.ext.get('1')

    def getDescription(self):
        return self.ext.get('2')

    def __eq__(self, rhs):
        return (self.getName() == rhs.getName())

    def __str__(self):
        s = []
        s.append('Entitlement (role) {')
        s.append('\tName ......... = %s' % self.getName())
        s.append('\tDescription .. = %s' % self.getDescription())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


class CertificateException(Exception):
    pass
