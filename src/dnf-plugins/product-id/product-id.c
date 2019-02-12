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
#include <libdnf/plugin/plugin.h>

#include <glib/gstdio.h>

#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/err.h>

#include <json-c/json.h>

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <errno.h>

#include "util.h"
#include "product-id.h"

const PluginInfo *pluginGetInfo() {
    return &pinfo;
}

/**
 * Initialize handle of this plugin
 * @param version
 * @param mode
 * @param initData
 * @return
 */
PluginHandle *pluginInitHandle(int version, PluginMode mode, DnfPluginInitData *initData) {
    debug("%s initializing handle!", pinfo.name);

    if (version != SUPPORTED_LIBDNF_PLUGIN_API_VERSION) {
        error("Unsupported version of libdnf plugin API: %d", version);
        return NULL;
    }

    if (mode != PLUGIN_MODE_CONTEXT) {
        error("Unsupported mode of libdnf plugin: %d", (int)mode);
        return NULL;
    }

    PluginHandle* handle = malloc(sizeof(PluginHandle));

    if (handle) {
        handle->version = version;
        handle->mode = mode;
        handle->context = pluginGetContext(initData);
    }

    return handle;
}

/**
 * Free handle and all other private date of handle
 * @param handle
 */
void pluginFreeHandle(PluginHandle *handle) {
    debug("%s freeing handle!", pinfo.name);

    if (handle) {
        free(handle);
    }
}

/**
 * This function tries to remove unused product certificates.
 *
 * @param productDb
 * @return
 */
int removeUnusedProductCerts(ProductDb *productDb) {
    // "Open" directory with product certificates
    GError *tmp_err = NULL;
    GDir* productDir = g_dir_open(PRODUCT_CERT_DIR, 0, &tmp_err);
    if (productDir != NULL) {
        const gchar *file_name = NULL;
        do {
            // Read all files in the directory. When file_name is NULL, then
            // it usually means that there is no more file.
            file_name = g_dir_read_name(productDir);
            if(file_name != NULL) {
                if(g_str_has_suffix(file_name, ".pem") == TRUE) {
                    gchar *product_id = g_strndup(file_name, strlen(file_name) - 4);
                    gboolean is_num = TRUE;
                    // Test if string represents number
                    for(size_t i=0; i<strlen(product_id); i++) {
                        if (g_ascii_isdigit(product_id[i]) != TRUE) {
                            is_num = FALSE;
                            break;
                        }
                    }
                    if (is_num != TRUE) {
                        debug("Name of product certificate is wrong (not digits only): %s. Skipping.", file_name);
                    }
                    // When product certificate is not in the hash table of active repositories
                    // then it is IMHO possible to remove this product certificate
                    else if (!hasProductId(productDb, product_id)) {
                        gchar *abs_file_name = g_strconcat(PRODUCT_CERT_DIR, file_name, NULL);
                        info("Removing product certificate: %s", abs_file_name);
                        int ret = g_remove(abs_file_name);
                        if (ret == -1) {
                            error("Unable to remove product certificate: %s", abs_file_name);
                        }
                        g_free(abs_file_name);
                    }
                    g_free(product_id);
                }
            } else if (errno != 0 && errno != ENODATA && errno != EEXIST) {
                error("Unable to read content of %s directory, %d, %s", PRODUCT_CERT_DIR, errno, strerror(errno));
            }
        } while (file_name != NULL);
        g_dir_close(productDir);
    } else {
        printError("Unable to open directory with product certificates", tmp_err);
    }
    return 0;
}

/**
 * Returns string representation of pluginHookdId. There is no need to free string, because it is statically
 * allocated.
 *
 * @param id Id of plugin hook
 * @return String representing hook
 */
gchar *strHookId(PluginHookId id) {
    switch(id) {
        case PLUGIN_HOOK_ID_CONTEXT_PRE_CONF:
            return "CONTEXT_PRE_CONF";
        case PLUGIN_HOOK_ID_CONTEXT_CONF:
            return "CONTEXT_CONF";
        case PLUGIN_HOOK_ID_CONTEXT_PRE_TRANSACTION:
            return "PRE_TRANSACTION";
        case PLUGIN_HOOK_ID_CONTEXT_TRANSACTION:
            return "CONTEXT_TRANSACTION";
        case PLUGIN_HOOK_ID_CONTEXT_PRE_REPOS_RELOAD:
            return "CONTEXT_PRE_REPOS_RELOAD";
        default:
            return "UNKNOWN";
    }
}

RepoProductId *initRepoProductId() {
    RepoProductId *repoProductId = (RepoProductId*) malloc(sizeof(RepoProductId));
    repoProductId->repo = NULL;
    repoProductId->productIdPath = NULL;
    return repoProductId;
}

void freeRepoProductId(RepoProductId *repoProductId) {
    free(repoProductId);
}

/**
 * This function tries to protect product certificates
 * @param repos Array of repositories.
 * @param productDb Pointer at ProductDb struct.
 */
void protectProductWithDisabledRepos(GPtrArray *disabledRepos, ProductDb *oldProductDb, ProductDb *productDb) {

    // Try to find active, but disabled repositories
    for (guint i = 0; i < disabledRepos->len; i++) {
        DnfRepo *repo = g_ptr_array_index(disabledRepos, i);
        debug("Disabled: %s", dnf_repo_get_id(repo));
        GHashTableIter iter;
        gpointer key, value;

        g_hash_table_iter_init (&iter, oldProductDb->repoMap);
        while (g_hash_table_iter_next (&iter, &key, &value)) {
            GSList *iterator = NULL;
            for (iterator = value; iterator; iterator = iterator->next) {
                if (g_strcmp0((char *)iterator->data, dnf_repo_get_id(repo)) == 0) {
                    debug("Protecting disabled repository: %s", (char *)iterator->data);
                    // When repository has been added to the product database in the past
                    // and it is disabled now, then keep it in database
                    addRepoId(productDb, key, dnf_repo_get_id(repo));
                }
            }
        }
    }
}

/**
 * Try to request productid metadata from all enabled repositories
 *
 * @param dnfContext Pointer on dnf context
 */
void requestProductIdMetadata(DnfContext *dnfContext) {
    debug("Requesting additional product id metadata from all repositories");

    // List of all repositories
    GPtrArray *repos = dnf_context_get_repos(dnfContext);

    for (guint i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        bool enabled = (dnf_repo_get_enabled(repo) & DNF_REPO_ENABLED_PACKAGES) > 0;
        if (enabled) {
            debug("Requesting downloading productid cert from repo: %s", dnf_repo_get_id(repo));
            dnf_repo_add_metadata_type_to_download(repo, "productid");
        }
    }
}

/**
 * Callback function. This method is executed for every libdnf hook. This callback
 * is called several times during transaction, but we are interested only in one situation.
 *
 * @param handle Pointer on structure with data specific for this plugin
 * @param id Id of hook (moment of transaction, when this callback is called)
 * @param hookData
 * @param error
 * @return
 */
int pluginHook(PluginHandle *handle, PluginHookId id, DnfPluginHookData *hookData, DnfPluginError *error) {
    // We do not need this for anything
    (void)error;

    if (!handle) {
        // We must have failed to allocate our handle during init; don't do anything.
        return 0;
    }

    debug("%s v%s, running hook_id: %s on DNF version %d",
            pinfo.name, pinfo.version, strHookId(id), handle->version);


    if (id == PLUGIN_HOOK_ID_CONTEXT_CONF) {
        // Get DNF context
        DnfContext *dnfContext = handle->context;
        if (dnfContext == NULL) {
            error("Unable to get dnf context");
            return 1;
        }

        requestProductIdMetadata(dnfContext);
    }


    if (id == PLUGIN_HOOK_ID_CONTEXT_TRANSACTION) {
        // Get DNF context
        DnfContext *dnfContext = handle->context;
        if (dnfContext == NULL) {
            error("Unable to get dnf context");
            return 1;
        }

        // Directory with productdb has to exist or plugin has to be able to create it.
        gint ret_val = g_mkdir_with_parents(PRODUCTDB_DIR, 0750);
        if (ret_val != 0) {
            error("Unable to create %s directory, %s", PRODUCTDB_DIR, strerror(errno));
            return 1;
        }

        // List of all repositories
        GPtrArray *repos = dnf_context_get_repos(dnfContext);
        // When there are no repositories, then we can't do anything
        if(repos == NULL) {
            info("No repositories. Nothing to do.");
            return 1;
        }

        // List of enabled repositories
        GPtrArray *enabledRepos = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with product id certificate
        GPtrArray *repoAndProductIds = g_ptr_array_sized_new(repos->len);
        // List of disabled repositories
        GPtrArray *disabledRepos = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with prouctid cert that are actively used
        GPtrArray *activeRepoAndProductIds = g_ptr_array_sized_new(repos->len);

        ProductDb *productDb = initProductDb();
        productDb->path = PRODUCTDB_FILE;
        // TODO: read product DB here, when cache-only mode is supported

        getEnabled(repos, enabledRepos);

        // Read existing db of product certificates and repositories
        ProductDb *oldProductDb = initProductDb();
        oldProductDb->path = PRODUCTDB_FILE;
        GError *err = NULL;
        readProductDb(oldProductDb, &err);
        if(err != NULL) {
            printError("Unable to read producDB", err);
        } else {
            debug("Old productDb: %s", productDbToString(oldProductDb));
            getDisabled(repos, disabledRepos);
            protectProductWithDisabledRepos(disabledRepos, oldProductDb, productDb);
        }

        for (guint i = 0; i < enabledRepos->len; i++) {
            DnfRepo *repo = g_ptr_array_index(enabledRepos, i);
            LrResult *lrResult = dnf_repo_get_lr_result(repo);
            LrYumRepoMd *repoMd = NULL;
            GError *tmp_err = NULL;

            debug("Enabled: %s", dnf_repo_get_id(repo));
            lr_result_getinfo(lrResult, &tmp_err, LRR_YUM_REPOMD, &repoMd);
            if (tmp_err) {
                printError("Unable to get information about repository", tmp_err);
            } else if (repoMd != NULL) {
                RepoProductId *repoProductId = initRepoProductId();
                int fetchSuccess = isProductIdDownloaded(repo, repoProductId);
                if (fetchSuccess) {
                    debug("Repository %s has a productid", dnf_repo_get_id(repo));
                    g_ptr_array_add(repoAndProductIds, repoProductId);
                } else {
                    free(repoProductId);
                }
            } else {
                error("Unable to get valid information about repository");
            }
        }

        getActive(hookData, repoAndProductIds, activeRepoAndProductIds);

        for (guint i = 0; i < activeRepoAndProductIds->len; i++) {
            RepoProductId *activeRepoProductId = g_ptr_array_index(activeRepoAndProductIds, i);
            debug("Handling active repo %s\n", dnf_repo_get_id(activeRepoProductId->repo));
            installProductId(activeRepoProductId, productDb, PRODUCT_CERT_DIR);
        }

        // Handle removals here
        removeUnusedProductCerts(productDb);

        // RepoMap is now a GHashTable with each product ID mapping to a GList of the repoId's associated
        // with that product.
        writeRepoMap(productDb);

        // We have to free memory allocated for all items of repoAndProductIds. This should also handle
        // activeRepoAndProductIds since the pointers in that array are pointing to the same underlying
        // values at repoAndProductIds.
        for (guint i=0; i < repoAndProductIds->len; i++) {
            RepoProductId *repoProductId = g_ptr_array_index(repoAndProductIds, i);
            free(repoProductId);
        }

        freeProductDb(oldProductDb);
        freeProductDb(productDb);
        g_ptr_array_unref(enabledRepos);
        g_ptr_array_unref(disabledRepos);
        g_ptr_array_unref(repoAndProductIds);
        g_ptr_array_unref(activeRepoAndProductIds);
    }

    return 1;
}

void writeRepoMap(ProductDb *productDb) {
    GError *err = NULL;
    writeProductDb(productDb, &err);

    if (err) {
        error("Unable to write productdb to file: %s", PRODUCTDB_FILE);
    }
}

/**
 * Find the list of repos that are actually enabled
 * @param repos all available repos
 * @param enabledRepos the list of enabled repos
 */
void getEnabled(const GPtrArray *repos, GPtrArray *enabledRepos) {
    for (guint i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        bool enabled = (dnf_repo_get_enabled(repo) & DNF_REPO_ENABLED_PACKAGES) > 0;
        if (enabled) {
            g_ptr_array_add(enabledRepos, repo);
        }
    }
}

/**
 * Find the list of repos that are actually disabled
 * @param repos all available repos
 * @param disabledRepos the list of disabled repos
 */
void getDisabled(const GPtrArray *repos, GPtrArray *disabledRepos) {
    for (guint i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        bool enabled = (dnf_repo_get_enabled(repo) & DNF_REPO_ENABLED_PACKAGES) > 0;
        if (!enabled) {
            g_ptr_array_add(disabledRepos, repo);
        }
    }
}

/**
 * This function tries to get array of installed packages
 * @return New array of installed packages
 */
GPtrArray *getInstalledPackages(DnfSack *rpmDbSack) {
    if(rpmDbSack == NULL) {
        return NULL;
    }

    GError *tmp_err = NULL;
    gboolean ret;
    ret = dnf_sack_setup(rpmDbSack, 0, &tmp_err);
    if (ret == FALSE) {
        printError("Unable to setup new sack object", tmp_err);
        return NULL;
    }

    ret = dnf_sack_load_system_repo(rpmDbSack, NULL, 0, &tmp_err);
    if (ret == FALSE) {
        printError("Unable to load system repo to sack object", tmp_err);
        return NULL;
    }

    // Get list of installed packages
    HyQuery query = hy_query_create_flags(rpmDbSack, 0);
    hy_query_filter(query, HY_REPO_NAME, HY_EQ, HY_SYSTEM_REPO_NAME);
    GPtrArray *installedPackages = hy_query_run(query);
    hy_query_free(query);

    return installedPackages;
}

/**
 * Get list of available package for given repository
 *
 * @param dnfSack pointer at dnf sack
 * @param repo poiner at dnf repository
 * @return array of available packages in given repository
 */
GPtrArray *getAvailPackageList(DnfSack *dnfSack, DnfRepo *repo) {
    if (dnfSack == NULL || repo == NULL) {
        return NULL;
    }
    HyQuery availQuery = hy_query_create_flags(dnfSack, 0);
    hy_query_filter(availQuery, HY_PKG_REPONAME, HY_EQ, dnf_repo_get_id(repo));
    GPtrArray *availPackageList = hy_query_run(availQuery);
    hy_query_free(availQuery);
    return availPackageList;
}

/**
 * Try to find at least one installed package in the list of available packages.
 *
 * @param installedPackages pointer at array of installed packages
 * @param availPackageList pointer at array of available packages
 * @return Return TRUE, when at least one installed package is included in the list of available packages.
 */
gboolean isAvailPackageInInstalledPackages(GPtrArray *installedPackages, GPtrArray *availPackageList) {
    if (installedPackages == NULL || availPackageList == NULL) {
        return FALSE;
    }

    // NB: Another way to do this would be with a bloom filter. A bloom filter can give a very quick,
    // accurate answer to the question "Is this item not in this set of things?" if the result is
    // negative. A positive result is probabilistic and requires a second full scan of the set to get the
    // ultimate answer. The bloom filter approach would eliminate the need for the O(n^2) nested for-loop
    // solution we have.

    // Go through all available packages from repository
    for (guint j = 0; j < availPackageList->len; j++) {
        DnfPackage *pkg = g_ptr_array_index(availPackageList, j);

        // Try to find if this available package is in the list of installed packages
        for(guint k = 0; k < installedPackages->len; k++) {
            DnfPackage *instPkg = g_ptr_array_index(installedPackages, k);
            if(g_strcmp0(dnf_package_get_nevra(pkg), dnf_package_get_nevra(instPkg)) == 0) {
                return TRUE;
            }
        }
    }

    return FALSE;
}

/**
 * Find the list of repos that provide packages that are actually installed.
 * @param repos all available repos
 * @param activeRepoAndProductIds the list of repos providing active
 */
void getActive(DnfPluginHookData *hookData, const GPtrArray *repoAndProductIds, GPtrArray *activeRepoAndProductIds) {
    if (hookData == NULL) {
        return;
    }

    HyGoal goal = hookContextTransactionGetGoal(hookData);
    if (goal == NULL) {
        error("Unable to get transaction goal");
        return;
    }

    DnfSack *dnfSack = hy_goal_get_sack(goal);
    if (dnfSack == NULL) {
        error("Unable to get dnf sack from dnf context");
        return;
    }

    // Create special sack object only for quering current rpmdb to get fresh list
    // of installed packages. Quering dnfSack would not include just installed RPM
    // package(s) or it would still include just removed package(s).
    DnfSack *rpmDbSack = dnf_sack_new();
    if (rpmDbSack == NULL) {
        error("Unable to create new sack object for quering rpmdb");
        return;
    }

    // Get list of all packages installed in the system
    GPtrArray *installedPackages = getInstalledPackages(rpmDbSack);
    if (installedPackages == NULL) {
        return;
    }

    for (guint i = 0; i < repoAndProductIds->len; i++) {
        RepoProductId *repoProductId = g_ptr_array_index(repoAndProductIds, i);
        GPtrArray *availPackageList = getAvailPackageList(dnfSack, repoProductId->repo);

        gboolean ret = isAvailPackageInInstalledPackages(installedPackages, availPackageList);
        if (ret == TRUE) {
            debug("Repo \"%s\" marked active", dnf_repo_get_id(repoProductId->repo));
            g_ptr_array_add(activeRepoAndProductIds, repoProductId);
        }

        g_ptr_array_unref(availPackageList);
    }

    g_ptr_array_unref(installedPackages);
    g_object_unref(rpmDbSack);
}


/**
 * Try to get content of productid certificate from DnfRepo structure. Note downloading of productid
 * has to be requested during PLUGIN_HOOK_ID_CONTEXT_CONF hook using dnf_repo_add_metadata_type_to_download
 *
 * @param repo Pointer at DnfRepo structure
 * @return Pointer at char buffer containing certificate. It has to be freed using g_free() later.
 */
gpointer getProductIdContent(DnfRepo *repo) {
    if (repo == NULL) {
        return NULL;
    }

    GError *tmp_err = NULL;
    gpointer content;
    gsize length;
    gboolean productid_downloaded;
    productid_downloaded = dnf_repo_get_metadata_content(repo, "productid", &content, &length, &tmp_err);
    if (productid_downloaded) {
        // Make sure that end of string contains trailing character: '\0'. Library libdnf cannot do that
        // because the library doesn't know anything about content of downloaded metadata
        ((char*)content)[length-1] = '\0';
        return content;
    } else {
        printError("Unable to get productid certificate from DnfRepo structure", tmp_err);
        return NULL;
    }
}

/**
 * This function checks if product-id certificate was downloaded for given repository
 *
 * @param repo Pointer at structure holding information about repository
 * @param repoProductId Pointer at our internal structure
 * @return
 */
int isProductIdDownloaded(DnfRepo *repo, RepoProductId *repoProductId) {
    int ret = 0;

    const gchar *path = dnf_repo_get_filename_md(repo, "productid");

    repoProductId->repo = repo;
    repoProductId->productIdPath = path;
    if (path) {
        debug("Productid certificate downloaded from repo %s to %s",
              dnf_repo_get_id(repo),
              repoProductId->productIdPath);
        ret = 1;
    } else {
        info("Repository %s does not contain any productid certificate",
             dnf_repo_get_id(repo));
    }

    return ret;
}

/**
 * This function tries to find product id certificate in /etc/pki/product-default.
 *
 * @param productId Pointer at buffer with product ID
 * @return Returns 1, when product certificate with same ID is already installed in /etc/pki/product-default.
 * Returns 0 otherwise.
 */
int isProductIdInstalledInDefault(const gchar *productId) {
    int ret = 0;
    // "Open" directory with product certificates
    GError *tmp_err = NULL;
    GDir* defaultProductDir = g_dir_open(DEFAULT_PRODUCT_CERT_DIR, 0, &tmp_err);
    if (defaultProductDir != NULL) {
        const gchar *file_name = NULL;
        do {
            // Read all files in the directory. When file_name is NULL, then
            // it usually means that there is no more file.
            file_name = g_dir_read_name(defaultProductDir);
            if(file_name != NULL) {
                const gchar *defaultProductId = g_strndup(file_name, strlen(file_name) - 4);
                if (g_strcmp0(productId, defaultProductId) == 0) {
                    debug("Productid certificate: %s.pem already installed in %s",
                            productId, DEFAULT_PRODUCT_CERT_DIR);
                    ret = 1;
                    break;
                }
            } else if (errno != 0 && errno != ENODATA && errno != EEXIST) {
                error("Unable to read content of %s directory, %d, %s", PRODUCT_CERT_DIR, errno, strerror(errno));
            }
        } while (file_name != NULL);
        g_dir_close(defaultProductDir);
    } else {
        printError("Unable to open directory with default product certificates", tmp_err);
    }
    return ret;
}

/**
 * This function tries to install productid certificate into system (typically to
 * /etc/pki/product/<product_id>.pem
 *
 * @param repoProductId Pointer on struct holding pointer at repository and destincation path
 * @param productDb Pointer at structure with information about installed product certs
 *
 * @return Return 1, when product certificate was installed to the system. Otherwise, return zero.
 */
int installProductId(RepoProductId *repoProductId, ProductDb *productDb, const char *product_cert_dir) {
    int ret = 0;

    if (repoProductId == NULL || productDb == NULL) {
        return 0;
    }

    if (repoProductId->productIdPath != NULL) {
        gchar *content = getProductIdContent(repoProductId->repo);

        if (content == NULL) {
            return 0;
        }
        GString *pemOutput = g_string_new(content);
        g_free(content);
        GString *outname = g_string_new("");
        debug("Content of product cert:\n%s", pemOutput->str);

        int productIdFound = findProductId(pemOutput, outname);
        if (productIdFound) {
            gint ret_val = g_mkdir_with_parents(product_cert_dir, 0775);
            if (ret_val == 0) {
                gchar *productId = g_strdup(outname->str);
                int already_installed = isProductIdInstalledInDefault(productId);
                if (already_installed == 0) {
                    g_string_prepend(outname, product_cert_dir);
                    g_string_append(outname, ".pem");
                    // TODO switch to using GFile methods to remain consistent with using GLib stuff when possible
                    FILE *fileOutput = fopen(outname->str, "w+");
                    if (fileOutput != NULL) {
                        info("Product certificate installed to: %s", outname->str);
                        fprintf(fileOutput, "%s", pemOutput->str);
                        fclose(fileOutput);

                        addRepoId(productDb, productId, dnf_repo_get_id(repoProductId->repo));
                        ret = 1;
                    } else {
                        error("Unable write to file with certificate file :%s", outname->str);
                    }
                }
                g_free(productId);
            } else {
                error("Unable to create directory %s, %s", product_cert_dir, strerror(errno));
            }
        }

        g_string_free(outname, TRUE);
        g_string_free(pemOutput, TRUE);
    }

    return ret;
}

/**
 * Look at the PEM of a certificate and figure out what is ID of the product.
 *
 * @param certContent String containing content of product certificate
 * @param result String containing ID of of product certificate
 * @return
 */
int findProductId(GString *certContent, GString *result) {
    int ret_val = 1;
    BIO *bio = BIO_new_mem_buf(certContent->str, (int) certContent->len);
    if (bio == NULL) {
        debug("Unable to create buffer for content of certificate: %s",
                ERR_error_string(ERR_get_error(), NULL));
        return -1;
    }

    X509 *x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL);
    BIO_free(bio);
    bio = NULL;

    if (x509 == NULL) {
        debug("Failed to read content of certificate from buffer to X509 structure: %s",
                ERR_error_string(ERR_get_error(), NULL));
        return -1;
    }

    int exts = X509_get_ext_count(x509);
    gboolean redhat_oid_found = FALSE;
    for (int i = 0; i < exts; i++) {
        char oid[MAX_BUFF];
        X509_EXTENSION *ext = X509_get_ext(x509, i);
        if (ext == NULL) {
            debug("Failed to get extension of X509 structure: %s",
                  ERR_error_string(ERR_get_error(), NULL));
            ret_val = -1;
            break;
        }
        OBJ_obj2txt(oid, MAX_BUFF, X509_EXTENSION_get_object(ext), 1);

        if (g_str_has_prefix(oid, REDHAT_PRODUCT_OID)) {
            redhat_oid_found = TRUE;
            gchar **components = g_strsplit(oid, ".", -1);
            int comp_id=0;
            // Because g_strsplit() returns array of NULL terminated pointers,
            // then we have to make sure that array is long enough to contain
            // required ID
            while(components[comp_id] != NULL) {
                comp_id++;
            }
            if (comp_id > 9) {
                debug("ID of product certificate: %s", components[9]);
                g_string_assign(result, components[9]);
            } else {
                error("Product certificate does not contain required ID");
                ret_val = -1;
            }
            g_strfreev(components);
            break;
        }
    }

    if (redhat_oid_found == FALSE) {
        warn("Red Hat Product OID: %s not found", REDHAT_PRODUCT_OID);
        ret_val = -1;
    }

    X509_free(x509);

    return ret_val;
}
