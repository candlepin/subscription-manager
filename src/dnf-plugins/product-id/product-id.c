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

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

int fetchProductId(DnfRepo *repo);

// This stuff could go in a header file, I guess
static const PluginInfo pinfo = {
    .name = "Product ID - DNF Test Plugin",
    .version = "1.0.0"
};

struct _PluginHandle {
    // Data provided by the init method
    int version;
    PluginMode mode;
    void* initData;

    // Add plugin-specific "private" data here
};



const PluginInfo *pluginGetInfo() {
    return &pinfo;
}

void write_log_msg(void) {
    FILE *f = fopen("/tmp/libdnf_plugin.log", "a");
    if(f != NULL) {
	time_t result = time(NULL);
        fprintf(f, "libdnf plugin: %s%ju\n", asctime(localtime(&result)), (uintmax_t)result);
        fclose(f);
        f = NULL;
    }
}

PluginHandle *pluginInitHandle(int version, PluginMode mode, void *initData) {
    printf("%s initializing handle!\n", pinfo.name);
    write_log_msg();

    PluginHandle* handle = malloc(sizeof(PluginHandle));

    if (handle) {
        handle->version = version;
        handle->mode = mode;
        handle->initData = initData;
    }

    return handle;
}

void pluginFreeHandle(PluginHandle *handle) {
    printf("%s freeing handle!\n", pinfo.name);
    write_log_msg();

    if (handle) {
        free(handle);
    }
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
 * @param activeRepos the list of repos providing active
 */
void getActive(DnfContext *context, const GPtrArray *repos, GPtrArray *activeRepos) {
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
            printf("%s is installed from %s\n", dnf_package_get_nevra(pkg), dnf_package_get_reponame(pkg));
            g_ptr_array_add(installedPackages, pkg);
        }
    }

    for (int i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
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
                    printf("Repo \"%s\" marked active due to installed package %s\n",
                           dnf_repo_get_id(repo),
                           dnf_package_get_nevra(pkg));
                    g_ptr_array_add(activeRepos, repo);
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
    fprintf(stderr, "Error encountered: %d: %s\n", err->code, err->message);
    g_error_free(err);
}

int pluginHook(PluginHandle *handle, PluginHookId id, void *hookData, PluginHookError *error) {
    if (!handle) {
        // We must have failed to allocate our handle during init; don't do anything.
        return 0;
    }

    printf("%s v%s, running on DNF version %d\n", pinfo.name, pinfo.version, handle->version);
    write_log_msg();

    if (id == PLUGIN_HOOK_ID_CONTEXT_PRE_TRANSACTION) {
        DnfContext *dnfContext = handle->initData;
        // List of all repositories
        GPtrArray *repos = dnf_context_get_repos(dnfContext);
        // List of enabled repositories
        GPtrArray *enabledRepos = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with product id certificate
        GPtrArray *enabledProdIDRepos = g_ptr_array_sized_new(repos->len);
        // Enabled repositories with prouctid cert that are actively used
        GPtrArray *activeRepos = g_ptr_array_sized_new(repos->len);

        getEnabled(repos, enabledRepos);

        for (int i = 0; i < enabledRepos->len; i++) {
            DnfRepo *repo = g_ptr_array_index(enabledRepos, i);
            LrResult *lrResult = dnf_repo_get_lr_result(repo);
            LrYumRepoMd *repoMd;
            GError *tmp_err = NULL;

            lr_result_getinfo(lrResult, &tmp_err, LRR_YUM_REPOMD, &repoMd);
            if (tmp_err) {
                printError(tmp_err);
            }
            else {
                LrYumRepoMdRecord *repoMdRecord = lr_yum_repomd_get_record(repoMd, "productid");
                if (repoMdRecord) {
                    int ret = fetchProductId(repo);
                    if(ret == 1) {
                        g_ptr_array_add(enabledProdIDRepos, repo);
                    }
                }
            }
        }
        getActive(dnfContext, enabledProdIDRepos, activeRepos);

        g_ptr_array_unref(repos);
        g_ptr_array_unref(enabledRepos);
        g_ptr_array_unref(enabledProdIDRepos);
        g_ptr_array_unref(activeRepos);
    }

    return 1;
}

int fetchProductId(DnfRepo *repo) {
    GError *tmp_err = NULL;
    LrHandle *lrHandle = dnf_repo_get_lr_handle(repo);
    char *downloadList[] = {"productid", NULL};
    int ret_val = 0;

    LrHandle *h = lr_handle_init();
    LrResult *r = lr_result_init();

    char *url;
    lr_handle_getinfo(lrHandle, &tmp_err, LRO_URLS, &url);
    if (tmp_err) {
        printError(tmp_err);
    }
    lr_handle_setopt(h, NULL, LRO_URLS, url);
    lr_handle_setopt(h, NULL, LRO_REPOTYPE, LR_YUMREPO);
    lr_handle_setopt(h, NULL, LRO_YUMDLIST, downloadList);

    printf("Ready to perform\n");
    gboolean ret = lr_handle_perform(h, r, &tmp_err);
    if (ret) {
        char *destdir;
        lr_handle_getinfo(h, &tmp_err, LRI_DESTDIR, &destdir);
        printf("Product id cert downloaded to dest dir is %s\n", destdir);
        ret_val = 1;
    } else {
        printError(tmp_err);
    }

    lr_handle_free(h);
    lr_result_free(r);

    return ret_val;
}
