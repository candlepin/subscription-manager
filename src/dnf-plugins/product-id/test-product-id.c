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

#define CORRECT_PEM_CERT "\
-----BEGIN CERTIFICATE-----\n\
MIIGEjCCA/qgAwIBAgIJALDxRLt/tWEVMA0GCSqGSIb3DQEBBQUAMIGuMQswCQYD\n\
VQQGEwJVUzEXMBUGA1UECAwOTm9ydGggQ2Fyb2xpbmExFjAUBgNVBAoMDVJlZCBI\n\
YXQsIEluYy4xGDAWBgNVBAsMD1JlZCBIYXQgTmV0d29yazEuMCwGA1UEAwwlUmVk\n\
IEhhdCBFbnRpdGxlbWVudCBQcm9kdWN0IEF1dGhvcml0eTEkMCIGCSqGSIb3DQEJ\n\
ARYVY2Etc3VwcG9ydEByZWRoYXQuY29tMB4XDTE4MDQxMzExMTk0NVoXDTM4MDQw\n\
ODExMTk0NVowRDFCMEAGA1UEAww5UmVkIEhhdCBQcm9kdWN0IElEIFsxMjYxMjAy\n\
ZS01Yjc2LTQ1MTMtOTlmMi05Mzk2NmFjZGY0MmJdMIICIjANBgkqhkiG9w0BAQEF\n\
AAOCAg8AMIICCgKCAgEAxj9J04z+Ezdyx1U33kFftLv0ntNS1BSeuhoZLDhs18yk\n\
sepG7hXXtHh2CMFfLZmTjAyL9i1XsxykQpVQdXTGpUF33C2qBQHB5glYs9+d781x\n\
8p8m8zFxbPcW82TIJXbgW3ErVh8vk5qCbG1cCAAHb+DWMq0EAyy1bl/JgAghYNGB\n\
RvKJObTdCrdpYh02KUqBLkSPZHvo6DUJFN37MXDpVeQq9VtqRjpKLLwuEfXb0Y7I\n\
5xEOrR3kYbOaBAWVt3mYZ1t0L/KfY2jVOdU5WFyyB9PhbMdLi1xE801j+GJrwcLa\n\
xmqvj4UaICRzcPATP86zVM1BBQa+lilkRQes5HyjZzZDiGYudnXhbqmLo/n0cuXo\n\
QBVVjhzRTMx71Eiiahmiw+U1vGqkHhQNxb13HtN1lcAhUCDrxxeMvrAjYdWpYlpI\n\
yW3NssPWt1YUHidMBSAJ4KctIf91dyE93aStlxwC/QnyFsZOmcEsBzVCnz9GmWMl\n\
1/6XzBS1yDUqByklx0TLH+z/sK9A+O2rZAy1mByCYwVxvbOZhnqGxAuToIS+A81v\n\
5hCjsCiOScVB+cil30YBu0cH85RZ0ILNkHdKdrLLWW4wjphK2nBn2g2i3+ztf+nQ\n\
ED2pQqZ/rhuW79jcyCZl9kXqe1wOdF0Cwah4N6/3LzIXEEKyEJxNqQwtNc2IVE8C\n\
AwEAAaOBmzCBmDAJBgNVHRMEAjAAMDAGCysGAQQBkggJAUUBBCEMH1JlZCBIYXQg\n\
RW50ZXJwcmlzZSBMaW51eCBTZXJ2ZXIwGQYLKwYBBAGSCAkBRQIECgwINy42IEJl\n\
dGEwFwYLKwYBBAGSCAkBRQMECAwGeDg2XzY0MCUGCysGAQQBkggJAUUEBBYMFHJo\n\
ZWwtNyxyaGVsLTctc2VydmVyMA0GCSqGSIb3DQEBBQUAA4ICAQBfm/EhFPJpd16p\n\
mlfi3FysnVOBdsBcoiGhHcNXsvklriWvBTauh4Aq8EsGb14bZziQ3ttEcHm/qnJd\n\
ZIocbbFIb0317ph4l5+ilIy8Zu/9cu7ZSJpdKPnDV0qOnqdxrMGpQjEK5oukSl+d\n\
2p0+qh5hKYZGOx9Jn3lBneKCQg1g8SLOE9DugWWzK5VwuZ/EhVRFl26NCX7Mr45X\n\
2WkvTVlC9vPNGD9OUDqBcdSX6hmnWXEcfqwN2/rAoYVybfA7GTauNTeglFaNytvM\n\
LfQsrBZCmHoM17q7X6+cKBcNLL2OnV5/EHTPEovqyus7In2wbW9UHopIlmkBrv0f\n\
VR1MTipcBhfTrZ9X2/aS1D0hXAE987bMPKZdnrEnXwz+FpLET/89bk2Zus5QCe6b\n\
9ZcUgOlrPcNs4sf9g0fquEvxz1ipl87EGzJOsmbj8bwR+ZPvs7igj3pZSY1hVjt8\n\
PJSnPRn8H9+KxLFLGm8vdBsVeTvXalAT1SGVC6fTzIEWzisZ8PXOYeMw/j2EC2ja\n\
vZ5sqc/+0iTLkHj2YbKy9UtJn30nQG185GWhrPm3qHovh+u1wSRLbb97oitMIoJ9\n\
8X/saMhUG2gzyz+jBETDTGsJyEvaMFXcR7ZoTJXh5z5Sj9q4wjeNC4xL0nFLya3j\n\
5IbpY9kFCqOizzZKTjgzc3sUIzECgw==\n\
-----END CERTIFICATE-----\n"

#define CORRUPTED_PEM_CERT "\
-----BEGIN CERTIFICATE-----\n\
MIIGEjCCA/qgAwIBAgIJALDxRLt/tWEVMA0GCSqGSIb3DQEBBQUAMIGuMQswCQYD\n\
-----END CERTIFICATE-----\n"

#define CONSUMER_CERT "\
-----BEGIN CERTIFICATE-----\n\
MIID3jCCAsagAwIBAgIIbPqoOJvSK6kwDQYJKoZIhvcNAQELBQAwPzEeMBwGA1UE\n\
AwwVY2FuZGxlcGluLmV4YW1wbGUuY29tMQswCQYDVQQGEwJVUzEQMA4GA1UEBwwH\n\
UmFsZWlnaDAeFw0xODEwMjkxNTE3MzFaFw0zNDEwMjkxNjE3MzFaMC8xLTArBgNV\n\
BAMMJGZjMWZkMjQ0LWQ2NTctNDYxYS05Y2Y5LTJmZWY3NWEzZjE2ZDCCASIwDQYJ\n\
KoZIhvcNAQEBBQADggEPADCCAQoCggEBALSkszwgwxOJKzVUxY3beo2p7LgTglTQ\n\
/hd7bYBfSk/1FuTpA+FKebQ6FjivwtFUMc9H9bGPesXYxNzK8fW7MClL8aJwb0Sq\n\
arABRWtBpbKK+aDlJyerhPUCOFLSS5Udg5Ma784rOgutcTtnmCzcZYQYDDpwsp3E\n\
lqZBC+DURa5rkn5ICE91/o/RqgZQl4NZMQucVUk28TAl0XiqwXhVCB+aswhB2O07\n\
7NmkcFYwfG9za26qgn4GJGHq3WrGFbMzqtF/G+td5lGhFYLpvgv/uP6i8/kA79js\n\
fSH5Hw6KUdCu/SAS+zMDqCK3l08eAXN9GQ8Bm4Y7G35jBEBmKHGMpNMCAwEAAaOB\n\
7TCB6jAOBgNVHQ8BAf8EBAMCBLAwEwYDVR0lBAwwCgYIKwYBBQUHAwIwCQYDVR0T\n\
BAIwADARBglghkgBhvhCAQEEBAMCBaAwHQYDVR0OBBYEFP6KB1M8+eO2yUT5Zynd\n\
VhWWh2psMB8GA1UdIwQYMBaAFHkScHy3YqTKDWnl00rUoqBk+mcdMGUGA1UdEQRe\n\
MFykMTAvMS0wKwYDVQQDDCRmYzFmZDI0NC1kNjU3LTQ2MWEtOWNmOS0yZmVmNzVh\n\
M2YxNmSkJzAlMSMwIQYDVQQDDBpjZW50b3M3LnN1Ym1hbi5leGFtcGxlLmNvbTAN\n\
BgkqhkiG9w0BAQsFAAOCAQEAk+k/OdSuPoDGCnSHraIyUfqd/2GaSz6aiDcuEJ5w\n\
AYj6TKzkLmBdNCPse2EJhEKRtpzjge2Z5+Oqv9JBaVUAdCUIYsiY6PUww/LGmMaK\n\
JabbKSPBPyqHE0Yr7eeEApCGdqGVvW44cOnKrjcWZlfYGigvPRtw5ozJxIv5TTyj\n\
d40Md827SPjgVzZh0pi+rVLP2tlgX6dmiuLiavyHECRCvI/1T2LumItOgGTvADzl\n\
+0HtMqvTs5yVKQf6XQMYTKeCI4JthptXCgC5jjabeUWTKUAzLiX4wNPmJJWxZt1i\n\
3HxHG05Yct/CFDJncDeHl7623QhlyzasYvVPG6/VSRnzOQ==\n\
-----END CERTIFICATE-----\n"

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

// Test reading correct certificate (default 69.pem from rhel)
void testFindProductIdInCorrectPEM(handleFixture *fixture, gconstpointer ignored) {
    (void)fixture;
    (void)ignored;
    GString *result = g_string_new("");
    int ret = findProductId(g_string_new(CORRECT_PEM_CERT), result);
    g_assert_cmpint(ret, ==, 1);
    g_assert_cmpstr(result->str, ==, "69");
    g_string_free(result, TRUE);
}

// Test reading of corrupted certificate
void testFindProductIdInCorruptedPEM(handleFixture *fixture, gconstpointer ignored) {
    (void)fixture;
    (void)ignored;
    GString *result = g_string_new("");
    int ret = findProductId(g_string_new(CORRUPTED_PEM_CERT), result);
    g_assert_cmpint(ret, ==, -1);
    g_assert_cmpstr(result->str, ==, "");
    g_string_free(result, TRUE);
}

// Test reading wrong certificate (consumer certificate not product certificate)
void testFindProductIdInConsomerPEM(handleFixture *fixture, gconstpointer ignored) {
    (void)fixture;
    (void)ignored;
    GString *result = g_string_new("");
    int ret = findProductId(g_string_new(CONSUMER_CERT), result);
    g_assert_cmpint(ret, ==, -1);
    g_assert_cmpstr(result->str, ==, "");
    g_string_free(result, TRUE);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set2/test plugin handle created", handleFixture, NULL, setup, testHandleCreated, teardown);
    g_test_add("/set2/test plugin handle not created (version)", handleFixture, NULL, setupUnsupportedApiVersion, testHandleNotCreatedVersion, teardown);
    g_test_add("/set2/test plugin handle not created (mode)", handleFixture, NULL, setupUnsupportedMode, testHandleNotCreatedMode, teardown);
    g_test_add("/set2/test unsupported hook called", handleFixture, NULL, setup, testUnsupportedHookCalled, teardown);
    g_test_add("/set2/test supported hook called", handleFixture, NULL, setup, testSupportedHookCalled, teardown);
    g_test_add("/set2/test find product ID", handleFixture, NULL, setup, testFindProductIdInCorrectPEM, teardown);
    g_test_add("/set2/test corrupeted certificate", handleFixture, NULL, setup, testFindProductIdInCorruptedPEM, teardown);
    g_test_add("/set2/test consumer certificate", handleFixture, NULL, setup, testFindProductIdInConsomerPEM, teardown);
    return g_test_run();
}