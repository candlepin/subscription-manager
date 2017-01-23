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
 *
 * This is an openssl wrapper to access X509 extensions. It is intended for use
 * internally to rhsm only, and as such, will be subject to api breakage.
 *
 * Example usage:
 *
 * from rhsm import _certificate
 *
 * x509 = _certificate.load(pem=my_pem_string)
 *
 * print x509.get_extension('10.11.1.2.9.7')
 * print x509.get_extension(name='subjectAltName')
 *
 * So why do we need this? The same versions of all python ssl bindings aren't
 * available everywhere we need it (el 5 vs 6, etc), and in some cases, the
 * behaviour of the libraries or commands changes across versions.
 *
 * Our specific need is to read non-standard extension values, as either
 * UTF8 strings,  or binary octets. M2Crypto and openssl itself default to
 * assuming that the extension payload is a printable string value, and
 * giving you that. This is why you see ".." in front of most extension values.
 * Those are non printable characters that make up the DER encoded header of
 * the value. You can instruct the openssl cli command to print out the
 * structural information of a value, and use that to glean the type and do
 * some parsing yourself (if necessary), but this argument does not work the
 * same across all versions either.
 *
 * Thus, we write our own binding!
 */

#include "Python.h"

#include <openssl/asn1.h>
#include <openssl/asn1t.h>
#include <openssl/opensslv.h>
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

#include "structmember.h"

#define MAX_BUF 256

/* Python 2/3 compatiblity defines */
#if PY_MAJOR_VERSION >= 3
#define PyString_FromStringAndSize(value, length) \
	PyUnicode_FromStringAndSize(value, length);
#define PyString_FromString(value) \
	PyUnicode_FromString(value);
#endif

/* OpenSSL pre version 1.1 compatibility defines */
#if OPENSSL_VERSION_NUMBER < 0x10100000L
	#define X509_EXTENSION_get_data(o) ((o)->value)
	#define X509_EXTENSION_get_object(o) ((o)->object)
	#define ASN1_STRING_get0_data(o) ASN1_STRING_data(o)
#endif

typedef struct {
	PyObject_HEAD;
	X509 *x509;
} certificate_x509;

typedef struct {
	PyObject_HEAD;
	EVP_PKEY *key;
} private_key;

static void
certificate_x509_dealloc (certificate_x509 *self)
{
	X509_free (self->x509);
	Py_TYPE(self)->tp_free ((PyObject *) self);
}

static void
private_key_dealloc (private_key *self)
{
	EVP_PKEY_free (self->key);
	Py_TYPE(self)->tp_free ((PyObject *) self);
}

static PyObject *get_not_before (certificate_x509 *self, PyObject *varargs);
static PyObject *get_not_after (certificate_x509 *self, PyObject *varargs);
static PyObject *get_serial_number (certificate_x509 *self, PyObject *varargs);
static PyObject *get_subject (certificate_x509 *self, PyObject *varargs);
static PyObject *get_issuer(certificate_x509 *self, PyObject *varargs);
static PyObject *get_extension (certificate_x509 *self, PyObject *varargs,
				PyObject *keywords);
static PyObject *get_all_extensions (certificate_x509 *self, PyObject *varargs);
static PyObject *as_pem (certificate_x509 *self, PyObject *varargs);
static PyObject *as_text (certificate_x509 *self, PyObject *varargs);

static PyMethodDef x509_methods[] = {
	{"get_not_before", (PyCFunction) get_not_before, METH_VARARGS,
	 "get the certificate's start time"},
	{"get_not_after", (PyCFunction) get_not_after, METH_VARARGS,
	 "get the certificate's end time"},
	{"get_serial_number", (PyCFunction) get_serial_number, METH_VARARGS,
	 "get the certificate's serial number"},
	{"get_subject", (PyCFunction) get_subject, METH_VARARGS,
	 "get the certificate's subject"},
	{"get_issuer", (PyCFunction) get_issuer, METH_VARARGS,
	 "get the certificate's issuer"},
	{"get_extension", (PyCFunction) get_extension,
	 METH_VARARGS | METH_KEYWORDS,
	 "get the string representation of an extension by oid"},
	{"get_all_extensions", (PyCFunction) get_all_extensions, METH_VARARGS,
	 "get a dict of oid: value"},
	{"as_pem", (PyCFunction) as_pem, METH_VARARGS,
	 "return the pem representation of this certificate"},
	{"as_text", (PyCFunction) as_text, METH_VARARGS,
	 "return the text representation of this certificate (such as printed by openssl x509 -noout -text)"},
	{NULL}
};

static PyTypeObject certificate_x509_type = {
	PyVarObject_HEAD_INIT (NULL, 0)
	"_certificate.X509",
	sizeof (certificate_x509),
	0,			/*tp_itemsize */
	(destructor) certificate_x509_dealloc,
	0,			/*tp_print */
	0,			/*tp_getattr */
	0,			/*tp_setattr */
	0,			/*tp_compare */
	0,			/*tp_repr */
	0,			/*tp_as_number */
	0,			/*tp_as_sequence */
	0,			/*tp_as_mapping */
	0,			/*tp_hash */
	0,			/*tp_call */
	0,			/*tp_str */
	0,			/*tp_getattro */
	0,			/*tp_setattro */
	0,			/*tp_as_buffer */
	Py_TPFLAGS_DEFAULT,	/*tp_flags */
	"X509 Certificate",	/* tp_doc */
	0,			/* tp_traverse */
	0,			/* tp_clear */
	0,			/* tp_richcompare */
	0,			/* tp_weaklistoffset */
	0,			/* tp_iter */
	0,			/* tp_iternext */
	x509_methods,		/* tp_methods */
	0,			/* tp_members */
	0,			/* tp_getset */
	0,			/* tp_base */
	0,			/* tp_dict */
	0,			/* tp_descr_get */
	0,			/* tp_descr_set */
	0,			/* tp_dictoffset */
	0,			/* tp_init */
	0,			/* tp_alloc */
	0,			/* tp_new */
};

static PyTypeObject private_key_type = {
	PyVarObject_HEAD_INIT (NULL, 0)
	"_certificate.PrivateKey",
	sizeof (private_key),
	0,			/*tp_itemsize */
	(destructor) private_key_dealloc,
	0,			/*tp_print */
	0,			/*tp_getattr */
	0,			/*tp_setattr */
	0,			/*tp_compare */
	0,			/*tp_repr */
	0,			/*tp_as_number */
	0,			/*tp_as_sequence */
	0,			/*tp_as_mapping */
	0,			/*tp_hash */
	0,			/*tp_call */
	0,			/*tp_str */
	0,			/*tp_getattro */
	0,			/*tp_setattro */
	0,			/*tp_as_buffer */
	Py_TPFLAGS_DEFAULT,	/*tp_flags */
	"Private Key",	    /* tp_doc */
	0,			/* tp_traverse */
	0,			/* tp_clear */
	0,			/* tp_richcompare */
	0,			/* tp_weaklistoffset */
	0,			/* tp_iter */
	0,			/* tp_iternext */
	0,			/* tp_methods */
	0,			/* tp_members */
	0,			/* tp_getset */
	0,			/* tp_base */
	0,			/* tp_dict */
	0,			/* tp_descr_get */
	0,			/* tp_descr_set */
	0,			/* tp_dictoffset */
	0,			/* tp_init */
	0,			/* tp_alloc */
	0,			/* tp_new */
};

static size_t
get_extension_by_object (X509 *x509, ASN1_OBJECT *obj, char **output)
{
	int pos = X509_get_ext_by_OBJ (x509, obj, -1);
	if (pos < 0) {
		return 0;
	}
	X509_EXTENSION *ext = X509_get_ext (x509, pos);

	int tag;
	long len;
	int tc;
	const unsigned char *p = X509_EXTENSION_get_data(ext)->data;

	ASN1_get_object (&p, &len, &tag, &tc, X509_EXTENSION_get_data(ext)->length);

	size_t size;
	switch (tag) {
		case V_ASN1_UTF8STRING:
			{
				ASN1_UTF8STRING *str =
					ASN1_item_unpack (X509_EXTENSION_get_data(ext),
							  ASN1_ITEM_rptr
							  (ASN1_UTF8STRING));
				*output = strndup ((const char *)
						   ASN1_STRING_get0_data (str),
						   str->length);
				size = str->length;
				ASN1_UTF8STRING_free (str);
				return size;
			}
		case V_ASN1_OCTET_STRING:
			{
				ASN1_OCTET_STRING *octstr =
					ASN1_item_unpack (X509_EXTENSION_get_data(ext),
							  ASN1_ITEM_rptr
							  (ASN1_OCTET_STRING));
				*output = malloc (octstr->length);
				memcpy (*output, octstr->data, octstr->length);
				size = octstr->length;
				ASN1_OCTET_STRING_free (octstr);
				return size;
			}
		default:
			{
				BIO *bio = BIO_new (BIO_s_mem ());
				X509V3_EXT_print (bio, ext, 0, 0);

				size_t size = BIO_ctrl_pending (bio);
				char *buf = malloc (sizeof (char) * size);
				BIO_read (bio, buf, size);
				*output = buf;
				BIO_free (bio);
				return size;
			}
	}
}

static ASN1_OBJECT *
get_object_by_oid (const char *oid)
{
	return OBJ_txt2obj (oid, 1);
}

static ASN1_OBJECT *
get_object_by_name (const char *name)
{
	int nid = OBJ_txt2nid (name);
	return OBJ_nid2obj (nid);
}

static PyObject *
load_cert (PyObject *self, PyObject *args, PyObject *keywords)
{
	const char *file_name = NULL;
	const char *pem = NULL;

	static char *keywordlist[] = { "file", "pem", NULL };

	if (!PyArg_ParseTupleAndKeywords (args, keywords, "|ss", keywordlist,
					  &file_name, &pem)) {
		return NULL;
	}

	BIO *bio;
	if (pem != NULL) {
		bio = BIO_new_mem_buf ((void *) pem, strlen (pem));
	} else {
		bio = BIO_new_file (file_name, "r");
	}

	X509 *x509 = PEM_read_bio_X509 (bio, NULL, NULL, NULL);
	BIO_free (bio);

	if (x509 == NULL) {
		Py_INCREF (Py_None);
		return Py_None;
	}

	certificate_x509 *py_x509 =
		(certificate_x509 *) _PyObject_New (&certificate_x509_type);
	py_x509->x509 = x509;
	return (PyObject *) py_x509;
}

static PyObject *
load_private_key (PyObject *self, PyObject *args, PyObject *keywords)
{
	const char *file_name = NULL;
	const char *pem = NULL;

	static char *keywordlist[] = { "file", "pem", NULL };

	if (!PyArg_ParseTupleAndKeywords (args, keywords, "|ss", keywordlist,
					  &file_name, &pem)) {
		return NULL;
	}

	BIO *bio;
	if (pem != NULL) {
		bio = BIO_new_mem_buf ((void *) pem, strlen (pem));
	} else {
		bio = BIO_new_file (file_name, "r");
	}

	EVP_PKEY* key = PEM_read_bio_PrivateKey (bio, NULL, NULL, NULL);
	BIO_free (bio);

	if (key == NULL) {
		Py_INCREF (Py_None);
		return Py_None;
	}

	private_key *py_key =
		(private_key *) _PyObject_New (&private_key_type);
	py_key->key = key;
	return (PyObject *) py_key;
}

static PyObject *
get_extension (certificate_x509 *self, PyObject *args, PyObject *keywords)
{
	const char *oid = NULL;
	const char *name = NULL;

	static char *keywordlist[] = { "oid", "name", NULL };

	if (!PyArg_ParseTupleAndKeywords (args, keywords, "|ss", keywordlist,
					  &oid, &name)) {
		return NULL;
	}

	char *value = NULL;
	size_t length;
	ASN1_OBJECT *obj = NULL;
	if (name != NULL) {
		obj = get_object_by_name (name);
	} else {
		obj = get_object_by_oid (oid);
	}

	if (obj == NULL) {
		Py_INCREF (Py_None);
		return Py_None;
	}

	length = get_extension_by_object (self->x509, obj, &value);
	ASN1_OBJECT_free (obj);
	if (value != NULL) {
		PyObject *extension = PyBytes_FromStringAndSize (value,
								  length);
		free (value);
		return extension;
	} else {
		Py_INCREF (Py_None);
		return Py_None;
	}
}

static PyObject *
get_all_extensions (certificate_x509 *self, PyObject *args)
{
	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	int i;
	int ext_count = X509_get_ext_count (self->x509);

	char oid[MAX_BUF];
	PyObject *dict = PyDict_New ();
	for (i = 0; i < ext_count; i++) {
		X509_EXTENSION *ext = X509_get_ext (self->x509, i);

		OBJ_obj2txt (oid, MAX_BUF, X509_EXTENSION_get_object(ext), 1);
		PyObject *key = PyString_FromString (oid);

		char *value = NULL;
		size_t length =
			get_extension_by_object (self->x509, X509_EXTENSION_get_object(ext),
						 &value);

		PyObject *dict_value = PyBytes_FromStringAndSize (value,
								   length);
		free (value);
		PyDict_SetItem (dict, key, dict_value);

		Py_DECREF (key);
		Py_DECREF (dict_value);
	}

	return dict;
}

static PyObject *
as_pem (certificate_x509 *self, PyObject *args)
{
	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	BIO *bio = BIO_new (BIO_s_mem ());
	PEM_write_bio_X509 (bio, self->x509);

	size_t size = BIO_ctrl_pending (bio);
	char *buf = malloc (sizeof (char) * size);
	BIO_read (bio, buf, size);
	BIO_free (bio);

	PyObject *pem = PyString_FromStringAndSize (buf, size);
	free (buf);
	return pem;
}

static PyObject *
as_text (certificate_x509 *self, PyObject *args)
{
	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	BIO *bio = BIO_new (BIO_s_mem ());
	X509_print (bio, self->x509);

	size_t size = BIO_ctrl_pending (bio);
	char *buf = malloc (sizeof (char) * size);
	BIO_read (bio, buf, size);
	BIO_free (bio);

	PyObject *pem = PyString_FromStringAndSize (buf, size);
	free (buf);
	return pem;
}

static PyObject *
get_serial_number (certificate_x509 *self, PyObject *args)
{
	PyObject *ret;

	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	ASN1_INTEGER *serial_asn = X509_get_serialNumber (self->x509);
	BIGNUM *bn = ASN1_INTEGER_to_BN (serial_asn, NULL);

	char *hex = BN_bn2hex (bn);

	BN_free (bn);
	ret = PyLong_FromString (hex, NULL, 16);
	OPENSSL_free (hex);
	return ret;
}

static PyObject *
get_subject (certificate_x509 *self, PyObject *args)
{
	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	X509_NAME *name = X509_get_subject_name (self->x509);
	int entries = X509_NAME_entry_count (name);
	int i;

	PyObject *dict = PyDict_New ();
	for (i = 0; i < entries; i++) {
		X509_NAME_ENTRY *entry = X509_NAME_get_entry (name, i);
		ASN1_OBJECT *obj = X509_NAME_ENTRY_get_object (entry);
		ASN1_STRING *data = X509_NAME_ENTRY_get_data (entry);

		PyObject *key =
			PyString_FromString (OBJ_nid2sn (OBJ_obj2nid (obj)));
		PyObject *value = PyString_FromString ((const char *)
						       ASN1_STRING_get0_data (data));
		PyDict_SetItem (dict, key, value);

		Py_DECREF (key);
		Py_DECREF (value);
	}

	return dict;
}

static PyObject *
get_issuer (certificate_x509 *self, PyObject *args)
{
	if (!PyArg_ParseTuple (args, "")) {
		return NULL;
	}

	X509_NAME *name = X509_get_issuer_name (self->x509);
	int entries = X509_NAME_entry_count (name);
	int i;

	PyObject *dict = PyDict_New ();
	for (i = 0; i < entries; i++) {
		X509_NAME_ENTRY *entry = X509_NAME_get_entry (name, i);
		ASN1_OBJECT *obj = X509_NAME_ENTRY_get_object (entry);
		ASN1_STRING *data = X509_NAME_ENTRY_get_data (entry);

		PyObject *key =
			PyString_FromString (OBJ_nid2sn (OBJ_obj2nid (obj)));
		PyObject *value = PyString_FromString ((const char *)
						       ASN1_STRING_get0_data (data));
		PyDict_SetItem (dict, key, value);

		Py_DECREF (key);
		Py_DECREF (value);
	}

	return dict;
}

static PyObject *
time_to_string (ASN1_UTCTIME *time)
{
	BIO *bio = BIO_new (BIO_s_mem ());
	ASN1_UTCTIME_print (bio, time);

	size_t size = BIO_ctrl_pending (bio);
	char *buf = malloc (sizeof (char) * size);
	BIO_read (bio, buf, size);
	BIO_free (bio);

	PyObject *time_str = PyString_FromStringAndSize (buf, size);
	free (buf);
	return time_str;
}

static PyObject *
get_not_before (certificate_x509 *self, PyObject *args)
{
	ASN1_UTCTIME *time = X509_get_notBefore (self->x509);
	return time_to_string (time);
}

static PyObject *
get_not_after (certificate_x509 *self, PyObject *args)
{
	ASN1_UTCTIME *time = X509_get_notAfter (self->x509);
	return time_to_string (time);
}

static PyMethodDef cert_methods[] = {
	{"load", (PyCFunction) load_cert, METH_VARARGS | METH_KEYWORDS,
	 "load a certificate from a file"},
	{"load_private_key", (PyCFunction) load_private_key, METH_VARARGS | METH_KEYWORDS,
	 "load a private key from a file"},
	{NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
	PyModuleDef_HEAD_INIT,
	"_certificate",
	NULL,
	0,
	cert_methods,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC
PyInit__certificate (void)
#else
PyMODINIT_FUNC
init_certificate (void)
#endif
{
	PyObject *module;
	#if PY_MAJOR_VERSION >= 3
	module = PyModule_Create (&moduledef);
	#else
	module = Py_InitModule ("_certificate", cert_methods);
	#endif

	certificate_x509_type.tp_new = PyType_GenericNew;
	if (PyType_Ready (&certificate_x509_type) < 0) {
		return;
	}

	Py_INCREF (&certificate_x509_type);
	PyModule_AddObject (module, "X509",
			    (PyObject *) & certificate_x509_type);

    private_key_type.tp_new = PyType_GenericNew;
	if (PyType_Ready (&private_key_type) < 0) {
		return;
	}

	Py_INCREF (&private_key_type);
	PyModule_AddObject (module, "PrivateKey",
			    (PyObject *) & private_key_type);
	#if PY_MAJOR_VERSION >= 3
	return module;
	#endif
}
