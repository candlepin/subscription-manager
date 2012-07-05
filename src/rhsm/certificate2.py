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

from M2Crypto import X509

from rhsm.certificate import Extensions, OID

REDHAT_OID_NAMESPACE = "1.3.6.1.4.1.2312.9"

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
        print extensions

        # Check the certificate version, absence of the extension implies v1.0:
        cert_version_str = "1.0"
        if EXT_CERT_VERSION in extensions:
            cert_version_str = extensions[EXT_CERT_VERSION]

        version = Version(cert_version_str)
        cert = self._create_cert(version, extensions)
        return cert

    def _create_cert(self, version, extensions):
        cert_class = VERSION_IMPLEMENTATIONS[version.major] \
                [self._get_cert_type(extensions)]
        cert = cert_class(version=version)
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
    def __init__(self, version=None):
        self.version = version


class ProductCertificate1(Certificate):
    pass


class EntitlementCertificate1(Certificate):
    pass


class ProductCertificate2(Certificate):
    pass


class EntitlementCertificate2(Certificate):
    pass



class CertificateException(Exception):
    pass

# Maps a major cert version to the class implementations to use for
# each certificate type:
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

