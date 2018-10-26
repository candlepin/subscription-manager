/**
 * Copyright (c) 2018 Red Hat, Inc.
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

#include <glib.h>
#include <stdio.h>
#include <gio/gio.h>
#include <string.h>

#include "product-id.h"

typedef struct {
    _PluginHandle *handle;
    DnfContext *dnfContext;
} handleFixture;

void setup(handleFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->dnfContext = dnf_context_new();
    PluginMode mode = PLUGIN_MODE_CONTEXT;
    // This is never explicitly called
    fixture->handle = pluginInitHandle(1, mode, (void*)fixture->dnfContext);
}

void teardown(handleFixture *fixture, gconstpointer testData) {
    (void)testData;
    pluginFreeHandle(fixture->handle);
}

void testHandleCreated(handleFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    g_assert_nonnull(fixture->dnfContext);
    g_assert_nonnull(fixture->handle);
    g_assert_cmpint(fixture->handle->version, ==, 1);
    g_assert_cmpint(fixture->handle->mode, ==, PLUGIN_MODE_CONTEXT);
}

void setupUnsupportedApiVersion(handleFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->dnfContext = dnf_context_new();
    PluginMode mode = PLUGIN_MODE_CONTEXT;
    // This is never explicitly called (This plugin version should not be supported)
    fixture->handle = pluginInitHandle(10000, mode, (void*)fixture->dnfContext);
}

void testHandleNotCreatedVersion(handleFixture *fixture, gconstpointer ignored) {
    // This test has to be run with setupUnsupportedApiVersion
    (void)ignored;
    g_assert_null(fixture->handle);
}

void setupUnsupportedMode(handleFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->dnfContext = dnf_context_new();
    PluginMode mode = 0;
    // This is never explicitly called (This plugin mode should not be supported)
    fixture->handle = pluginInitHandle(1, mode, (void*)fixture->dnfContext);
}

void testHandleNotCreatedMode(handleFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    g_assert_null(fixture->handle);
}

void testUnsupportedHookCalled(handleFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    // We do nothing when this hook is called
    int ret_val = pluginHook(fixture->handle, PLUGIN_HOOK_ID_CONTEXT_PRE_CONF, NULL, NULL);
    // But return value still should be 1
    g_assert_cmpint(ret_val, ==, 1);
}

void testSupportedHookCalled(handleFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    int ret_val = pluginHook(fixture->handle, PLUGIN_HOOK_ID_CONTEXT_TRANSACTION, NULL, NULL);
    g_assert_cmpint(ret_val, ==, 1);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set2/test handle created", handleFixture, NULL, setup, testHandleCreated, teardown);
    g_test_add("/set2/test handle not created (version)", handleFixture, NULL, setupUnsupportedApiVersion, testHandleNotCreatedVersion, teardown);
    g_test_add("/set2/test handle not created (mode)", handleFixture, NULL, setupUnsupportedMode, testHandleNotCreatedMode, teardown);
    g_test_add("/set2/test unsupported hook called", handleFixture, NULL, setup, testUnsupportedHookCalled, teardown);
    g_test_add("/set2/test supported hook called", handleFixture, NULL, setup, testSupportedHookCalled, teardown);
    return g_test_run();
}