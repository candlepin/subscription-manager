# Copyright (c) 2026 Red Hat, Inc.
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
import tempfile
import unittest
import rhsm._certificate

# Self-signed certificate generated using:
#
# openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc \
#   -keyout key.pem -out cert.pem -sha256 \
#   -subj "/CN=test.example.com/O=Example Org" -set_serial 0x0123456789ABCDEF0123 \
#   -not_before 20260101000000Z -not_after 21260101000000Z \
#   -addext "basicConstraints=critical,CA:FALSE" \
#   -addext "subjectAltName=DNS:test.example.com" \
#   -addext "1.3.6.1.4.1.2312.9.99.1=ASN1:UTF8String:Red Hat Enterprise Linux" \
#   -addext "1.3.6.1.4.1.2312.9.99.2=ASN1:FORMAT:HEX,OCTETSTRING:0001FEFF"
TEST_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIICDDCCAbGgAwIBAgIKASNFZ4mrze8BIzAKBggqhkjOPQQDAjAxMRkwFwYDVQQD
DBB0ZXN0LmV4YW1wbGUuY29tMRQwEgYDVQQKDAtFeGFtcGxlIE9yZzAgFw0yNjAx
MDEwMDAwMDBaGA8yMTI2MDEwMTAwMDAwMFowMTEZMBcGA1UEAwwQdGVzdC5leGFt
cGxlLmNvbTEUMBIGA1UECgwLRXhhbXBsZSBPcmcwWTATBgcqhkjOPQIBBggqhkjO
PQMBBwNCAAQrMhN6pkoCkOzGjigfeYWyRkl25S0C0efLMm2O4OZTB+SI7oTl8W6v
Va3Smhen+U4eWex9KqfGSp2Eu5mZ4e0Ao4GuMIGrMB0GA1UdDgQWBBTwX5ihdqUs
yCyoKUjm/nPMohdn4zAfBgNVHSMEGDAWgBTwX5ihdqUsyCyoKUjm/nPMohdn4zAM
BgNVHRMBAf8EAjAAMBsGA1UdEQQUMBKCEHRlc3QuZXhhbXBsZS5jb20wKAYKKwYB
BAGSCAljAQQaDBhSZWQgSGF0IEVudGVycHJpc2UgTGludXgwFAYKKwYBBAGSCAlj
AgQGBAQAAf7/MAoGCCqGSM49BAMCA0kAMEYCIQCV613YrBlBRxhWZyIlELfvcnHo
6/PsedbXIIGLFGFdBQIhAM24uFG5RX/q3UrvpqLGCwDvk9KoFNeRdVyTueexjMOI
-----END CERTIFICATE-----
"""

# Private key of TEST_CERT_PEM (used only by this test)
TEST_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQggFX8L/eIIiPWVESS
aXAHrstm1g7GMsjGJP4SQ+Fm3iOhRANCAAQrMhN6pkoCkOzGjigfeYWyRkl25S0C
0efLMm2O4OZTB+SI7oTl8W6vVa3Smhen+U4eWex9KqfGSp2Eu5mZ4e0A
-----END PRIVATE KEY-----
"""

TEST_SUBJECT = {"CN": "test.example.com", "O": "Example Org"}
TEST_SERIAL = 0x0123456789ABCDEF0123
TEST_NOT_BEFORE = "Jan  1 00:00:00 2026 GMT"
TEST_NOT_AFTER = "Jan  1 00:00:00 2126 GMT"

SUBJECT_KEY_ID_OID = "2.5.29.14"
SUBJECT_KEY_ID_VALUE = bytes.fromhex("F05F98A176A52CC82CA82948E6FE73CCA21767E3")
AUTHORITY_KEY_ID_OID = "2.5.29.35"
BASIC_CONSTRAINTS_OID = "2.5.29.19"
SUBJECT_ALT_NAME_OID = "2.5.29.17"
SUBJECT_ALT_NAME_VALUE = b"DNS:test.example.com"
UTF8_EXT_OID = "1.3.6.1.4.1.2312.9.99.1"
UTF8_EXT_VALUE = b"Red Hat Enterprise Linux"
OCTET_EXT_OID = "1.3.6.1.4.1.2312.9.99.2"
# Binary value containing NUL byte to make sure it is not handled as C string
OCTET_EXT_VALUE = b"\x00\x01\xfe\xff"


class TestCertificateSO(unittest.TestCase):

    def helper_test_list_of_algorithms(self, algorithms):
        """
        The list of algorithms should contain OIDs of supported algorithms.
        """
        self.assertIsInstance(algorithms, list)
        self.assertGreater(len(algorithms), 0)
        for algo in algorithms:
            self.assertTrue(isinstance(algo, str))
            # The algorithm should be represented as OID
            self.assertRegex(algo, r"^[0-9]+(\.[0-9]+)+$")

    def test_get_public_key_algorithms(self):
        """
        Test that the public key algorithms are returned.
        The list should contain OIDs of supported algorithms.
        The list of OIDs could be different on different systems.
        """
        pub_key_algos = rhsm._certificate.get_public_key_algorithms()
        self.helper_test_list_of_algorithms(pub_key_algos)

    def test_get_signature_algorithms(self):
        """
        Test that the signature algorithms are returned.
        The list should contain OIDs of supported algorithms.
        The list of OIDs could be different on different systems.
        """
        signature_algos = rhsm._certificate.get_signature_algorithms()
        self.helper_test_list_of_algorithms(signature_algos)


class TestLoadSO(unittest.TestCase):
    def test_load_cert_from_pem(self):
        """
        Test loading certificate from PEM string
        """
        cert = rhsm._certificate.load(pem=TEST_CERT_PEM)
        self.assertIsInstance(cert, rhsm._certificate.X509)

    def test_load_cert_from_file(self):
        """
        Test loading certificate from file
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as cert_file:
            cert_file.write(TEST_CERT_PEM)
        try:
            cert = rhsm._certificate.load(file=cert_file.name)
        finally:
            os.unlink(cert_file.name)
        self.assertIsInstance(cert, rhsm._certificate.X509)

    def test_load_cert_invalid_pem(self):
        """
        Test that loading of invalid PEM raises exception
        """
        with self.assertRaises(rhsm._certificate.OpenSSLCertificateLoadingError):
            rhsm._certificate.load(pem="This is not a certificate")

    def test_load_cert_missing_file(self):
        """
        Test that loading of missing file raises exception
        """
        with self.assertRaises(rhsm._certificate.OpenSSLCertificateLoadingError):
            rhsm._certificate.load(file="/nonexistent/directory/cert.pem")

    def test_load_private_key(self):
        """
        Test loading private key from PEM string
        """
        key = rhsm._certificate.load_private_key(pem=TEST_KEY_PEM)
        self.assertIsInstance(key, rhsm._certificate.PrivateKey)

    def test_load_private_key_invalid(self):
        """
        Test that loading of invalid private key returns None
        """
        key = rhsm._certificate.load_private_key(pem="This is not a key")
        self.assertIsNone(key)


class TestX509SO(unittest.TestCase):
    def setUp(self):
        self.cert = rhsm._certificate.load(pem=TEST_CERT_PEM)

    def test_get_subject(self):
        self.assertEqual(self.cert.get_subject(), TEST_SUBJECT)

    def test_get_issuer(self):
        """
        The certificate is self-signed, so issuer is the same as subject
        """
        self.assertEqual(self.cert.get_issuer(), TEST_SUBJECT)

    def test_get_serial_number(self):
        """
        The serial number is bigger than 64 bits
        """
        self.assertEqual(self.cert.get_serial_number(), TEST_SERIAL)

    def test_get_not_before(self):
        self.assertEqual(self.cert.get_not_before(), TEST_NOT_BEFORE)

    def test_get_not_after(self):
        self.assertEqual(self.cert.get_not_after(), TEST_NOT_AFTER)

    def test_get_extension_utf8_string(self):
        """
        Value of UTF8String extension is returned without DER header
        """
        self.assertEqual(self.cert.get_extension(oid=UTF8_EXT_OID), UTF8_EXT_VALUE)

    def test_get_extension_octet_string(self):
        """
        Value of OCTET STRING extension is returned as raw bytes
        """
        self.assertEqual(self.cert.get_extension(oid=OCTET_EXT_OID), OCTET_EXT_VALUE)
        self.assertEqual(self.cert.get_extension(oid=SUBJECT_KEY_ID_OID), SUBJECT_KEY_ID_VALUE)

    def test_get_extension_by_oid_positional(self):
        self.assertEqual(self.cert.get_extension(UTF8_EXT_OID), UTF8_EXT_VALUE)

    def test_get_extension_by_name(self):
        """
        Other extensions are printed in human-readable form by OpenSSL
        """
        self.assertEqual(self.cert.get_extension(name="subjectAltName"), SUBJECT_ALT_NAME_VALUE)
        self.assertEqual(self.cert.get_extension(name="basicConstraints"), b"CA:FALSE")

    def test_get_extension_missing(self):
        # Valid OID, but the certificate does not contain such extension
        self.assertIsNone(self.cert.get_extension(oid="1.3.6.1.4.1.2312.9.99.42"))
        # Unknown extension name
        self.assertIsNone(self.cert.get_extension(name="noSuchExtension"))
        # Invalid OID
        self.assertIsNone(self.cert.get_extension(oid="not an oid"))

    def test_get_all_extensions(self):
        extensions = self.cert.get_all_extensions()
        self.assertEqual(
            set(extensions.keys()),
            {
                SUBJECT_KEY_ID_OID,
                AUTHORITY_KEY_ID_OID,
                BASIC_CONSTRAINTS_OID,
                SUBJECT_ALT_NAME_OID,
                UTF8_EXT_OID,
                OCTET_EXT_OID,
            },
        )
        for value in extensions.values():
            self.assertIsInstance(value, bytes)
        self.assertEqual(extensions[SUBJECT_KEY_ID_OID], SUBJECT_KEY_ID_VALUE)
        self.assertEqual(extensions[BASIC_CONSTRAINTS_OID], b"CA:FALSE")
        self.assertEqual(extensions[SUBJECT_ALT_NAME_OID], SUBJECT_ALT_NAME_VALUE)
        self.assertEqual(extensions[UTF8_EXT_OID], UTF8_EXT_VALUE)
        self.assertEqual(extensions[OCTET_EXT_OID], OCTET_EXT_VALUE)

    def test_as_pem(self):
        self.assertEqual(self.cert.as_pem(), TEST_CERT_PEM)

    def test_as_text(self):
        text = self.cert.as_text()
        self.assertIn("Certificate:", text)
        self.assertIn("CN=test.example.com", text)
        self.assertIn("DNS:test.example.com", text)
