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

#include <stdio.h>
#include <stdlib.h>

#include <json-c/json.h>

#include <glib.h>
#include <gio/gio.h>
#include "productdb.h"

ProductDb * initProductDb() {
    ProductDb *productDb = malloc(sizeof(ProductDb));
    productDb->repoMap = g_hash_table_new(g_str_hash, g_str_equal);
    return productDb;
}

void clearTable(gpointer key, gpointer value, gpointer data) {
    g_slist_free(value);
}

void freeProductDb(ProductDb *productDb) {
    g_hash_table_foreach(productDb->repoMap, (GHFunc) clearTable, NULL);
    g_hash_table_destroy(productDb->repoMap);
    free(productDb);
}

void readProductDb(ProductDb *productDb, GError **err) {
    GFile *dbFile = g_file_new_for_path(productDb->path);
    gchar *contents;

    GError *internalErr = NULL;
    gboolean loadedFile = g_file_load_contents(dbFile, NULL, &contents, NULL, NULL, &internalErr);

    if (!loadedFile) {
        *err = g_error_copy(internalErr);
        g_error_free(internalErr);
        return;
    }

    g_object_unref(dbFile);
    json_object *dbJson = json_tokener_parse(contents);

    GHashTable *repoMap = g_hash_table_new(g_str_hash, g_str_equal);
    struct json_object_iterator it = json_object_iter_begin(dbJson);
    struct json_object_iterator itEnd = json_object_iter_end(dbJson);
    while (!json_object_iter_equal(&it, &itEnd)) {
        gchar *productId = json_object_iter_peek_name(&it);
        g_hash_table_add(repoMap, productId);
        json_object *repoIds = json_object_iter_peek_value(&it);
        json_object_iter_next(&it);
    }
}

void writeProductDb(ProductDb *productDb, GError **err) {

}

void addRepoId(ProductDb *productDb, const char *productId, const char *repoId) {
    // If the value isn't present, this value will be a NULL and g_slist_prepend will
    // begin a new list
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);
    // We prepend so that we don't have to walk the entire linked list
    g_hash_table_insert(
        productDb->repoMap,
        (gpointer) productId,
        g_slist_prepend(valueList, (gpointer) repoId)
    );

}

gboolean removeProductId(ProductDb *productDb, const char *productId) {
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);
    if (valueList) {
        g_hash_table_replace(productDb->repoMap, (gpointer) productId, NULL);
        g_slist_free(valueList);
    }
    return g_hash_table_remove(productDb->repoMap, productId);
}

gboolean removeRepoId(ProductDb *productDb, const char *productId, const char *repoId) {
    GSList *repoIds = g_hash_table_lookup(productDb->repoMap, productId);
    if (repoIds) {
        GSList *modifiedRepoIds = g_slist_remove_all(repoIds, repoId);
        // If an item is removed modifiedList will point to a different place than valueList
        if (repoIds == modifiedRepoIds) {
            g_hash_table_replace(productDb->repoMap, (gpointer) productId, modifiedRepoIds);
            return TRUE;
        }
    }
    return FALSE;
}

gboolean hasProductId(ProductDb *productDb, const char *productId) {
    return g_hash_table_contains(productDb->repoMap, productId);
}


gboolean hasRepoId(ProductDb *productDb, const char *productId, const char *repoId) {
    GSList *repoIds = g_hash_table_lookup(productDb->repoMap, productId);
    if (repoIds) {
        GSList *iterator = NULL;
        for (iterator = repoIds; iterator; iterator = iterator->next) {
            if(g_strcmp0(repoId, iterator->data) == 0) {
                return TRUE;
            }
        }

    }
    return FALSE;
};


void printTable(gpointer key, gpointer value, gpointer data) {
    g_string_append_printf(data, "\t%s:", (char *) key);

    GSList *iterator = NULL;
    for (iterator = value; iterator; iterator = iterator->next) {
        g_string_append_printf(data, "%s ", (char *) iterator->data);
    }
    g_string_append(data, "\n");
}

char *toString(ProductDb *productDb) {
    GString *out = g_string_new("");
    g_string_printf(out, "Path: %s\n", productDb->path);
    g_string_append(out, "Contents:\n");

    g_hash_table_foreach(productDb->repoMap, (GHFunc) printTable, out);
    return g_strdup(out->str);
}

