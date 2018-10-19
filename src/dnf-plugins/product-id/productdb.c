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

void readProductDb(ProductDb *productDb, GError *err) {

}

void writeProductDb(ProductDb *productDb, GError *err) {

}

void addRepoId(ProductDb *productDb, const char *productId, const char *repoId, GError *err) {
    gpointer valueList = g_hash_table_lookup(productDb->repoMap, productId);
    // We prepend so that we don't have to walk the entire linked list
    g_hash_table_insert(
        productDb->repoMap,
        (gpointer) productId,
        g_list_prepend(valueList, (gpointer) repoId)
    );

}

void removeRepoId(ProductDb *productDb, const char *productId, const char *repoId, GError *err) {

}

void hasRepoId(ProductDb *productDb, const char *productId, const char *repoId, GError *err) {

};

void printTable(gpointer key, gpointer value, gpointer data) {
    g_string_printf(data, "\t%s:", (char *) key);

    GSList *iterator = NULL;
    for (iterator = value; iterator; iterator = iterator->next) {
        g_string_printf(data, "%s ", (char *) iterator->data);
    }
    g_string_append(data, "\n");
}

GString *toString(ProductDb *productDb) {
    GString *out = g_string_new("");
    g_string_printf(out, "Path: %s\n", productDb->path);
    g_string_append(out, "Contents:\n");

    g_hash_table_foreach(productDb->repoMap, (GHFunc) printTable, out);
    return out;
}

