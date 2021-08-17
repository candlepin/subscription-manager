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

#ifndef PRODUCT_ID_PRODUCT_ID_H
#define PRODUCT_ID_PRODUCT_ID_H

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wvariadic-macros"
#include <libdnf/libdnf.h>
#include <zlib.h>
#pragma GCC diagnostic pop

#define PRODUCTDB_FILE "/var/lib/rhsm/productid.js"
#define PRODUCT_CERT_DIR "/etc/pki/product/"
#define DEFAULT_PRODUCT_CERT_DIR "/etc/pki/product-default/"

#define AVAIL_PKGS_CACHE_FILE "/var/lib/rhsm/cache/package_repo_mapping.json"

#define SUPPORTED_LIBDNF_PLUGIN_API_VERSION 1

#define CHUNK 16384
#define MAX_BUFF 256

// The Red Hat OID plus ".1" which is the product namespace
#define REDHAT_PRODUCT_OID "1.3.6.1.4.1.2312.9.1"

#include "productdb.h"

/**
 * Information about libdnf plugin
 */
static const PluginInfo pinfo = {
    .name = "Product ID - libdnf Plugin",
    .version = "1.0.0"
};

/**
 * Structure holding all data specific for this plugin
 */
typedef struct _PluginHandle {
    // Data provided by the init method
    int version;
    PluginMode mode;
    DnfContext *context;

    // Add plugin-specific "private" data here
} _PluginHandle;

/**
 * Internal structure for holding information about product-id certificate
 * in specific repository
 */
typedef struct {
    DnfRepo *repo;
    char *productIdPath;
    bool isInstalled;
} RepoProductId;

RepoProductId *initRepoProductId();
void freeRepoProductId(RepoProductId *repoProductId);
void printError(const char *msg, GError *err);
void getEnabled(const GPtrArray *repos, GPtrArray *enabledRepos);
void getDisabled(const GPtrArray *repos, GPtrArray *disabledRepos);
GPtrArray *getAvailPackageList(DnfSack *dnfSack, DnfRepo *repo);
GPtrArray *getInstalledPackages(DnfSack *rpmDbSack);
int getInstalledProductCerts(gchar *certDir, GPtrArray *repos, GPtrArray *enabledRepoProductId, ProductDb *productDb);
void getActiveReposFromInstalledPkgs(DnfContext *dnfContext, const GPtrArray *enabledRepoAndProductIds,
                                     GPtrArray *activeRepoAndProductIds, GPtrArray *installedPackages);
void getActive(DnfContext *dnfContext, const GPtrArray *enabledRepoAndProductIds,
        GPtrArray *activeRepoAndProductIds);
int decompress(gzFile input, GString *output);
int findProductId(GString *certContent, GString *result);
int fetchProductId(DnfRepo *repo, RepoProductId *repoProductId);
int installProductId(RepoProductId *repoProductId, ProductDb *productDb, const char *product_cert_dir);
void writeRepoMap(ProductDb *productDb);
void protectProductWithDisabledRepos(GPtrArray *disabledRepos, ProductDb *oldProductDb, ProductDb *productDb);

#endif //PRODUCT_ID_PRODUCT_ID_H
