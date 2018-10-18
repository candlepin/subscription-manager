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
#include <libdnf/libdnf.h>

#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/err.h>

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <zlib.h>

#define LOGFILE "/var/log/rhsm/productid.log"
#define CHUNK 16384

// This stuff could go in a header file, I guess
static const PluginInfo pinfo = {
    .name = "Product ID - DNF Test Plugin",
    .version = "1.0.0"
};

static char *const PRODUCT_CERT_DIR = "/etc/pki/product/";

static const int MAX_BUFF = 256;
/**
 * Structure holding all data specific for this plugin
 */
struct _PluginHandle {
    // Data provided by the init method
    int version;
    PluginMode mode;
    void* initData;

    // Add plugin-specific "private" data here
};

typedef struct {
    DnfRepo *repo;
    const char *productIdPath;

} RepoProductId;

static gboolean show_debug = TRUE;

void printError(GError *err);
void getEnabled(const GPtrArray *repos, GPtrArray *enabledRepos);
void getActive(DnfContext *context, const GPtrArray *repoAndProductIds, GPtrArray *activeRepoAndProductIds);

// Prototypes of functions used in this plugin
int decompress(gzFile input, GString *output) ;
int findProductId(GString *certContent, GString *result);
int fetchProductId(DnfRepo *repo, RepoProductId *repoProductId);
int installProductId(const char *productIdPath);

const PluginInfo *pluginGetInfo() {
    return &pinfo;
}


const char *timestamp () {
    time_t tm = time (0);
    char *ts = asctime (localtime (&tm));
    char *p = ts;
    while (*p) {
        p++;
        if (*p == '\n') {
            *p = 0;
        }
    }
    return ts;
}

/*
 * log function. If we can't open the log, attempt to log to stdout
 * rather than fail. opening the log each time is OK since we log so rarely.
 *
 * prototype included here so we can use the printf format checking.
 */
void r_log (const char *level, const char *message, ...)
__attribute__ ((format (printf, 2, 3)));

void r_log (const char *level, const char *message, ...)
{
    bool use_stdout = false;
    va_list argp;
    FILE *log_file = fopen (LOGFILE, "a");
    if (!log_file) {
        // redirect message to stdout
        log_file = stdout;
        use_stdout = true;
    }
    va_start (argp, message);

    fprintf (log_file, "%s [%s] ", timestamp (), level);
    vfprintf (log_file, message, argp);
    putc ('\n', log_file);

    if (!use_stdout) {
        fclose (log_file);
    }

    va_end(argp);
}

#define info(msg, ...) r_log ("INFO", msg, ##__VA_ARGS__)
#define warn(msg, ...) r_log ("WARN", msg, ##__VA_ARGS__)
#define error(msg, ...) r_log ("ERROR", msg, ##__VA_ARGS__)
#define debug(msg, ...) if (show_debug) r_log ("DEBUG", msg, ##__VA_ARGS__)

/**
 * Initialize handle of this plugin
 * @param version
 * @param mode
 * @param initData
 * @return
 */
PluginHandle *pluginInitHandle(int version, PluginMode mode, void *initData) {
    debug("%s initializing handle!", pinfo.name);

    PluginHandle* handle = malloc(sizeof(PluginHandle));

    if (handle) {
        handle->version = version;
        handle->mode = mode;
        handle->initData = initData;
    }

    return handle;
}

/**
 * Free handle and all
 * @param handle
 */
void pluginFreeHandle(PluginHandle *handle) {
    debug("%s freeing handle!", pinfo.name);

    if (handle) {
        free(handle);
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
int pluginHook(PluginHandle *handle, PluginHookId id, void *hookData, PluginHookError *error) {
    if (!handle) {
        // We must have failed to allocate our handle during init; don't do anything.
        return 0;
    }

    debug("%s v%s, running hook: %d on DNF version %d", pinfo.name, pinfo.version, id, handle->version);

    if (id == PLUGIN_HOOK_ID_CONTEXT_PRE_TRANSACTION) {
        DnfContext *dnfContext = handle->initData;
        // List of all repositories
        GPtrArray *repos = dnf_context_get_repos(dnfContext);
        // List of enabled repositories
        GPtrArray *enabledRepos = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with product id certificate
        GPtrArray *repoAndProductIds = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with prouctid cert that are actively used
        GPtrArray *activeRepoAndProductIds = g_ptr_array_sized_new(repos->len);

        getEnabled(repos, enabledRepos);

        for (int i = 0; i < enabledRepos->len; i++) {
            DnfRepo *repo = g_ptr_array_index(enabledRepos, i);
            LrResult *lrResult = dnf_repo_get_lr_result(repo);
            LrYumRepoMd *repoMd;
            GError *tmp_err = NULL;

            debug("Enabled: %s", dnf_repo_get_id(repo));
            lr_result_getinfo(lrResult, &tmp_err, LRR_YUM_REPOMD, &repoMd);
            if (tmp_err) {
                printError(tmp_err);
            }
            else {
                LrYumRepoMdRecord *repoMdRecord = lr_yum_repomd_get_record(repoMd, "productid");
                if (repoMdRecord) {
                    debug("Repository %s has a productid", dnf_repo_get_id(repo));
                    RepoProductId *repoProductId = malloc(sizeof(RepoProductId));
                    int fetchSuccess = fetchProductId(repo, repoProductId);
                    if(fetchSuccess == 1) {
                        g_ptr_array_add(repoAndProductIds, repoProductId);
                    }
                }
            }
        }

        getActive(dnfContext, repoAndProductIds, activeRepoAndProductIds);
        for (int i = 0; i < activeRepoAndProductIds->len; i++) {
            RepoProductId *activeRepoProductId = g_ptr_array_index(activeRepoAndProductIds, i);
            debug("Handling active repo %s\n", dnf_repo_get_id(activeRepoProductId->repo));
            installProductId(activeRepoProductId->productIdPath);
        }

        // We have to free memory allocated for all items of repoAndProductIds
        for (int i=0; i < repoAndProductIds->len; i++) {
            RepoProductId *repoProductId = g_ptr_array_index(repoAndProductIds, i);
            free(repoProductId);
        }

        g_ptr_array_unref(repos);
        g_ptr_array_unref(enabledRepos);
        g_ptr_array_unref(repoAndProductIds);
        g_ptr_array_unref(activeRepoAndProductIds);
    }

    return 1;
}

/**
 * Find the list of repos that are actually enabled
 * @param repos all available repos
 * @param enabledRepos the list of enabled repos
 */
void getEnabled(const GPtrArray *repos, GPtrArray *enabledRepos) {
    for (int i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        bool enabled = (dnf_repo_get_enabled(repo) & DNF_REPO_ENABLED_PACKAGES) > 0;
        if (enabled) {
            g_ptr_array_add(enabledRepos, repo);
        }
    }
}

/**
 * Find the list of repos that provide packages that are actually installed.
 * @param repos all available repos
 * @param activeRepoAndProductIds the list of repos providing active
 */
void getActive(DnfContext *context, const GPtrArray *repoAndProductIds, GPtrArray *activeRepoAndProductIds) {
    DnfSack *dnfSack = dnf_context_get_sack(context);

    // FIXME: this query does not provide fresh list of installed packages
    // Currently installed/removed package is not listed in the query.
    // The problem is with sack. We have to get it in different way.
    HyQuery query = hy_query_create_flags(dnfSack, 0);
    hy_query_filter(query, HY_PKG_NAME, HY_GLOB, "*");
    hy_query_filter(query, HY_REPO_NAME, HY_EQ, HY_SYSTEM_REPO_NAME);

    GPtrArray *packageList = hy_query_run(query);
    GPtrArray *installedPackages = g_ptr_array_sized_new(packageList->len);
    hy_query_free(query);

    for (int i = 0; i < packageList->len; i++) {
        DnfPackage *pkg = g_ptr_array_index(packageList, i);

        if (dnf_package_installed(pkg)) {
            g_ptr_array_add(installedPackages, pkg);
        }
    }

    for (int i = 0; i < repoAndProductIds->len; i++) {
        RepoProductId *repoProductId = g_ptr_array_index(repoAndProductIds, i);
        DnfRepo *repo = repoProductId->repo;
        HyQuery availQuery = hy_query_create_flags(dnfSack, 0);
        hy_query_filter(availQuery, HY_PKG_REPONAME, HY_EQ, dnf_repo_get_id(repo));
        GPtrArray *availPackageList = hy_query_run(availQuery);
        hy_query_free(availQuery);

        // NB: Another way to do this would be with a bloom filter.  A bloom filter can give a very quick,
        // accurate answer to the question "Is this item not in this set of things?" if the result is
        // negative.  A positive result is probabilistic and requires a second full scan of the set to get the
        // ultimate answer.  The bloom filter approach would eliminate the need for the O(n^2) nested for-loop
        // solution we have.

        // Go through all available packages from repository
        for (int j = 0; j < availPackageList->len; j++) {
            DnfPackage *pkg = g_ptr_array_index(availPackageList, j);
            gboolean package_found = FALSE;

            // Try to find if this available package is in the list of installed packages
            for(int k = 0; k < installedPackages->len; k++) {
                DnfPackage *instPkg = g_ptr_array_index(installedPackages, k);
                if(strcmp(dnf_package_get_nevra(pkg), dnf_package_get_nevra(instPkg)) == 0) {
                    debug("Repo \"%s\" marked active due to installed package %s",
                           dnf_repo_get_id(repo),
                           dnf_package_get_nevra(pkg));
                    g_ptr_array_add(activeRepoAndProductIds, repoProductId);
                    package_found = TRUE;
                    break;
                }
            }

            if(package_found == TRUE) {
                break;
            }
        }
        g_ptr_array_unref(availPackageList);
    }

    g_ptr_array_unref(installedPackages);
    g_ptr_array_unref(packageList);
}

void printError(GError *err) {
    error("Encountered: %d: %s", err->code, err->message);
    g_error_free(err);
}

int fetchProductId(DnfRepo *repo, RepoProductId *repoProductId) {
    int ret = 0;
    GError *tmp_err = NULL;
    LrHandle *lrHandle = dnf_repo_get_lr_handle(repo);
    LrResult *lrResult = dnf_repo_get_lr_result(repo);

    // getinfo uses the LRI* constants while setopt uses LRO*
    char *destdir;
    lr_handle_getinfo(lrHandle, &tmp_err, LRI_DESTDIR, &destdir);
    if (tmp_err) {
        printError(tmp_err);
    }

    char *url = NULL;
    lr_handle_getinfo(lrHandle, &tmp_err, LRI_URLS, &url);
    if (tmp_err) {
        printError(tmp_err);
    }

    /* Set information on our LrHandle instance.  The LRO_UPDATE option is to tell the LrResult to update the
     * repo (i.e. download missing information) rather than attempt to replace it.
     *
     * FIXME: The internals of this are unclear.  Do we need to create our own LrHandle instance or could we
     * use the one provided and just modify the download list?  Is reusing the LrResult going to cause
     * problems?
     */
    char *downloadList[] = {"productid", NULL};
    LrHandle *h = lr_handle_init();
    lr_handle_setopt(h, NULL, LRO_YUMDLIST, downloadList);
    lr_handle_setopt(h, NULL, LRO_URLS, url);
    lr_handle_setopt(h, NULL, LRO_REPOTYPE, LR_YUMREPO);
    lr_handle_setopt(h, NULL, LRO_DESTDIR, destdir);
    lr_handle_setopt(h, NULL, LRO_UPDATE, TRUE);

    gboolean handleSuccess = lr_handle_perform(h, lrResult, &tmp_err);
    if (handleSuccess) {
        LrYumRepo *lrYumRepo = lr_yum_repo_init();
        if (lrYumRepo != NULL) {
            lr_result_getinfo(lrResult, &tmp_err, LRR_YUM_REPO, &lrYumRepo);
            repoProductId->repo = repo;
            repoProductId->productIdPath = lr_yum_repo_path(lrYumRepo, "productid");
            info("Product id cert downloaded from repo metadata to %s", repoProductId->productIdPath);
            ret = 1;
            lr_yum_repo_free(lrYumRepo);
            lrYumRepo = NULL;
        } else {
            error("Unable to initialize LrYumRepo");
        }
    } else {
        printError(tmp_err);
    }

    if(url) {
        free(url);
    }
    lr_handle_free(h);
    return ret;
}

int installProductId(const char *productIdPath) {
    int ret_val = 0;

    gzFile input = gzopen(productIdPath, "r");

    if (input != NULL) {
        GString *output = g_string_new("");
        GString *outname = g_string_new("");

        debug("Decompresing product certificate");
        ret_val = decompress(input, output);
        debug("Decompressing of certificate finished with status: %d", ret_val);
        debug("Content of product cert:\n%s", output->str);

        int product_id_found = findProductId(output, outname);
        if (product_id_found) {
            g_string_prepend(outname, PRODUCT_CERT_DIR);
            g_string_append(outname, ".pem");
            FILE *fileOutput = fopen(outname->str, "w+");
            if (fileOutput != NULL) {
                debug("Content of certificate written to: %s", outname->str);
                fprintf(fileOutput, "%s", output->str);
                fclose(fileOutput);
            } else {
                error("Unable write to file with certificate file :%s", outname->str);
            }
        } else {
            ret_val = -1;
        }
        g_string_free(outname, TRUE);
        g_string_free(output, TRUE);
    }
    if(input != NULL) {
        gzclose(input);
    } else {
        debug("Unable to open compressed product certificate");
    }

    return ret_val;
}

/**
 * Look at the PEM of a certificate and figure out what is ID of the product.
 *
 * @param certContent String containing content of product certificate
 * @param result String containing ID of of product certificate
 * @return
 */
int findProductId(GString *certContent, GString *result) {
    // The Red Hat OID plus ".1" which is the product namespace
    char *prefix = "1.3.6.1.4.1.2312.9.1";

    BIO *bio = BIO_new_mem_buf(certContent->str, (int) certContent->len);
    if (bio == NULL) {
        debug("Unable to create buffer for content of certificate: %s",
                ERR_error_string(ERR_get_error(), NULL));
        return -1;
    }
    X509 *x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL);
    if (x509 == NULL) {
        debug("Failed to read content of certificate from buffer to X509 structure: %s",
                ERR_error_string(ERR_get_error(), NULL));
        return -1;
    }
    BIO_free(bio);
    bio = NULL;

    int exts = X509_get_ext_count(x509);
    for (int i = 0; i < exts; i++) {
        char oid[MAX_BUFF];
        X509_EXTENSION *ext = X509_get_ext(x509, i);
        if (ext == NULL) {
            debug("Failed to get extension of X509 structure: %s",
                  ERR_error_string(ERR_get_error(), NULL));
            return -1;
        }
        OBJ_obj2txt(oid, MAX_BUFF, X509_EXTENSION_get_object(ext), 1);

        if (strncmp(prefix, oid, strlen(prefix)) == 0) {
            gchar **components = g_strsplit(oid, ".", -1);
            int comp_id=0;
            // Because g_strsplit() returns array of NULL terminated pointers,
            // then we have to make sure that array is long enough to contain
            // required ID
            while(components[comp_id] != NULL) {
                comp_id++;
            }
            debug("Number of OID components: %d", comp_id);
            if (comp_id > 9) {
                debug("ID of product certificate: %s", (char*)components[9]);
                g_string_assign(result, components[9]);
            } else {
                error("Product certificate does not contain required ID");
            }
            g_strfreev(components);
            break;
        }
    }

    return 1;
}

/**
 * Decompress product certificate
 *
 * @param input This is pointer at input compressed file
 * @param output Pointer at string, where content of certificate will be stored
 * @return Return TRUE, when decompression was successful. Otherwise return FALSE.
 */
int decompress(gzFile input, GString *output) {
    int ret = TRUE;
    while (1) {
        int err;
        int bytes_read;
        unsigned char buffer[CHUNK];
        bytes_read = gzread(input, buffer, CHUNK - 1);
        buffer[bytes_read] = '\0';
        g_string_printf(output, "%s", buffer);
        if (bytes_read < CHUNK - 1) {
            if (gzeof (input)) {
                break;
            }
            else {
                const char * error_string;
                error_string = gzerror(input, & err);
                if (err) {
                    error("Decompressing failed with error: %s.", error_string);
                    ret = FALSE;
                    break;
                }
            }
        }
    }
    return ret;
}