#include <openssl/asn1.h>
#include <openssl/asn1t.h>
#include <openssl/x509.h>

#include "Python.h"

#define MAX_BUF 256

static size_t
get_extension_by_object(X509 *x509, ASN1_OBJECT *obj, char **output) {
	int pos = X509_get_ext_by_OBJ(x509, obj, -1);
	if (pos < 0) {
		return 0;
	}
	X509_EXTENSION *ext = X509_get_ext(x509, pos);

	int tag;
	long len;
	long tc;
	char *p = ext->value->data;
	int res = ASN1_get_object (&p, &len, &tag, &tc, ext->value->length);

	switch(tag) {
	case V_ASN1_UTF8STRING:
		{
		ASN1_UTF8STRING *str = ASN1_item_unpack(ext->value,
			ASN1_ITEM_rptr(ASN1_UTF8STRING));
		*output = strdup(ASN1_STRING_data(str));
		return strlen(output);
		}
	case V_ASN1_OCTET_STRING:
		{
		ASN1_OCTET_STRING *octstr = ASN1_item_unpack(ext->value,
			ASN1_ITEM_rptr(ASN1_OCTET_STRING));
		*output = malloc(octstr->length);
		memcpy(*output, octstr->data, octstr->length);
		return octstr->length;
		}
	default:
		{
		BIO *bio = BIO_new(BIO_s_mem());
		X509V3_EXT_print(bio, ext, 0, 0);

		size_t size = BIO_ctrl_pending(bio);
		char *buf = malloc(sizeof(char) * size);
		BIO_read(bio, buf, size);
		*output = buf;
		BIO_free(bio);
		return size;
		}
	}
}

ASN1_OBJECT *
get_object_by_oid(const char *oid) {
	return OBJ_txt2obj(oid, 1);
}
	
static ASN1_OBJECT *
get_object_by_name(const char *name) {
	int nid = OBJ_txt2nid(name);
	return OBJ_nid2obj(nid);
}

static PyObject *
load_cert(PyObject *self, PyObject *args, PyObject *keywords) {
	const char *file_name = NULL;
	const char *pem = NULL;

	static char *keywordlist[] = {"file", "pem", NULL};

	if (!PyArg_ParseTupleAndKeywords(args, keywords, "|ss", keywordlist,
					 &file_name, &pem)) {
		return NULL;
	}

	BIO *bio;
	if (pem != NULL) {
		bio = BIO_new_mem_buf(pem, strlen(pem));
	} else {
		bio = BIO_new_file(file_name, "r");
	}

	X509 *x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL);
	BIO_free(bio);

	return PyCObject_FromVoidPtr(x509, X509_free);
}

static PyObject *
get_extension(PyObject *self, PyObject *args, PyObject *keywords) {
	X509 *x509;
	PyCObject *x509_object;
	const char *oid = NULL;
	const char *name = NULL;

	static char *keywordlist[] = {"x509", "oid", "name", NULL};

	if (!PyArg_ParseTupleAndKeywords(args, keywords, "O|ss", keywordlist,
					 &x509_object, &oid, &name)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);
	char *value = NULL;
	size_t length;
	ASN1_OBJECT *obj = NULL;
	if (name != NULL) {
		obj = get_object_by_name(name);
	} else {
		obj = get_object_by_oid(oid);
	}

	length = get_extension_by_object(x509, obj, &value);
	if (value != NULL) {
		return PyString_FromStringAndSize(value, length);
	} else {
		Py_INCREF(Py_None);
		return Py_None;
	}
}

static PyObject *
get_all_extensions(PyObject *self, PyObject *args) {
	X509 *x509;
	PyCObject *x509_object;

	if (!PyArg_ParseTuple(args, "O", &x509_object)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);

	int i;
	int ext_count = X509_get_ext_count(x509);

	char oid[MAX_BUF];
	PyObject *dict = PyDict_New();
	for (i = 0; i < ext_count; i++) {
		X509_EXTENSION *ext = X509_get_ext(x509, i);

		OBJ_obj2txt(oid, MAX_BUF, ext->object, 1);
		PyObject *key = PyString_FromString(oid);

		char *value;
		size_t length = get_extension_by_object(x509, ext->object,
							&value);
		PyObject *dict_value = PyString_FromString(value);

		PyDict_SetItem(dict, key, dict_value);
	}

	return dict;

}
static PyObject *
get_serial_number(PyObject *self, PyObject *args) {
	X509 *x509;
	PyCObject *x509_object;

	if (!PyArg_ParseTuple(args, "O", &x509_object)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);

	ASN1_INTEGER *serial_asn = X509_get_serialNumber(x509);
	long serial = ASN1_INTEGER_get (serial_asn);

	return PyInt_FromLong(serial);
}

static PyObject *
get_subject(PyObject *self, PyObject *args) {
	X509 *x509;
	PyCObject *x509_object;

	if (!PyArg_ParseTuple(args, "O", &x509_object)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);

	X509_NAME *name = X509_get_subject_name(x509);
	int entries = X509_NAME_entry_count(name);
	int i;

	PyObject *dict = PyDict_New();
	for (i = 0; i < entries; i++) {
		X509_NAME_ENTRY *entry = X509_NAME_get_entry(name, i);
		ASN1_OBJECT *obj = X509_NAME_ENTRY_get_object(entry);
		ASN1_STRING *data = X509_NAME_ENTRY_get_data(entry);

		PyObject *key =
			PyString_FromString(OBJ_nid2sn(OBJ_obj2nid(obj)));
		PyObject *value =
			PyString_FromString(ASN1_STRING_data(data));
		PyDict_SetItem(dict, key, value);
	}

	return dict;
}

static PyObject *
time_to_string(ASN1_UTCTIME *time) {
	BIO *bio = BIO_new(BIO_s_mem());
	ASN1_UTCTIME_print(bio, time);

	size_t size = BIO_ctrl_pending(bio);
	char *buf = malloc(sizeof(char) * size);
	BIO_read(bio, buf, size);
	BIO_free(bio);

	return PyString_FromStringAndSize(buf, size);
}

static PyObject *
get_not_before(PyObject *self, PyObject *args) {
	X509 *x509;
	PyCObject *x509_object;

	if (!PyArg_ParseTuple(args, "O", &x509_object)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);

	ASN1_UTCTIME *time = X509_get_notBefore(x509);
	return time_to_string(time);

//	Py_INCREF(Py_None);
//	return Py_None;
}

static PyObject *
get_not_after(PyObject *self, PyObject *args) {
	X509 *x509;
	PyCObject *x509_object;

	if (!PyArg_ParseTuple(args, "O", &x509_object)) {
		return NULL;
	}

	x509 = PyCObject_AsVoidPtr(x509_object);

	ASN1_UTCTIME *time = X509_get_notAfter(x509);
	return time_to_string(time);

//	Py_INCREF(Py_None);
//	return Py_None;
}

static PyMethodDef cert_methods[] = {
	{"load", load_cert, METH_VARARGS | METH_KEYWORDS,
	 "load a certificate from a file"},
	{"get_serial_number", get_serial_number, METH_VARARGS,
	 "get the certificate's serial number"},
	{"get_subject", get_subject, METH_VARARGS,
	 "get the certificate's subject"},
	{"get_not_before", get_not_before, METH_VARARGS,
	 "get the certificate's start time"},
	{"get_not_after", get_not_after, METH_VARARGS,
	 "get the certificate's end time"},
	{"get_extension", get_extension, METH_VARARGS | METH_KEYWORDS,
	 "get the string representation of an extension by oid"},
	{"get_all_extensions", get_all_extensions, METH_VARARGS,
	 "get a dict of oid: value"},

	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_certificate(void) {
	Py_InitModule("_certificate", cert_methods);
}
