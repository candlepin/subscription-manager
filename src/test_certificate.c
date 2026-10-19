/*
 * Copyright (c) 2012 Red Hat, Inc.
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 *
 * Red Hat trademarks are not licensed under GPLv2. No permission is
 * granted to use or replicate Red Hat trademarks that are incorporated
 * in this software or its documentation.
 */

#include <Python.h>

#include <string.h>

#include <glib.h>
#include <glib/gstdio.h>
#include <gio/gio.h>

#include <openssl/bio.h>
#include <openssl/bn.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

#include "certificate.h"

#define TEST_CN "test.example.com"
#define TEST_ORG "Example Org"
#define TEST_SERIAL_HEX "0123456789ABCDEF0123"
/* 2026-01-01 00:00:00 UTC and 2036-01-01 00:00:00 UTC */
#define TEST_NOT_BEFORE 1767225600
#define TEST_NOT_AFTER 2082844800
#define TEST_NOT_BEFORE_STR "Jan  1 00:00:00 2026 GMT"
#define TEST_NOT_AFTER_STR "Jan  2 00:00:00 2036 GMT"
#define TEST_UTF8_EXT_OID "1.3.6.1.4.1.2312.9.99.1"
#define TEST_UTF8_EXT_VALUE "Red Hat Enterprise Linux"
#define TEST_OCTET_EXT_OID "1.3.6.1.4.1.2312.9.99.2"
#define TEST_SAN_OID "2.5.29.17"
#define TEST_SAN_VALUE "DNS:" TEST_CN
#define TEST_BASIC_CONSTRAINTS_OID "2.5.29.19"
#define TEST_EXT_COUNT 4

/* Binary value containing NUL byte to make sure it is not handled as C string */
static const unsigned char TEST_OCTET_EXT_VALUE[] = {0x00, 0x01, 0xfe, 0xff};

static PyObject *certificate_module = NULL;
/* Looked up in advance, because Python API must not be called while an exception is set */
static PyObject *loading_error = NULL;

typedef struct {
    EVP_PKEY *key;
    gchar *cert_pem;
    gchar *key_pem;
    PyObject *cert;
} CertFixture;

/* Call method of obj with one keyword string argument, e.g. load(pem="...") */
static PyObject *call_with_kwarg(PyObject *obj, const char *method, const char *key, const char *value) {
    PyObject *func = PyObject_GetAttrString(obj, method);
    g_assert_nonnull(func);
    PyObject *args = PyTuple_New(0);
    PyObject *kwargs = Py_BuildValue("{s:s}", key, value);
    PyObject *result = PyObject_Call(func, args, kwargs);
    Py_DECREF(kwargs);
    Py_DECREF(args);
    Py_DECREF(func);
    return result;
}

static void assert_instance_of(PyObject *obj, const char *type_name) {
    PyObject *type = PyObject_GetAttrString(certificate_module, type_name);
    g_assert_nonnull(type);
    g_assert_cmpint(PyObject_IsInstance(obj, type), ==, 1);
    Py_DECREF(type);
}

static void assert_raised(PyObject *exception) {
    g_assert_nonnull(PyErr_Occurred());
    g_assert_cmpint(PyErr_ExceptionMatches(exception), ==, 1);
    PyErr_Clear();
    ERR_clear_error();
}

static void assert_bytes_equal(PyObject *obj, const void *expected, Py_ssize_t expected_len) {
    g_assert_nonnull(obj);
    g_assert_cmpint(PyBytes_Check(obj), ==, 1);
    g_assert_cmpint(PyBytes_Size(obj), ==, expected_len);
    g_assert_cmpmem(PyBytes_AsString(obj), expected_len, expected, expected_len);
}

static void assert_dict_str_item(PyObject *dict, const char *key, const char *expected) {
    PyObject *value = PyDict_GetItemString(dict, key);
    g_assert_nonnull(value);
    g_assert_cmpstr(PyUnicode_AsUTF8(value), ==, expected);
}

static gchar *bio_to_string(BIO *bio) {
    char *data = NULL;
    long len = BIO_get_mem_data(bio, &data);
    return g_strndup(data, len);
}

/* Add extension with given OID and DER encoded value */
static void add_der_extension(X509 *x509, const char *oid, const unsigned char *der, int der_len) {
    ASN1_OBJECT *obj = OBJ_txt2obj(oid, 1);
    g_assert_nonnull(obj);
    ASN1_OCTET_STRING *data = ASN1_OCTET_STRING_new();
    g_assert_cmpint(ASN1_OCTET_STRING_set(data, der, der_len), ==, 1);
    X509_EXTENSION *ext = X509_EXTENSION_create_by_OBJ(NULL, obj, 0, data);
    g_assert_nonnull(ext);
    g_assert_cmpint(X509_add_ext(x509, ext, -1), ==, 1);
    X509_EXTENSION_free(ext);
    ASN1_OCTET_STRING_free(data);
    ASN1_OBJECT_free(obj);
}

static void add_utf8_extension(X509 *x509, const char *oid, const char *value) {
    ASN1_UTF8STRING *str = ASN1_UTF8STRING_new();
    g_assert_cmpint(ASN1_STRING_set(str, value, -1), ==, 1);
    unsigned char *der = NULL;
    int der_len = i2d_ASN1_UTF8STRING(str, &der);
    g_assert_cmpint(der_len, >, 0);
    add_der_extension(x509, oid, der, der_len);
    OPENSSL_free(der);
    ASN1_UTF8STRING_free(str);
}

static void add_octet_extension(X509 *x509, const char *oid, const unsigned char *value, int len) {
    ASN1_OCTET_STRING *str = ASN1_OCTET_STRING_new();
    g_assert_cmpint(ASN1_OCTET_STRING_set(str, value, len), ==, 1);
    unsigned char *der = NULL;
    int der_len = i2d_ASN1_OCTET_STRING(str, &der);
    g_assert_cmpint(der_len, >, 0);
    add_der_extension(x509, oid, der, der_len);
    OPENSSL_free(der);
    ASN1_OCTET_STRING_free(str);
}

/* Add standard extension using the same syntax as openssl.cnf */
static void add_conf_extension(X509 *x509, int nid, const char *value) {
    X509V3_CTX ctx;
    X509V3_set_ctx_nodb(&ctx);
    X509V3_set_ctx(&ctx, x509, x509, NULL, NULL, 0);
    X509_EXTENSION *ext = X509V3_EXT_nconf_nid(NULL, &ctx, nid, value);
    g_assert_nonnull(ext);
    g_assert_cmpint(X509_add_ext(x509, ext, -1), ==, 1);
    X509_EXTENSION_free(ext);
}

/* Create self-signed certificate with well-known content */
static X509 *create_test_certificate(EVP_PKEY *key) {
    X509 *x509 = X509_new();
    g_assert_nonnull(x509);
    g_assert_cmpint(X509_set_version(x509, X509_VERSION_3), ==, 1);

    BIGNUM *serial = NULL;
    g_assert_cmpint(BN_hex2bn(&serial, TEST_SERIAL_HEX), >, 0);
    g_assert_nonnull(BN_to_ASN1_INTEGER(serial, X509_get_serialNumber(x509)));
    BN_free(serial);

    g_assert_nonnull(ASN1_TIME_set(X509_getm_notBefore(x509), TEST_NOT_BEFORE));
    g_assert_nonnull(ASN1_TIME_set(X509_getm_notAfter(x509), TEST_NOT_AFTER));

    X509_NAME *name = X509_NAME_new();
    g_assert_cmpint(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                                               (const unsigned char *)TEST_CN, -1, -1, 0), ==, 1);
    g_assert_cmpint(X509_NAME_add_entry_by_txt(name, "O", MBSTRING_ASC,
                                               (const unsigned char *)TEST_ORG, -1, -1, 0), ==, 1);
    g_assert_cmpint(X509_set_subject_name(x509, name), ==, 1);
    g_assert_cmpint(X509_set_issuer_name(x509, name), ==, 1);
    X509_NAME_free(name);

    g_assert_cmpint(X509_set_pubkey(x509, key), ==, 1);

    add_conf_extension(x509, NID_basic_constraints, "critical,CA:FALSE");
    add_conf_extension(x509, NID_subject_alt_name, TEST_SAN_VALUE);
    add_utf8_extension(x509, TEST_UTF8_EXT_OID, TEST_UTF8_EXT_VALUE);
    add_octet_extension(x509, TEST_OCTET_EXT_OID, TEST_OCTET_EXT_VALUE, sizeof(TEST_OCTET_EXT_VALUE));

    g_assert_cmpint(X509_sign(x509, key, EVP_sha256()), >, 0);
    return x509;
}

static void cert_fixture_setup(CertFixture *fixture, gconstpointer user_data) {
    fixture->key = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
    g_assert_nonnull(fixture->key);

    X509 *x509 = create_test_certificate(fixture->key);
    BIO *bio = BIO_new(BIO_s_mem());
    g_assert_cmpint(PEM_write_bio_X509(bio, x509), ==, 1);
    fixture->cert_pem = bio_to_string(bio);
    BIO_free(bio);
    X509_free(x509);

    bio = BIO_new(BIO_s_mem());
    g_assert_cmpint(PEM_write_bio_PrivateKey(bio, fixture->key, NULL, NULL, 0, NULL, NULL), ==, 1);
    fixture->key_pem = bio_to_string(bio);
    BIO_free(bio);

    fixture->cert = call_with_kwarg(certificate_module, "load", "pem", fixture->cert_pem);
    g_assert_nonnull(fixture->cert);
}

static void cert_fixture_teardown(CertFixture *fixture, gconstpointer user_data) {
    Py_XDECREF(fixture->cert);
    g_free(fixture->key_pem);
    g_free(fixture->cert_pem);
    EVP_PKEY_free(fixture->key);
}

/*
* Unit tests
*/

void test_get_signature_algorithms() {
    const PyObject *obj = get_signature_algorithms(NULL, NULL, NULL);
    g_assert_nonnull(obj);
    g_assert_cmpint(PyList_Check(obj), ==, 1);
    g_assert_cmpint(PyList_Size((PyObject *)obj), >, 0);
    Py_DECREF(obj);
}

void test_get_public_key_algorithms() {
    const PyObject *obj = get_public_key_algorithms(NULL, NULL, NULL);
    g_assert_nonnull(obj);
    g_assert_cmpint(PyList_Check(obj), ==, 1);
    g_assert_cmpint(PyList_Size((PyObject *)obj), >, 0);
    Py_DECREF(obj);
}

void test_load_cert_from_pem(CertFixture *fixture, gconstpointer user_data) {
    assert_instance_of(fixture->cert, "X509");
}

void test_load_cert_from_file(CertFixture *fixture, gconstpointer user_data) {
    GError *error = NULL;
    gchar *path = NULL;
    gint fd = g_file_open_tmp("test_certificate-XXXXXX.pem", &path, &error);
    g_assert_no_error(error);
    g_close(fd, NULL);
    g_file_set_contents(path, fixture->cert_pem, -1, &error);
    g_assert_no_error(error);

    PyObject *cert = call_with_kwarg(certificate_module, "load", "file", path);
    g_unlink(path);
    g_free(path);

    g_assert_nonnull(cert);
    assert_instance_of(cert, "X509");
    Py_DECREF(cert);
}

void test_load_cert_invalid_pem() {
    PyObject *cert = call_with_kwarg(certificate_module, "load", "pem", "This is not a certificate");
    g_assert_null(cert);
    assert_raised(loading_error);
}

void test_load_cert_missing_file() {
    PyObject *cert = call_with_kwarg(certificate_module, "load", "file", "/nonexistent/directory/cert.pem");
    g_assert_null(cert);
    assert_raised(PyExc_RuntimeError);
}

void test_load_private_key(CertFixture *fixture, gconstpointer user_data) {
    PyObject *key = call_with_kwarg(certificate_module, "load_private_key", "pem", fixture->key_pem);
    g_assert_nonnull(key);
    assert_instance_of(key, "PrivateKey");
    Py_DECREF(key);
}

void test_load_private_key_invalid() {
    PyObject *key = call_with_kwarg(certificate_module, "load_private_key", "pem", "This is not a key");
    g_assert_true(key == Py_None);
    Py_DECREF(key);
    ERR_clear_error();
}

void test_load_private_key_missing_file() {
    PyObject *key = call_with_kwarg(certificate_module, "load_private_key", "file", "/nonexistent/directory/key.pem");
    g_assert_null(key);
    assert_raised(PyExc_RuntimeError);
}

void test_get_subject(CertFixture *fixture, gconstpointer user_data) {
    PyObject *subject = PyObject_CallMethod(fixture->cert, "get_subject", NULL);
    g_assert_nonnull(subject);
    g_assert_cmpint(PyDict_Check(subject), ==, 1);
    g_assert_cmpint(PyDict_Size(subject), ==, 2);
    assert_dict_str_item(subject, "CN", TEST_CN);
    assert_dict_str_item(subject, "O", TEST_ORG);
    Py_DECREF(subject);
}

void test_get_issuer(CertFixture *fixture, gconstpointer user_data) {
    PyObject *issuer = PyObject_CallMethod(fixture->cert, "get_issuer", NULL);
    g_assert_nonnull(issuer);
    g_assert_cmpint(PyDict_Check(issuer), ==, 1);
    g_assert_cmpint(PyDict_Size(issuer), ==, 2);
    assert_dict_str_item(issuer, "CN", TEST_CN);
    assert_dict_str_item(issuer, "O", TEST_ORG);
    Py_DECREF(issuer);
}

void test_get_serial_number(CertFixture *fixture, gconstpointer user_data) {
    PyObject *serial = PyObject_CallMethod(fixture->cert, "get_serial_number", NULL);
    g_assert_nonnull(serial);
    g_assert_cmpint(PyLong_Check(serial), ==, 1);
    PyObject *expected = PyLong_FromString(TEST_SERIAL_HEX, NULL, 16);
    g_assert_cmpint(PyObject_RichCompareBool(serial, expected, Py_EQ), ==, 1);
    Py_DECREF(expected);
    Py_DECREF(serial);
}

void test_get_not_before(CertFixture *fixture, gconstpointer user_data) {
    PyObject *not_before = PyObject_CallMethod(fixture->cert, "get_not_before", NULL);
    g_assert_nonnull(not_before);
    g_assert_cmpstr(PyUnicode_AsUTF8(not_before), ==, TEST_NOT_BEFORE_STR);
    Py_DECREF(not_before);
}

void test_get_not_after(CertFixture *fixture, gconstpointer user_data) {
    PyObject *not_after = PyObject_CallMethod(fixture->cert, "get_not_after", NULL);
    g_assert_nonnull(not_after);
    g_assert_cmpstr(PyUnicode_AsUTF8(not_after), ==, TEST_NOT_AFTER_STR);
    Py_DECREF(not_after);
}

void test_get_extension_utf8_string(CertFixture *fixture, gconstpointer user_data) {
    PyObject *value = call_with_kwarg(fixture->cert, "get_extension", "oid", TEST_UTF8_EXT_OID);
    assert_bytes_equal(value, TEST_UTF8_EXT_VALUE, strlen(TEST_UTF8_EXT_VALUE));
    Py_DECREF(value);
}

void test_get_extension_octet_string(CertFixture *fixture, gconstpointer user_data) {
    PyObject *value = call_with_kwarg(fixture->cert, "get_extension", "oid", TEST_OCTET_EXT_OID);
    assert_bytes_equal(value, TEST_OCTET_EXT_VALUE, sizeof(TEST_OCTET_EXT_VALUE));
    Py_DECREF(value);
}

void test_get_extension_by_name(CertFixture *fixture, gconstpointer user_data) {
    /* subjectAltName is a SEQUENCE, so it is printed by X509V3_EXT_print() */
    PyObject *value = call_with_kwarg(fixture->cert, "get_extension", "name", "subjectAltName");
    assert_bytes_equal(value, TEST_SAN_VALUE, strlen(TEST_SAN_VALUE));
    Py_DECREF(value);
}

void test_get_extension_missing(CertFixture *fixture, gconstpointer user_data) {
    /* Valid OID, but the certificate does not contain such extension */
    PyObject *value = call_with_kwarg(fixture->cert, "get_extension", "oid", "1.3.6.1.4.1.2312.9.99.42");
    g_assert_true(value == Py_None);
    Py_DECREF(value);

    /* Unknown extension name */
    value = call_with_kwarg(fixture->cert, "get_extension", "name", "noSuchExtension");
    g_assert_true(value == Py_None);
    Py_DECREF(value);

    /* Invalid OID */
    value = call_with_kwarg(fixture->cert, "get_extension", "oid", "not an oid");
    g_assert_true(value == Py_None);
    Py_DECREF(value);
    ERR_clear_error();
}

void test_get_all_extensions(CertFixture *fixture, gconstpointer user_data) {
    PyObject *extensions = PyObject_CallMethod(fixture->cert, "get_all_extensions", NULL);
    g_assert_nonnull(extensions);
    g_assert_cmpint(PyDict_Check(extensions), ==, 1);
    g_assert_cmpint(PyDict_Size(extensions), ==, TEST_EXT_COUNT);

    g_assert_nonnull(PyDict_GetItemString(extensions, TEST_BASIC_CONSTRAINTS_OID));
    assert_bytes_equal(PyDict_GetItemString(extensions, TEST_SAN_OID),
                       TEST_SAN_VALUE, strlen(TEST_SAN_VALUE));
    assert_bytes_equal(PyDict_GetItemString(extensions, TEST_UTF8_EXT_OID),
                       TEST_UTF8_EXT_VALUE, strlen(TEST_UTF8_EXT_VALUE));
    assert_bytes_equal(PyDict_GetItemString(extensions, TEST_OCTET_EXT_OID),
                       TEST_OCTET_EXT_VALUE, sizeof(TEST_OCTET_EXT_VALUE));
    Py_DECREF(extensions);
}

void test_as_pem(CertFixture *fixture, gconstpointer user_data) {
    PyObject *pem = PyObject_CallMethod(fixture->cert, "as_pem", NULL);
    g_assert_nonnull(pem);
    g_assert_cmpstr(PyUnicode_AsUTF8(pem), ==, fixture->cert_pem);
    Py_DECREF(pem);
}

void test_as_text(CertFixture *fixture, gconstpointer user_data) {
    PyObject *text = PyObject_CallMethod(fixture->cert, "as_text", NULL);
    g_assert_nonnull(text);
    const char *str = PyUnicode_AsUTF8(text);
    g_assert_nonnull(strstr(str, "Certificate:"));
    g_assert_nonnull(strstr(str, "CN=" TEST_CN));
    g_assert_nonnull(strstr(str, TEST_SAN_VALUE));
    Py_DECREF(text);
}

#define add_cert_test(path, func) \
    g_test_add(path, CertFixture, NULL, cert_fixture_setup, func, cert_fixture_teardown)

int main(int argc, char **argv) {
    PyImport_AppendInittab("_certificate", PyInit__certificate);
    Py_Initialize();
    certificate_module = PyImport_ImportModule("_certificate");
    if (certificate_module == NULL) {
        PyErr_Print();
        return 1;
    }
    loading_error = PyObject_GetAttrString(certificate_module, "OpenSSLCertificateLoadingError");
    if (loading_error == NULL) {
        PyErr_Print();
        return 1;
    }

    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/test_certificate/test_get_signature_algorithms", test_get_signature_algorithms);
    g_test_add_func("/test_certificate/test_get_public_key_algorithms", test_get_public_key_algorithms);
    add_cert_test("/test_certificate/test_load_cert_from_pem", test_load_cert_from_pem);
    add_cert_test("/test_certificate/test_load_cert_from_file", test_load_cert_from_file);
    g_test_add_func("/test_certificate/test_load_cert_invalid_pem", test_load_cert_invalid_pem);
    g_test_add_func("/test_certificate/test_load_cert_missing_file", test_load_cert_missing_file);
    add_cert_test("/test_certificate/test_load_private_key", test_load_private_key);
    g_test_add_func("/test_certificate/test_load_private_key_invalid", test_load_private_key_invalid);
    g_test_add_func("/test_certificate/test_load_private_key_missing_file", test_load_private_key_missing_file);
    add_cert_test("/test_certificate/test_get_subject", test_get_subject);
    add_cert_test("/test_certificate/test_get_issuer", test_get_issuer);
    add_cert_test("/test_certificate/test_get_serial_number", test_get_serial_number);
    add_cert_test("/test_certificate/test_get_not_before", test_get_not_before);
    add_cert_test("/test_certificate/test_get_not_after", test_get_not_after);
    add_cert_test("/test_certificate/test_get_extension_utf8_string", test_get_extension_utf8_string);
    add_cert_test("/test_certificate/test_get_extension_octet_string", test_get_extension_octet_string);
    add_cert_test("/test_certificate/test_get_extension_by_name", test_get_extension_by_name);
    add_cert_test("/test_certificate/test_get_extension_missing", test_get_extension_missing);
    add_cert_test("/test_certificate/test_get_all_extensions", test_get_all_extensions);
    add_cert_test("/test_certificate/test_as_pem", test_as_pem);
    add_cert_test("/test_certificate/test_as_text", test_as_text);
    int ret = g_test_run();

    Py_DECREF(loading_error);
    Py_DECREF(certificate_module);
    Py_FinalizeEx();
    return ret;
}
