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
#include "util.h"

/**
 * Allocate memory for a new ProductDb.
 * @return a ProductId
 */
ProductDb *initProductDb() {
    ProductDb *productDb = malloc(sizeof(ProductDb));
    productDb->path = NULL;
    // We do not provide method for freeing value, because it would be ineficient to
    // free and recreate GSList everytime we add/remove item in the list
    productDb->repoMap = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);
    return productDb;
}

static void freeRepodIds(gpointer key, gpointer value, gpointer unused) {
    (void) key;
    (void) unused;
    g_slist_free_full(value, g_free);
}

/**
 * Free memory used by ProductDb
 * @param productDb
 */
void freeProductDb(ProductDb *productDb) {
    g_hash_table_foreach(productDb->repoMap, freeRepodIds, NULL);
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
    if (dbFile == NULL) {
        return;
    }

    gchar *fileContents;
    GError *internalErr = NULL;
    gboolean loadedFileSuccess = g_file_load_contents(dbFile, NULL, &fileContents, NULL, NULL, &internalErr);
    g_object_unref(dbFile);

    if (!loadedFileSuccess) {
        *err = g_error_copy(internalErr);
        g_error_free(internalErr);
        return;
    }

    json_object *dbJson = json_tokener_parse(fileContents);
    g_free(fileContents);

    const gchar *error_string = "Content of /var/lib/rhsm/productid.js file is corrupted";
    GQuark quark = g_quark_from_string(error_string);

    if (dbJson == NULL) {
        *err = g_error_new(quark, 0, error_string);
        return;
    }

    GHashTable *repoMap = productDb->repoMap;
    struct json_object_iterator it = json_object_iter_begin(dbJson);
    struct json_object_iterator itEnd = json_object_iter_end(dbJson);
    while (!json_object_iter_equal(&it, &itEnd)) {
        gchar *productId = g_strdup(json_object_iter_peek_name(&it));
        if (productId) {
            json_object *repoIds = json_object_iter_peek_value(&it);
            if (repoIds == NULL) {
                *err = g_error_new(quark, 0, error_string);
                return;
            }
            GSList *repoList = NULL;

            array_list *idArray = json_object_get_array(repoIds);
            if (idArray == NULL) {
                *err = g_error_new(quark, 0, error_string);
                return;
            }
            int len = array_list_length(idArray);

            for (int i = 0; i < len; i++) {
                json_object *o = array_list_get_idx(idArray, i);
                gchar *repoId = g_strdup(json_object_get_string(o));
                if (repoId == NULL) {
                    *err = g_error_new(quark, 0, error_string);
                    return;
                }
                repoList = g_slist_prepend(repoList, (gpointer) repoId);
            }

            g_hash_table_insert(repoMap, productId, repoList);
        }
        json_object_iter_next(&it);
    }

    // Free productIdDb.  JSON-C has a confusing method name for this
    json_object_put(dbJson);
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
        const gchar *productId = iterator->data;
        json_object *repoIdJson = json_object_new_array();

        GList *values = g_hash_table_lookup(productDb->repoMap, productId);
        GList *valuesIterator = NULL;
        for(valuesIterator = values; valuesIterator; valuesIterator=valuesIterator->next) {
            const gchar *repoId = valuesIterator->data;
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
        gboolean ret;
        ret = g_output_stream_write_all((GOutputStream *) os, dbJson, strlen(dbJson), NULL, NULL, &internalErr);
        if (ret == FALSE && internalErr) {
            printError("Unable to write into /var/lib/rhsm/productid.js file", internalErr);
        }
        ret = g_output_stream_close((GOutputStream *) os, NULL, &internalErr);
        if (ret == FALSE && internalErr) {
            printError("Unable to close /var/lib/rhsm/productid.js file", internalErr);
        }
    } else {
        printError("Unable to update /var/lib/rhsm/productid.js file", internalErr);
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
 * Function used for comparing two values (strings) in GSList
 * @param value1 pointer at string in GSList
 * @param value2 pointer at new data
 * @return
 */
static int compareRepoIds(gconstpointer str1, gconstpointer str2) {
    return g_strcmp0((char*)str1, (char*)str2);
}

/**
 * Add a repo ID to the list of repo IDs associated to a product ID.  The list deduplicates redundant entries.
 * @param productDb ProductDb to update
 * @param productId ID to associate the repo ID to.
 * @param repoId repo ID to associate
 */
void addRepoId(ProductDb *productDb, const char *productId, const char *repoId) {
    // If the value isn't present, this value will be a NULL and g_slist_prepend will
    // begin a new list
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);

    GSList *existsNode = g_slist_find_custom((GSList *) valueList, repoId, compareRepoIds);
    if (!existsNode) {
        // We prepend so that we don't have to walk the entire linked list, but we
        // have to update record in has table despite linked list already exist, because
        // first item of the linked list is different.
        g_hash_table_insert(
                productDb->repoMap,
                (gpointer) g_strdup(productId),
                g_slist_prepend(valueList, (gpointer) g_strdup(repoId))
        );
    }
}

/**
 * Return list of repo IDs for given product ID
 *
 * @param productDb Pointer at ProductDb
 * @param productId String with representation of product ID
 * @return Return pointer at list of Repo IDs or NULL
 */
GSList *getRepoIds(ProductDb *productDb, const char *productId) {
    return (GSList*)g_hash_table_lookup(productDb->repoMap, productId);
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
        g_slist_free_full(valueList, g_free);
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
    GSList *repoIds = (GSList*)g_hash_table_lookup(productDb->repoMap, productId);
    if (repoIds) {
        GSList *existsNode = g_slist_find_custom((GSList *) repoIds, repoId, compareRepoIds);
        if (existsNode) {
            g_free(existsNode->data);
            GSList *modifiedRepoIds = g_slist_delete_link(repoIds, existsNode);
            // If an item is removed modifiedList will point to a different place than valueList
            if (repoIds == modifiedRepoIds) {
                g_hash_table_replace(productDb->repoMap, (gpointer) g_strdup(productId), modifiedRepoIds);
            }
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
    g_string_append_printf(data, "\t%s: ", (char *) key);

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

