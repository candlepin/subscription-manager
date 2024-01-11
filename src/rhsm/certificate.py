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
from typing import List, Any, Callable, Optional, Union, Tuple, Dict

import dateutil
import os
import re
import datetime
from rhsm import _certificate
import logging
import warnings

log = logging.getLogger(__name__)


# Regex used to scan for OIDs:
OID_PATTERN = re.compile(r"([0-9]+\.)+[0-9]+:")


# Regex used to parse OID values such as:
#    0:d=0  hl=2 l=   3 prim: UTF8STRING        :2.0
VALUE_PATTERN = re.compile(r".*prim:\s(\w*)\s*:*(.*)")


# NOTE: These factory methods create new style certificate objects from
# the certificate2 module. They are placed here to abstract the fact that
# we're using two modules for the time being. Eventually the certificate2 code
# should be moved here.
def create_from_file(path: str) -> "EntitlementCertificate":
    """
    Try to create certificate object from path to certificate
    :param path: String with path to certificate
    :return: rhsm.certificate2.Certificate
    """
    from rhsm.certificate2 import _CertFactory  # prevent circular deps

    return _CertFactory().create_from_file(path)


def create_from_pem(pem: str) -> "EntitlementCertificate":
    """
    Try to create certificate object from PEM string
    :param pem: String with PEM
    :return: Instance of rhsm.certificate2.Certificate
    """
    from rhsm.certificate2 import _CertFactory  # prevent circular deps

    return _CertFactory().create_from_pem(pem)


def parse_tags(tag_str: str) -> List[str]:
    """
    Split a comma separated list of tags from a certificate into a list.
    """
    tags: List[str] = []
    if tag_str:
        tags = tag_str.split(",")
    return tags


class UTC(datetime.tzinfo):
    """UTC"""

    _ZERO = datetime.timedelta(0)

    def utcoffset(self, dt: Any) -> datetime.timedelta:
        return self._ZERO

    def tzname(self, dt: Any) -> str:
        return "UTC"

    def dst(self, dt: Any) -> datetime.timedelta:
        return self._ZERO


def get_datetime_from_x509(date: Any) -> datetime.datetime:
    return dateutil.parser.parse(date)


def deprecated(func: Callable) -> Callable:
    """
    A decorator that marks a function as deprecated. This will cause a
    warning to be emitted any time that function is used by a caller.
    """

    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function: %s" % func.__name__, category=DeprecationWarning)
        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


class Certificate:
    """
    Represents and x.509 certificate.

    :ivar x509: The :obj:`X509` backing object.
    :type x509: :class:`X509`
    :ivar __ext: A dictionary of extensions `OID`:value
    :type __ext: dict of :obj:`Extensions`
    """

    @deprecated
    def __init__(self, content: str = None):
        """
        :param content: The (optional) PEM encoded content
        """
        self._update(content)
        self.path = None

    def _update(self, content: str) -> None:
        if content:
            x509 = _certificate.load(pem=content)
            if x509 is None:
                raise CertificateException("Error loading certificate")
        else:
            x509 = _certificate.X509()
        self.__ext: Extensions = Extensions(x509)
        self.x509: _certificate.X509 = x509

        self.subj: dict = self.x509.get_subject()
        self.serial: int = self.x509.get_serial_number()

        self.altName: str = x509.get_extension(name="subjectAltName")

    def serialNumber(self) -> int:
        """
        Get the serial number

        :return: The x.509 serial number
        """
        return self.serial

    def subject(self) -> dict:
        """
        Get the certificate subject.

        note: Missing NID mapping for UID added to patch openssl.

        :return: A dictionary of subject fields.
        :rtype: dict
        """
        return self.subj

    def alternateName(self) -> str:
        """
        Return the alternate name of the certificate.

        :return: A string representation of the alternate name
        """
        return self.altName

    def validRange(self) -> "DateRange":
        """
        Get the valid date range.

        :return: The valid date range.
        """
        return DateRange(
            get_datetime_from_x509(self.x509.get_not_before()),
            get_datetime_from_x509(self.x509.get_not_after()),
        )

    def valid(self, on_date: datetime.datetime = None) -> bool:
        """
        Get whether the certificate is valid based on date.

        :return: True if valid.
        """
        valid_range = self.validRange()
        gmt = datetime.datetime.now(datetime.timezone.utc)
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return valid_range.has_date(gmt)

    def expired(self, on_date: datetime.datetime = None) -> bool:
        """
        Get whether the certificate is expired based on date.

        :return: True if valid.
        """
        valid_range = self.validRange()
        gmt = datetime.datetime.now(datetime.timezone.utc)
        if on_date:
            gmt = on_date
        gmt = gmt.replace(tzinfo=GMT())
        return valid_range.end() < gmt

    def bogus(self) -> list:
        """
        Get whether the certificate contains bogus data or is otherwise unsuitable.

        The certificate may be valid but still be considered bogus.

        :return: List of reasons if bogus
        """
        return []

    def extensions(self) -> "Extensions":
        """
        Get custom extensions.

        :return: An extensions object.
        :rtype: :class:`Extensions`
        """
        return self.__ext

    def read(self, pem_path: str) -> "Certificate":
        """
        Read a certificate file
        :param pem_path: The path to a .pem file.
        """
        f = open(pem_path)
        content = f.read()
        try:
            self._update(content)
        finally:
            f.close()
        self.path = pem_path
        return self

    def write(self, pem_path: str) -> "Certificate":
        """
        Write the certificate.

        :param pem_path: The path to the .pem file.
        :return: self
        """
        f = open(pem_path, "w")
        f.write(self.toPEM())
        self.path = pem_path
        f.close()
        return self

    def delete(self) -> None:
        """
        Delete the file associated with this certificate.
        """
        if hasattr(self, "path"):
            os.unlink(self.path)
        else:
            raise Exception("no path, not deleted")

    def toPEM(self) -> str:
        """
        Get PEM representation of the certificate.

        :return: A PEM string
        """
        return self.x509.as_pem()

    def __str__(self) -> str:
        return self.x509.as_text()

    def __repr__(self) -> str:
        sn = self.serialNumber()
        cert_path = None
        if hasattr(self, "path"):
            cert_path = self.path
        return '[sn: %d, path: "%s"]' % (sn, cert_path)

    def __cmp__(self, other: "Certificate") -> int:
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
    Represents a Red Hat certificate
    :cvar REDHAT: The Red Hat base OID
    """

    REDHAT: str = "1.3.6.1.4.1.2312.9"

    def __init__(self, *args, **kwargs) -> None:
        super(RedhatCertificate, self).__init__(*args, **kwargs)
        self._extract_redhat_extensions()

    def _extract_redhat_extensions(self) -> None:
        self.__redhat: Extensions = self.extensions().branch(self.REDHAT)

    def _update(self, content: str) -> None:
        Certificate._update(self, content)
        self._extract_redhat_extensions()

    def redhat(self) -> "Extensions":
        """
        Get the extension subtree for the `redhat` namespace.

        :return: The extensions with the Red Hat namespace trimmed.
        """
        return self.__redhat

    def bogus(self) -> List[str]:
        """
        Return list of reason, why the certificate is bogus
        :return: List of strings with reasons.
        """
        bogus: list = Certificate.bogus(self)
        if self.serialNumber() < 1:
            bogus.append("Serial number must be > 0")
        cn = self.subject().get("CN")
        if not cn:
            bogus.append("Invalid common name: %s" % cn)
        return bogus


class ProductCertificate(RedhatCertificate):
    """
    Represents a Red Hat product/entitlement certificate.

    It is OID schema aware and provides methods to
    get product information.
    """

    def getProduct(self) -> Union["Product", None]:
        """
        Get the product defined in the certificate.

        :return: A product object.
        """
        rhns = self.redhat()
        products = rhns.find("1.*.1", 1)
        if products:
            p = products[0]
            oid = p[0]
            root = oid.rtrim(1)
            product_id = oid[1]
            ext = rhns.branch(root)
            return Product(product_id, ext)

    def getProducts(self) -> List["Product"]:
        """
        Get a list products defined in the certificate.

        :return: A list of product objects.
        """
        lst = []
        rhns = self.redhat()
        for p in rhns.find("1.*.1"):
            oid = p[0]
            root = oid.rtrim(1)
            product_id = oid[1]
            ext = rhns.branch(root)
            lst.append(Product(product_id, ext))
        return lst

    def bogus(self) -> List[str]:
        bogus = RedhatCertificate.bogus(self)
        return bogus

    def __str__(self) -> str:
        s = []
        s.append("RAW:")
        s.append("===================================")
        s.append(Certificate.__str__(self))
        s.append("MODEL:")
        s.append("===================================")
        s.append("Serial#: %s" % self.serialNumber())
        s.append("Subject (CN): %s" % self.subject().get("CN"))
        for p in self.getProducts():
            s.append(str(p))
        return "\n".join(s)


class EntitlementCertificate(ProductCertificate):
    """
    Represents an entitlement certificate.
    """

    def _update(self, content: str) -> None:
        ProductCertificate._update(self, content)

        rhns = self.redhat()
        order = rhns.find("4.1", 1, True)
        if order:
            p = order[0]
            oid = p[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            self.order = Order(ext)
        else:
            self.order = None

    def delete(self) -> None:
        """
        Delete the file associated with this certificate.
        """
        if hasattr(self, "path"):
            os.unlink(self.path)
            # we should keep the key path around, but
            # we dont seem to, but it's consistent
            parts = self.path.split(".")
            key_path = "%s-key.pem" % parts[0]
            os.unlink(key_path)
        else:
            raise Exception("no path, not deleted")

    def getOrder(self) -> "Order":
        """
        Get the :obj:`order` object defined in the certificate.

        :return: An order object.
        """
        return self.order

    def getEntitlements(self) -> List["Entitlement"]:
        """
        Get all entitlements defined in the certificate.

        :return: A list of entitlement object.
        """
        return self.getContentEntitlements() + self.getRoleEntitlements()

    # TODO: Not a great name, this is just getting content, self is
    # the entitlement.
    def getContentEntitlements(self) -> List["Entitlement"]:
        """
        Get the B{content} entitlements defined in the certificate.

        :return: A list of entitlement object.
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find("2.*.1.1")
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            lst.append(Content(ext))
        return lst

    def getRoleEntitlements(self) -> List["Role"]:
        """
        Get the *role* entitlements defined in the certificate.

        :return: A list of entitlement object.
        :rtype: [:obj:`Role`,..]
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find("3.*.1")
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

    def bogus(self) -> List[str]:
        bogus = ProductCertificate.bogus(self)
        if self.getOrder() is None:
            bogus.append("No order information")
        return bogus

    def __str__(self) -> str:
        s = []
        order = self.getOrder()
        s.append(ProductCertificate.__str__(self))
        for ent in self.getEntitlements():
            s.append(str(ent))
        s.append(str(order))
        return "\n".join(s)


class Key:
    """
    The (private|public) key.

    :ivar content: The PEM encoded key.
    :type content: str
    """

    @classmethod
    def read(cls, pem_path: str) -> "Key":
        """
        Read the key.

        :param pem_path: The path to the .pem file.
        """
        f = open(pem_path)
        content: str = f.read()
        f.close()
        key = Key(content)
        key.path = pem_path
        return key

    def __init__(self, content: str):
        """
        :param content: The PEM encoded key.
        """
        self.content: str = content
        self.path: Optional[str] = None

    def bogus(self) -> List[str]:
        bogus = []
        if self.content:
            # TODO handle public keys too? class docstring seems to indicate so
            key = _certificate.load_private_key(pem=self.content)
            if not key:
                bogus.append("Invalid key data")
        else:
            bogus.append("No key data provided")

        return bogus

    def write(self, pem_path: str) -> "Key":
        """
        Write the key.

        :param pem_path: The path to the .pem file.
        """
        f = open(pem_path, "w")
        f.write(self.content)
        self.path = pem_path
        f.close()
        os.chmod(pem_path, 0o644)
        return self

    def delete(self) -> None:
        """
        Delete the file associated with this key.
        """
        if hasattr(self, "path"):
            os.unlink(self.path)
        else:
            raise Exception("no path, not deleted")

    def __str__(self) -> str:
        return self.content


class DateRange:
    """
    Date range object.

    :ivar begin_date: The beginning date
    :ivar end_date: The ending date
    """

    def __init__(self, begin_date: datetime.datetime, end_date: datetime.datetime):
        self._begin = self._convert_to_utc(begin_date)
        self._end = self._convert_to_utc(end_date)

    def _convert_to_utc(self, timestamp: datetime.datetime) -> datetime.datetime:
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=GMT())
        else:
            return timestamp.astimezone(GMT())

    def begin(self) -> datetime.datetime:
        """
        Get range beginning.

        :return: The beginning date in UTC.
        """
        return self._begin

    def end(self) -> datetime.datetime:
        """
        Get range end.

        :return: The end date in UTC.
        """
        return self._end

    def has_now(self) -> bool:
        """
        Get whether the certificate is valid based on the date now.

        :return: True if valid.
        """
        gmt: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        gmt = gmt.replace(tzinfo=GMT())
        return self.has_date(gmt)

    def has_date(self, date: datetime.datetime) -> bool:
        """
        Get whether the certificate is valid based on the date.

        :return: True if valid.
        """
        return date >= self.begin() and date <= self.end()

    @deprecated
    def hasDate(self, date):
        return self.has_date(date)

    @deprecated
    def hasNow(self):
        return self.has_now()

    def __str__(self) -> str:
        return "\n\t%s\n\t%s" % (self._begin, self._end)


class GMT(datetime.tzinfo):
    """GMT"""

    def utcoffset(self, dt: Any) -> datetime.timedelta:
        return datetime.timedelta(seconds=0)

    def tzname(self, dt: Any) -> str:
        return "GMT"

    def dst(self, dt: Any):
        return datetime.timedelta(seconds=0)


class Extensions(dict):
    """
    Represents x.509 (v3) custom extensions.
    """

    def __init__(self, x509: Union[dict, _certificate.X509]):
        if isinstance(x509, dict):
            self.update(x509)
        else:
            self._parse(x509)

    def ltrim(self, n: int) -> "Extensions":
        """
        Left trim *n* parts.

        :param n: The number of parts to trim
        :return: The trimmed OID
        """
        d = {}
        for oid, v in list(self.items()):
            d[oid.ltrim(n)] = v
        return Extensions(d)

    def get(self, oid: Union[str, "OID"], default: Optional[str] = None) -> str:
        """
        Get the value of an extension by *oid*.

        Note: The *oid* may contain (*) wildcards.

        :param oid: An `OID` that may contain (*) wildcards.
        :param default: Default value.
        :return: The value of the first extension matched.
        """
        ext = self.find(oid, 1, True)
        if ext:
            return ext[0][1]
        else:
            return default

    def find(
        self,
        oid: Union["OID", str],
        limit: int = 0,
        ignoreOrder: bool = False,
    ) -> List[Tuple["OID", str]]:
        """
        Find all extensions matching the oid.

        Note: The oid may contain (*) wildcards.

        :param oid: An OID that may contain (*) wildcards.
        :param limit: Limit the number returned, 0=unlimited
        :param ignoreOrder: Should OIDs be ordered
        :return: A list of matching items.
        :see: OID.match()
        """
        ext: List[Tuple["OID", str]] = []
        found: int = 0
        if isinstance(oid, str):
            oid = OID(oid)

        # Only order the keys if we want more than a single return value
        keyset: List["OID"]
        if ignoreOrder:
            keyset = list(self.keys())
        else:
            keyset = sorted(self.keys())

        for k in keyset:
            if k.match(oid):
                v: str = self[k]
                ext.append((k, v))
                found = found + 1
            if limit and found == limit:
                break
        return ext

    def branch(self, root: Union["OID", str]) -> "Extensions":
        """
        Find a subtree by matching the oid.

        :param root: An `OID` that may contain (*) wildcards.
        :return: A subtree.
        """
        d: Dict["OID", str] = {}
        if isinstance(root, str):
            root = OID(root)
        if root[-1]:
            root = root.append("")
        ln: int = len(root) - 1
        for oid, v in self.find(root):
            trimmed = oid.ltrim(ln)
            d[trimmed] = v
        return Extensions(d)

    def _parse(self, x509: _certificate.X509) -> None:
        """
        Parse the extensions.
        """
        for oid, value in list(x509.get_all_extensions().items()):
            oid = OID(oid)
            self[oid] = value

    def __str__(self) -> str:
        s = []
        for item in list(self.items()):
            s.append('%s = "%s"' % item)
        return "\n".join(s)


class OID:
    """
    The Object Identifier object
    :ivar part: The oid parts
    :cvar WILDCARD: The wildcard character
    """

    WILDCARD: str = "*"

    @classmethod
    def join(cls, *oid) -> str:
        return ".".join(oid)

    @classmethod
    def split(cls, s: str) -> List[str]:
        """
        Split an OID string.

        :param s: An OID string Eg: (1.2.3)
        :return: A list of OID parts.
        """
        return s.split(".")

    def __init__(self, oid: Union[str, List[str]]):
        """
        :param oid: The OID value.
        """
        if isinstance(oid, str):
            self.part = self.split(oid)
        else:
            self.part = oid

        self._len: Optional[int] = None
        self._str: Optional[str] = None
        self._hash: Optional[str] = None

    def parent(self) -> Optional["OID"]:
        """
        Get the parent OID.

        :return: The parent OID.
        """
        p: List[str] = self.part[:-1]
        if p:
            return OID(p)

    def ltrim(self, n: int) -> "OID":
        """
        Left trim I{n} parts.

        :param n: The number of parts to trim.
        :return: The trimmed OID
        """
        return OID(self.part[n:])

    def rtrim(self, n: int) -> "OID":
        """
        Right trim I{n} parts.

        :param n: The number of parts to trim.
        :return: The trimmed OID
        """
        return OID(self.part[:-n])

    def append(self, oid: Union["OID", str]) -> "OID":
        """
        Append the specified OID fragment.

        :param oid: An OID fragment.
        :return: The concatenated OID.
        """
        if isinstance(oid, str):
            oid = OID(oid)
        part: List[str] = self.part + oid.part
        return OID(part)

    def match(self, oid: "OID") -> bool:
        """
        Match the specified OID considering wildcards.

        Patterns:
          - 1.4.5.6.74 (not wildcarded)
          -    .5.6.74 (match on only last 4)
          -    5.6.74. (match only first 4)
          - 1.4.*.6.*  (wildcard pattern)

        :param oid: An OID string or object.
        :return: True if matched
        """
        i: int = 0

        # Matching the end
        if not oid[0]:
            oid = oid[1:]
            parts = self.part[-len(oid) :]
        # Matching the beginning
        elif not oid[-1]:
            oid = oid[:-1]
            parts = self.part[: len(oid)]
        # Full on match
        else:
            parts = self.part

        # The lengths do not match, fail.
        if len(parts) != len(oid):
            return False

        for x in parts:
            val: str = oid[i]
            if x == val or val == self.WILDCARD:
                i += 1
            else:
                return False

        return True

    def __len__(self) -> int:
        if not self._len:
            self._len = len(self.part)

        return self._len

    def __getitem__(self, index: int) -> str:
        return self.part[index]

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> str:
        if not self._hash:
            self._hash = hash(str(self))

        return self._hash

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __lt__(self, other) -> bool:
        return str(self) < str(other)

    def __str__(self) -> str:
        if not self._str:
            self._str = ".".join(self.part)

        return self._str


class Order:
    @deprecated
    def __init__(self, ext):
        self.ext = ext

    def getName(self):
        return self.ext.get("1")

    def getNumber(self):
        return self.ext.get("2")

    def getSku(self):
        return self.ext.get("3")

    def getSubscription(self):
        return self.ext.get("4")

    def getQuantity(self):
        return self.ext.get("5")

    def getStart(self):
        return self.ext.get("6")

    def getEnd(self):
        return self.ext.get("7")

    def getVirtLimit(self):
        return self.ext.get("8")

    def getSocketLimit(self):
        return self.ext.get("9")

    def getContract(self):
        return self.ext.get("10")

    def getQuantityUsed(self):
        """
        Returns the quantity of the subscription that *this* entitlement is using.

        WARNING: a little misleading as it (a) is part of the order namespace
        and (b) sounds suspiciously like the total consumed quantity of the
        subscription.
        """
        return self.ext.get("11")

    def getWarningPeriod(self):
        return self.ext.get("12")

    def getAccountNumber(self):
        return self.ext.get("13")

    def getProvidesManagement(self):
        return self.ext.get("14")

    def getSupportLevel(self):
        return self.ext.get("15")

    def getSupportType(self):
        return self.ext.get("16")

    def getStackingId(self):
        return self.ext.get("17")

    def getVirtOnly(self):
        return self.ext.get("18")

    def __str__(self):
        s = []
        s.append("Order {")
        s.append("\tName .............. = %s" % self.getName())
        s.append("\tNumber ............ = %s" % self.getNumber())
        s.append("\tSKU ............... = %s" % self.getSku())
        s.append("\tSubscription ...... = %s" % self.getSubscription())
        s.append("\tQuantity .......... = %s" % self.getQuantity())
        s.append("\tStart (Ent) ....... = %s" % self.getStart())
        s.append("\tEnd (Ent) ......... = %s" % self.getEnd())
        s.append("\tVirt Limit ........ = %s" % self.getVirtLimit())
        s.append("\tSocket Limit ...... = %s" % self.getSocketLimit())
        s.append("\tContract .......... = %s" % self.getContract())
        s.append("\tWarning Period .... = %s" % self.getWarningPeriod())
        s.append("\tAccount Number .... = %s" % self.getAccountNumber())
        s.append("\tProvides Management = %s" % self.getProvidesManagement())
        s.append("\tSupport Level ..... = %s" % self.getSupportLevel())
        s.append("\tSupport Type ...... = %s" % self.getSupportType())
        s.append("\tStacking Id ....... = %s" % self.getStackingId())
        s.append("\tVirt Only ......... = %s" % self.getVirtOnly())
        s.append("}")
        return "\n".join(s)


class Product:
    @deprecated
    def __init__(self, p_hash: str, ext: Extensions) -> None:
        self.hash = p_hash
        self.ext = ext
        self.name = self.ext.get("1")
        self.version = self.ext.get("2")
        self.arch = self.ext.get("3")
        self.provided_tags = parse_tags(self.ext.get("4"))
        self.brand_type = self.ext.get("5")
        self.brand_name = self.ext.get("6")

    def getHash(self) -> str:
        return self.hash

    def getName(self) -> str:
        return self.name

    def getArch(self) -> str:
        return self.arch

    def getVersion(self) -> str:
        return self.version

    def getProvidedTags(self) -> List[str]:
        return self.provided_tags

    def getBrandType(self) -> str:
        return self.brand_type

    def getBrandName(self) -> str:
        return self.brand_name

    def __eq__(self, rhs) -> bool:
        return self.getHash() == rhs.getHash()

    def __str__(self) -> str:
        s = []
        s.append("Product {")
        s.append("\tHash ......... = %s" % self.getHash())
        s.append("\tName ......... = %s" % self.getName())
        s.append("\tVersion ...... = %s" % self.getVersion())
        s.append("\tArchitecture . = %s" % self.getArch())
        s.append("\tProvided Tags  = %s" % self.getProvidedTags())
        s.append("\tBrand Type     = %s" % self.getBrandType())
        s.append("\tBrand Name     = %s" % self.getBrandName())
        s.append("}")
        return "\n".join(s)

    def __repr__(self):
        return str(self)


class Entitlement:
    def __init__(self, ext: Extensions):
        self.ext: Extensions = ext


class Content(Entitlement):
    def __init__(self, ext: Extensions):
        Entitlement.__init__(self, ext)
        self.name: str = self.ext.get("1")
        self.label: str = self.ext.get("2")
        self.quantity: str = self.ext.get("3")
        self.flex_quantity: str = self.ext.get("4")
        self.vendor: str = self.ext.get("5")
        self.url: str = self.ext.get("6")
        self.gpg: str = self.ext.get("7")
        self.enabled: str = self.ext.get("8")
        self.metadata_expire: str = self.ext.get("9")
        self.required_tags: List[str] = parse_tags(self.ext.get("10"))

    def getName(self) -> str:
        return self.name

    def getLabel(self) -> str:
        return self.label

    def getQuantity(self) -> str:
        return self.quantity

    def getFlexQuantity(self) -> str:
        return self.flex_quantity

    def getVendor(self) -> str:
        return self.vendor

    def getUrl(self) -> str:
        return self.url

    def getGpg(self) -> str:
        return self.gpg

    def getEnabled(self) -> str:
        return self.enabled

    def getMetadataExpire(self) -> str:
        return self.metadata_expire

    def getRequiredTags(self) -> List[str]:
        return self.required_tags

    def __eq__(self, rhs: "Content") -> bool:
        return isinstance(rhs, self.__class__) and (self.label == rhs.label)

    def __str__(self) -> str:
        s: List[str] = []
        s.append("Entitlement (content) {")
        s.append("\tName .......... = %s" % self.getName())
        s.append("\tLabel ......... = %s" % self.getLabel())
        s.append("\tQuantity ...... = %s" % self.getQuantity())
        s.append("\tFlex Quantity . = %s" % self.getFlexQuantity())
        s.append("\tVendor ........ = %s" % self.getVendor())
        s.append("\tURL ........... = %s" % self.getUrl())
        s.append("\tGPG Key ....... = %s" % self.getGpg())
        s.append("\tEnabled ....... = %s" % self.getEnabled())
        s.append("\tMetadata Expire = %s" % self.getMetadataExpire())
        s.append("\tRequired Tags . = %s" % self.getRequiredTags())
        s.append("}")
        return "\n".join(s)

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(self.label)


class Role(Entitlement):
    def getName(self) -> str:
        return self.ext.get("1")

    def getDescription(self) -> str:
        return self.ext.get("2")

    def __eq__(self, rhs: "Role") -> bool:
        return self.getName() == rhs.getName()

    def __str__(self) -> str:
        s = []
        s.append("Entitlement (role) {")
        s.append("\tName ......... = %s" % self.getName())
        s.append("\tDescription .. = %s" % self.getDescription())
        s.append("}")
        return "\n".join(s)

    def __repr__(self) -> str:
        return str(self)


class CertificateException(Exception):
    pass
