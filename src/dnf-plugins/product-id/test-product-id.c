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
    g_object_unref(fixture->dnfContext);
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
    GString *certContent = g_string_new(CORRECT_PEM_CERT);
    int ret = findProductId(certContent, result);
    g_assert_cmpint(ret, ==, 1);
    g_assert_cmpstr(result->str, ==, "69");
    g_string_free(certContent, TRUE);
    g_string_free(result, TRUE);
}

// Test reading of corrupted certificate
void testFindProductIdInCorruptedPEM(handleFixture *fixture, gconstpointer ignored) {
    (void)fixture;
    (void)ignored;
    GString *result = g_string_new("");
    GString *certContent = g_string_new(CORRUPTED_PEM_CERT);
    int ret = findProductId(certContent, result);
    g_assert_cmpint(ret, ==, -1);
    g_assert_cmpstr(result->str, ==, "");
    g_string_free(certContent, TRUE);
    g_string_free(result, TRUE);
}

// Test reading wrong certificate (consumer certificate not product certificate)
void testFindProductIdInConsumerPEM(handleFixture *fixture, gconstpointer ignored) {
    (void)fixture;
    (void)ignored;
    GString *result = g_string_new("");
    GString *certContent = g_string_new(CONSUMER_CERT);
    int ret = findProductId(certContent, result);
    g_assert_cmpint(ret, ==, -1);
    g_assert_cmpstr(result->str, ==, "");
    g_string_free(certContent, TRUE);
    g_string_free(result, TRUE);
}

typedef struct {
    RepoProductId *repoProductId;
    ProductDb *productDb;
} productFixture;

void setupProduct(productFixture *fixture, gconstpointer testData) {
    (void)testData;

    fixture->productDb = initProductDb();
    fixture->repoProductId = initRepoProductId();
}

void teardownProduct(productFixture *fixture, gconstpointer testData) {
    (void)testData;

    freeProductDb(fixture->productDb);
    freeRepoProductId(fixture->repoProductId);
}

void testProductNullPointers(productFixture *fixture, gconstpointer testData) {
    (void)fixture;
    (void)testData;
    int ret = installProductId(NULL, NULL, "/tmp");
    g_assert_cmpint(ret, ==, 0);
}

void testWrongPathToCompressedProductCert(productFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->repoProductId->productIdPath = g_strdup("/path/to/non-existing-compressed-cert.gz");
    int ret = installProductId(fixture->repoProductId, fixture->productDb, "/tmp");
    g_assert_cmpint(ret, ==, 0);
}

void testCorruptedCompressedProductCert(productFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->repoProductId->productIdPath = g_strdup("./test_data/corrupted_compressed_productid.pem.gz");
    int ret = installProductId(fixture->repoProductId, fixture->productDb, "/tmp");
    g_assert_cmpint(ret, ==, 0);
}

void testInstallingCompressedProductCert(productFixture *fixture, gconstpointer testData) {
    (void) testData;
    // Set path to correct productid certificate
    fixture->repoProductId->productIdPath = g_strdup("./test_data/59803427316a729fb1d67fd08e7d0c8ccd2a4a5377729b747b76345851bdba6c-productid.gz");
    // Create dummy repository
    DnfContext *dnfContext = dnf_context_new();
    fixture->repoProductId->repo = dnf_repo_new(dnfContext);
    int ret = installProductId(fixture->repoProductId, fixture->productDb, "./");
    g_object_unref(fixture->repoProductId->repo);
    g_object_unref(dnfContext);
    g_assert_cmpint(ret, == , 1);
}

void testFetchingProductId(productFixture *fixture, gconstpointer testData) {
    (void) testData;
    // Create dummy repository
    DnfContext *dnfContext = dnf_context_new();
    DnfRepo *repo = dnf_repo_new(dnfContext);

    int ret = fetchProductId(repo, fixture->repoProductId);
    printf("result of fetchProductId: %d\n", ret);
    g_assert_cmpint(ret, ==, 0);

    g_object_unref(repo);
    g_object_unref(dnfContext);
}

typedef struct {
    DnfContext *dnfContext;
    GPtrArray *repos;
    GPtrArray *enabledRepos;
    DnfRepo* repo1;
    DnfRepo* repo2;
    DnfRepo* repo3;
} enabledReposFixture;

void setupEnabledRepos(enabledReposFixture *fixture, gconstpointer testData) {
    (void)testData;
    // Create testing array of testing repositories
    fixture->dnfContext = dnf_context_new();
    fixture->repos = g_ptr_array_sized_new(3);
    // 1st
    fixture->repo1 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_enabled(fixture->repo1, TRUE);
    g_ptr_array_add(fixture->repos, fixture->repo1);
    // 2nd
    fixture->repo2 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_enabled(fixture->repo2, TRUE);
    g_ptr_array_add(fixture->repos, fixture->repo2);
    // 3th
    fixture->repo3 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_enabled(fixture->repo3, FALSE);
    g_ptr_array_add(fixture->repos, fixture->repo3);
    // Create array for storing enabled repositories
    fixture->enabledRepos = g_ptr_array_sized_new(3);
}

void teardownEnabledRepos(enabledReposFixture *fixture, gconstpointer testData) {
    g_object_unref(fixture->repo1);
    g_object_unref(fixture->repo2);
    g_object_unref(fixture->repo3);
    g_ptr_array_unref(fixture->repos);
    g_ptr_array_unref(fixture->enabledRepos);
    g_object_unref(fixture->dnfContext);
    (void)testData;
}

void testGetEnabledRepos(enabledReposFixture *fixture, gconstpointer testData) {
    (void)testData;
    getEnabled(fixture->repos, fixture->enabledRepos);
    g_assert_cmpint(fixture->enabledRepos->len, ==, 2);
}

typedef struct {
    DnfContext *dnfContext;
    GPtrArray *repoAndProductIds;
    GPtrArray *activeRepoAndProductIds;
    RepoProductId *repoProductId1;
    RepoProductId *repoProductId2;
    RepoProductId *repoProductId3;
} activeReposFixture;

void setupActiveRepos(activeReposFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->dnfContext = dnf_context_new();
    int max_size = 3;
    fixture->repoAndProductIds = g_ptr_array_sized_new(max_size);
    fixture->repoProductId1 = initRepoProductId();
    fixture->repoProductId1->repo = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_enabled(fixture->repoProductId1->repo, TRUE);
    fixture->repoProductId2 = initRepoProductId();
    fixture->repoProductId2->repo = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_enabled(fixture->repoProductId2->repo, TRUE);
    fixture->repoProductId3 = initRepoProductId();
    fixture->repoProductId3->repo = dnf_repo_new(fixture->dnfContext);
    fixture->activeRepoAndProductIds = g_ptr_array_sized_new(max_size);
}

void teardownActiveRepos(activeReposFixture *fixture, gconstpointer testData) {
    (void)testData;
    g_object_unref(fixture->repoProductId1->repo);
    freeRepoProductId(fixture->repoProductId1);
    g_object_unref(fixture->repoProductId2->repo);
    freeRepoProductId(fixture->repoProductId2);
    g_object_unref(fixture->repoProductId3->repo);
    freeRepoProductId(fixture->repoProductId3);
    g_ptr_array_unref(fixture->repoAndProductIds);
    g_ptr_array_unref(fixture->activeRepoAndProductIds);
    g_object_unref(fixture->dnfContext);
}

void testGetActiveRepos(activeReposFixture *fixture, gconstpointer testData) {
    (void)testData;
    getActive(fixture->dnfContext, fixture->repoAndProductIds, fixture->activeRepoAndProductIds);
    // TODO: improve this unit test to get at least one active repository
    g_assert_cmpint(fixture->activeRepoAndProductIds->len, ==, 0);
}

typedef struct {
    DnfSack *rpmDbSack;
} installedPackageFixture;

void setupInstalledPackages(installedPackageFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->rpmDbSack = dnf_sack_new();
}

void teardownInstalledPackages(installedPackageFixture *fixture, gconstpointer testData) {
    (void)testData;
    g_object_unref(fixture->rpmDbSack);
}

void testInstalledPackages(installedPackageFixture *fixture, gconstpointer testData) {
    (void)testData;
    // Note: it is probably not possible to mock functions used in getInstalledPackages
    // for quering. Thus this method return list of packages installed in current system
    GPtrArray *installedPackages = getInstalledPackages(fixture->rpmDbSack);
    // We expect that the length of the list will be bigger than zero :-)
    g_assert_cmpint(installedPackages->len, >, 0);
    g_ptr_array_unref(installedPackages);
}

typedef struct {
    ProductDb *oldProductDb;
    GPtrArray *disabledRepos;
    DnfRepo *repo;
    DnfContext *dnfContext;
} protectedProductFixture;

void setupProtectedProduct(protectedProductFixture *fixture, gconstpointer testData) {
    (void) testData;
    // Set up fake existing dabatase with product-ids and repos
    fixture->oldProductDb = initProductDb();
    fixture->oldProductDb->path = "/path/to/testing.json";
    addRepoId(fixture->oldProductDb, "69", "rhel");
    addRepoId(fixture->oldProductDb, "69", "rhel-testing");
    addRepoId(fixture->oldProductDb, "71", "jboss");
    // Set up fake list of disabled repos
    fixture->disabledRepos = g_ptr_array_sized_new(1);
    fixture->dnfContext = dnf_context_new();
    fixture->repo = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_id(fixture->repo, "jboss");
    g_ptr_array_add(fixture->disabledRepos, fixture->repo);
}

void teardownProtectedProduct(protectedProductFixture *fixture, gconstpointer testData) {
    (void)testData;
    g_ptr_array_unref(fixture->disabledRepos);
    freeProductDb(fixture->oldProductDb);
    g_object_unref(fixture->repo);
    g_object_unref(fixture->dnfContext);
}

void testProtectedProduct(protectedProductFixture *fixture, gconstpointer testData) {
    (void)testData;
    ProductDb *productDb = initProductDb();
    productDb->path = "/path/to/testing.json";
    protectProductWithDisabledRepos(fixture->disabledRepos, fixture->oldProductDb, productDb);
    gpointer repoIdList = g_hash_table_lookup(productDb->repoMap, "71");
    guint listLength = g_slist_length((GSList *) repoIdList);
    g_assert_cmpint(1, ==, listLength);
    freeProductDb(productDb);
}

typedef struct {
    GPtrArray *repos;
    GPtrArray *enabledRepoProductId;
    ProductDb *productDb;
    DnfContext *dnfContext;
} installedProductCertsFixture;

void setupInstalledProduct(installedProductCertsFixture *fixture, gconstpointer testData) {
    (void) testData;
    fixture->dnfContext = dnf_context_new();

    fixture->repos = g_ptr_array_sized_new(2);
    // First repo
    DnfRepo *repo1 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_id(repo1, "rhel");
    g_ptr_array_add(fixture->repos, repo1);
    // Second repo
    DnfRepo *repo2 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_id(repo2, "rhel-testing");
    g_ptr_array_add(fixture->repos, repo2);

    fixture->enabledRepoProductId = g_ptr_array_sized_new(2);

    fixture->productDb = initProductDb();
    addRepoId(fixture->productDb, "71", "rhel");
    addRepoId(fixture->productDb, "71", "rhel-testing");
}

void teardownInstalledProduct(installedProductCertsFixture *fixture, gconstpointer testData) {
    (void)testData;

    freeProductDb(fixture->productDb);
    for (guint i = 0; i < fixture->repos->len; i++) {
        DnfRepo *repo = g_ptr_array_index(fixture->repos, i);
        g_object_unref(repo);
    }
    g_ptr_array_unref(fixture->repos);
    for (guint i = 0; i < fixture->enabledRepoProductId->len; i++) {
        RepoProductId *repoProductId = g_ptr_array_index(fixture->enabledRepoProductId, i);
        freeRepoProductId(repoProductId);
    }
    g_ptr_array_unref(fixture->enabledRepoProductId);
    g_object_unref(fixture->dnfContext);
}

void testInstalledProduct(installedProductCertsFixture *fixture, gconstpointer testData) {
    (void)testData;

    int ret = getInstalledProductCerts("./test_data/cert_dir/", fixture->repos, fixture->enabledRepoProductId, fixture->productDb);
    g_assert_cmpint(1, ==, ret);
}

typedef struct {
    DnfContext *dnfContext;
    DnfSack *rpmDbSack;
    GPtrArray *repos;
    GPtrArray *enabledRepoAndProductIds;
    GPtrArray *activeRepoAndProductIds;
    GPtrArray *installedPackages;
} packageRepoFixture;

void setupPackageRepo(packageRepoFixture *fixture, gconstpointer testData) {
    (void) testData;
    fixture->dnfContext = dnf_context_new();
    fixture->repos = g_ptr_array_sized_new(2);
    // First repo
    DnfRepo *repo1 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_id(repo1, "foo-bar");
    g_ptr_array_add(fixture->repos, repo1);
    // Second repo
    DnfRepo *repo2 = dnf_repo_new(fixture->dnfContext);
    dnf_repo_set_id(repo2, "foo-bar-testing");
    g_ptr_array_add(fixture->repos, repo2);
    fixture->enabledRepoAndProductIds = g_ptr_array_sized_new(fixture->repos->len);
    fixture->activeRepoAndProductIds = g_ptr_array_sized_new(fixture->repos->len);
    fixture->rpmDbSack = dnf_sack_new();
    fixture->installedPackages = getInstalledPackages(fixture->rpmDbSack);
}

void teardownPackageRepo(packageRepoFixture *fixture, gconstpointer testData) {
    (void)testData;
    for (guint i = 0; i < fixture->repos->len; i++) {
        DnfRepo *repo = g_ptr_array_index(fixture->repos, i);
        g_object_unref(repo);
    }
    g_ptr_array_unref(fixture->repos);
    for (guint i = 0; i < fixture->enabledRepoAndProductIds->len; i++) {
        RepoProductId *repoProductId = g_ptr_array_index(fixture->enabledRepoAndProductIds, i);
        freeRepoProductId(repoProductId);
    }
    g_ptr_array_unref(fixture->enabledRepoAndProductIds);
    for (guint i = 0; i < fixture->activeRepoAndProductIds->len; i++) {
        RepoProductId *repoProductId = g_ptr_array_index(fixture->activeRepoAndProductIds, i);
        freeRepoProductId(repoProductId);
    }
    g_ptr_array_unref(fixture->activeRepoAndProductIds);
    g_object_unref(fixture->dnfContext);
    g_object_unref(fixture->rpmDbSack);
}

void testPackageRepo(packageRepoFixture *fixture, gconstpointer testData) {
    (void)testData;

    getActiveReposFromInstalledPkgs(fixture->dnfContext, fixture->enabledRepoAndProductIds,
                                         fixture->activeRepoAndProductIds, fixture->installedPackages);
    g_assert_cmpint(0, ==, fixture->activeRepoAndProductIds->len);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set2/test plugin handle created", handleFixture, NULL, setup, testHandleCreated, teardown);
    g_test_add("/set2/test plugin handle not created (version)", handleFixture, NULL, setupUnsupportedApiVersion, testHandleNotCreatedVersion, teardown);
    g_test_add("/set2/test plugin handle not created (mode)", handleFixture, NULL, setupUnsupportedMode, testHandleNotCreatedMode, teardown);
    g_test_add("/set2/test unsupported hook called", handleFixture, NULL, setup, testUnsupportedHookCalled, teardown);
    g_test_add("/set2/test supported hook called", handleFixture, NULL, setup, testSupportedHookCalled, teardown);
    g_test_add("/set2/test find product ID", handleFixture, NULL, setup, testFindProductIdInCorrectPEM, teardown);
    g_test_add("/set2/test corrupted certificate", handleFixture, NULL, setup, testFindProductIdInCorruptedPEM, teardown);
    g_test_add("/set2/test consumer certificate", handleFixture, NULL, setup, testFindProductIdInConsumerPEM, teardown);
    g_test_add("/set2/test installProductId null pointers", productFixture, NULL, setupProduct, testProductNullPointers, teardownProduct);
    g_test_add("/set2/test invalid repoProductId", productFixture, NULL, setupProduct, testWrongPathToCompressedProductCert, teardownProduct);
    g_test_add("/set2/test corrupted compressed productid cert", productFixture, NULL, setupProduct, testCorruptedCompressedProductCert, teardownProduct);
    g_test_add("/set2/test installing product-id cert", productFixture, NULL, setupProduct, testInstallingCompressedProductCert, teardownProduct);
    g_test_add("/set2/test fetching of product-id cert", productFixture, NULL, setupProduct, testFetchingProductId, teardownProduct);
    g_test_add("/set2/test getting enabled repos", enabledReposFixture, NULL, setupEnabledRepos, testGetEnabledRepos, teardownEnabledRepos);
    g_test_add("/set2/test getting active repos", activeReposFixture, NULL, setupActiveRepos, testGetActiveRepos, teardownActiveRepos);
    g_test_add("/set2/test installed packages", installedPackageFixture, NULL, setupInstalledPackages, testInstalledPackages, teardownInstalledPackages);
    g_test_add("/set2/test protect disabled repos", protectedProductFixture, NULL, setupProtectedProduct, testProtectedProduct, teardownProtectedProduct);
    g_test_add("/set2/test installed product cert", installedProductCertsFixture, NULL, setupInstalledProduct, testInstalledProduct, teardownInstalledProduct);
    g_test_add("/set2/test package with repo id", packageRepoFixture, NULL, setupPackageRepo, testPackageRepo, teardownPackageRepo);
    return g_test_run();
}
