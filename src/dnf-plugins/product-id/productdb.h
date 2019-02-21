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

#ifndef PRODUCT_ID_PRODUCTDB_H
#define PRODUCT_ID_PRODUCTDB_H

#include <glib.h>

#define PRODUCTDB_DIR "/var/lib/rhsm/"
#define PRODUCTDB_FILE "/var/lib/rhsm/productid.js"

typedef struct {
    const char *path;
    GHashTable *repoMap;
} ProductDb;

ProductDb * initProductDb();
void freeProductDb(ProductDb *productDb);
void readProductDb(ProductDb *productDb, GError **err);
void writeProductDb(ProductDb *productDb, GError **err);
void addRepoId(ProductDb *productDb, const char *productId, const char *repoId);
GSList *getRepoIds(ProductDb *productDb, const char *productId);
gboolean removeProductId(ProductDb *productDb, const char *productId);
gboolean removeRepoId(ProductDb *productDb, const char *productId, const char *repoId);
gboolean hasProductId(ProductDb *productDb, const char *productId);
gboolean hasRepoId(ProductDb *productDb, const char *productId, const char *repoId);

char *productDbToString(ProductDb *productDb);
#endif //PRODUCT_ID_PRODUCTDB_H
