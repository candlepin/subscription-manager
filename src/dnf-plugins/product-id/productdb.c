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
#include <string.h>
#include "productdb.h"

/**
 * Function to free the values in the GHashTable we use to represent the productDB internally
 * @param value pointer to the GSList that holds the repo IDs.
 */
void valueFree(gpointer value) {
    GSList *iterator = NULL;
    for (iterator = value; iterator; iterator = iterator->next) {
        g_free(iterator->data);
    }
    g_slist_free(value);
}

/**
 * Allocate memory for a new ProductDb.
 * @return a ProductId
 */
ProductDb *initProductDb() {
    ProductDb *productDb = malloc(sizeof(ProductDb));
    productDb->path = NULL;
    // TODO: implement methods for freeing key and value
    productDb->repoMap = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    return productDb;
}

void freeProductDb(ProductDb *productDb) {
    g_hash_table_destroy(productDb->repoMap);
    free(productDb);
}

/**
 * Read content of product db from json file into structure
 *
 * @param productDb Pointer at ProductDb struct.  The ProductDb is populated.
 * @param err Pointer to a pointer to a glib error.  Updated if an error occurs.
 */
void readProductDb(ProductDb *productDb, GError **err) {
    GFile *dbFile = g_file_new_for_path(productDb->path);
    gchar *fileContents;

    GError *internalErr = NULL;
    gboolean loadedFileSuccess = g_file_load_contents(dbFile, NULL, &fileContents, NULL, NULL, &internalErr);
    if (!loadedFileSuccess) {
        *err = g_error_copy(internalErr);
        g_error_free(internalErr);
        return;
    }
    g_object_unref(dbFile);

    json_object *dbJson = json_tokener_parse(fileContents);

    GHashTable *repoMap = productDb->repoMap;
    struct json_object_iterator it = json_object_iter_begin(dbJson);
    struct json_object_iterator itEnd = json_object_iter_end(dbJson);
    while (!json_object_iter_equal(&it, &itEnd)) {
        gchar *productId = g_strdup(json_object_iter_peek_name(&it));
        json_object *repoIds = json_object_iter_peek_value(&it);
        GSList *repoList = NULL;

        array_list *idArray = json_object_get_array(repoIds);
        int len = array_list_length(idArray);

        for (int i=0; i<len; i++) {
            json_object *o = array_list_get_idx(idArray, i);
            gchar *repoId = g_strdup(json_object_get_string(o));
            repoList = g_slist_prepend(repoList, (gpointer) repoId);
        }

        g_hash_table_insert(repoMap, productId, repoList);
        json_object_iter_next(&it);
    }

    // Free productIdDb.  JSON-C has a confusing method name for this
    json_object_put(dbJson);
    g_free(fileContents);
}

/**
 * Write the GHashTable in the ProductDb repoMap field to the path stored in the ProductDb path field.
 * @param productDb populated ProductDb
 * @param err a pointer to a pointer to a glib error.  Updated if an error occurs.
 */
void writeProductDb(ProductDb *productDb, GError **err) {
    json_object *productIdDb = json_object_new_object();
    GList *keys = g_hash_table_get_keys(productDb->repoMap);

    GList *iterator = NULL;

    for(iterator = keys; iterator; iterator=iterator->next) {
        gchar *productId = g_strdup(iterator->data);
        json_object *repoIdJson = json_object_new_array();

        GList *values = g_hash_table_lookup(productDb->repoMap, productId);
        GList *valuesIterator = NULL;
            for(valuesIterator = values; valuesIterator; valuesIterator=valuesIterator->next) {
            gchar *repoId = g_strdup(valuesIterator->data);
            json_object_array_add(repoIdJson, json_object_new_string(repoId));
        }
        json_object_object_add(productIdDb, productId, repoIdJson);
    }

    gchar *dbJson = (gchar *) json_object_to_json_string(productIdDb);

    g_list_free(keys);

    GFile *dbFile = g_file_new_for_path(productDb->path);
    GError *internalErr = NULL;

    GFileOutputStream *os = g_file_replace(dbFile, NULL, FALSE, G_FILE_CREATE_NONE, NULL, &internalErr);
    if (!internalErr) {
        g_output_stream_write_all((GOutputStream *) os, dbJson, strlen(dbJson), NULL, NULL, &internalErr);
        g_output_stream_close((GOutputStream *) os, NULL, &internalErr);
    }

    // Free productIdDb.  JSON-C has a confusing method name for this
    json_object_put(productIdDb);
    g_object_unref(dbFile);
    g_object_unref(os);

    if (internalErr) {
        *err = g_error_copy(internalErr);
        g_error_free(internalErr);
        return;
    }
}

/**
 * Add a repo ID to the list of repo IDs associated to a product ID.  The list deduplicates redundant entries.
 * @param productDb ProductDb to update
 * @param productId ID to associate the repo ID to
 * @param repoId repo ID to associate
 */
void addRepoId(ProductDb *productDb, const char *productId, const char *repoId) {
    // If the value isn't present, this value will be a NULL and g_slist_prepend will
    // begin a new list
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);

    GSList *existsNode = g_slist_find((GSList *) valueList, repoId);
    if (!existsNode) {
        // We prepend so that we don't have to walk the entire linked list
        g_hash_table_insert(
            productDb->repoMap,
            (gpointer) productId,
            g_slist_prepend(valueList, (gpointer) repoId)
        );
    }
}

/**
 * Remove of a product ID from the product DB.
 * @param productDb ProductDb to update
 * @param productId ID to remove
 * @return TRUE if the ID was found and removed
 */
gboolean removeProductId(ProductDb *productDb, const char *productId) {
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);
    if (valueList) {
        g_hash_table_replace(productDb->repoMap, (gpointer) productId, NULL);
        g_slist_free(valueList);
    }
    return g_hash_table_remove(productDb->repoMap, productId);
}

/**
 * Remove a repo ID from the list of repo IDs associated to a product ID.
 * @param productDb ProductDb to update
 * @param productId product ID to edit
 * @param repoId repo ID to remove from the list associate to the product ID
 * @return TRUE if the ID was found and removed
 */
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

/**
 * Search for a given product ID in a product DB.
 * @param productDb productDB to interrogate
 * @param productId product ID to search for
 * @return TRUE if this productDB contains the given product ID
 */
gboolean hasProductId(ProductDb *productDb, const char *productId) {
    return g_hash_table_contains(productDb->repoMap, productId);
}

/**
 * Search for a given repo ID within the scope of a given product ID.
 * @param productDb productDB to interrogate
 * @param productId product ID to interrogate
 * @param repoId repo ID to search for
 * @return TRUE if the product ID in the given product DB contains the repo ID
 */
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
}

/**
 * Private-ish method used to print out entries from a GHashTable
 * @param key hash key
 * @param value hash value
 * @param data in this case, a GString to append to
 */
void printProductIdHashTable(gpointer key, gpointer value, gpointer data) {
    // data is a pointer to a GString
    g_string_append_printf(data, "\t%s:", (char *) key);

    GSList *iterator = NULL;
    for (iterator = value; iterator; iterator = iterator->next) {
        g_string_append_printf(data, "%s ", (char *) iterator->data);
    }
    g_string_append(data, "\n");
}

/**
 * Create a string representation of a product DB.
 * @param productDb product DB to print
 * @return string containing the data in a product DB
 */
char *productDbToString(ProductDb *productDb) {
    GString *out = g_string_new("");
    g_string_printf(out, "Path: %s\n", productDb->path);
    g_string_append(out, "Contents:\n");

    g_hash_table_foreach(productDb->repoMap, (GHFunc) printProductIdHashTable, out);
    return g_strdup(out->str);
}

