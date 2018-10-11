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

void fetchProductId(DnfRepo *repo);

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

    HyQuery query = hy_query_create_flags(dnfSack, 0);
    hy_query_filter(query, HY_PKG_NAME, HY_GLOB, "*");

    GPtrArray *packageList = hy_query_run(query);
    GPtrArray *installedPackages = g_ptr_array_sized_new(packageList->len);
    hy_query_free(query);

    for (int i = 0; i < packageList->len; i++) {
        DnfPackage *pkg = g_ptr_array_index(packageList, i);
        guint64 id = dnf_package_get_rpmdbid(pkg);

        if (id) {
            g_ptr_array_add(installedPackages, pkg);
        }
    }

    for (int i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        printf("Looking in %s against %i packages\n", dnf_repo_get_id(repo), installedPackages->len);

        for (int j = 0; j < installedPackages->len; j++) {
            DnfPackage *instPkg = g_ptr_array_index(installedPackages, j);
            HyQuery repoQuery = hy_query_create_flags(dnfSack, 0);
            hy_query_filter(repoQuery, HY_PKG_NEVRA, HY_EQ, dnf_package_get_nevra(instPkg));
            hy_query_filter(repoQuery, HY_PKG_REPONAME, HY_EQ, dnf_repo_get_id(repo));

            GPtrArray *repoPackageList = hy_query_run(repoQuery);
            hy_query_free(repoQuery);

            if (repoPackageList->len) {
                const char *nvra = dnf_package_get_nevra(instPkg);
                const char *repoName = dnf_package_get_reponame(instPkg);
                printf("%s is from %s\n", nvra, repoName);
                g_ptr_array_add(activeRepos, repo);
                break;
            }
            g_ptr_array_unref(repoPackageList);
        }
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
        GPtrArray *repos = dnf_context_get_repos(dnfContext);
        GPtrArray *enabledRepos = g_ptr_array_sized_new(repos->len);
        GPtrArray *activeRepos = g_ptr_array_sized_new(repos->len);

        getEnabled(repos, enabledRepos);
        getActive(dnfContext, repos, activeRepos);

        for (unsigned int i = 0; i < enabledRepos->len; i++) {
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
                    fetchProductId(repo);
                }
            }
        }
    }
    return 1;
}

void fetchProductId(DnfRepo *repo) {
    GError *tmp_err = NULL;
    LrHandle *lrHandle = dnf_repo_get_lr_handle(repo);
    char *downloadList[] = {"productid", NULL};

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
        printf("Dest dir is %s\n", destdir);
    } else {
        printError(tmp_err);
    }

    lr_handle_free(h);
    lr_result_free(r);
}
