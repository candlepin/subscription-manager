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


void write_log_msg(void);

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

void write_log_msg(void)
{
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

void downloadProductId(DnfRepo *repo) {

}

void getEnabled(const GPtrArray *repos, GPtrArray *enabledRepos) {
    for (int i = 0; i < repos->len; i++) {
        DnfRepo* repo = g_ptr_array_index(repos, i);
        bool enabled = (dnf_repo_get_enabled(repo) & DNF_REPO_ENABLED_PACKAGES) > 0;
        if (enabled) {
            // download ProductId
            // Get the cert.
            // If download fails, add error
            // if cert is not none, add it to the enabledRepos list
            g_ptr_array_add(enabledRepos, repo);
        }
    }
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

        getEnabled(repos, enabledRepos);

    }
    return 1;
}

