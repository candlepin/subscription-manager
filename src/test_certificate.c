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

#include <glib.h>
#include <gio/gio.h>

#include "certificate.h"

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

int main(int argc, char **argv) {
    Py_Initialize();
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/test_certificate/test_get_signature_algorithms", test_get_signature_algorithms);
    g_test_add_func("/test_certificate/test_get_public_key_algorithms", test_get_public_key_algorithms);
    g_test_run();
    Py_FinalizeEx();
    return 0;
}
