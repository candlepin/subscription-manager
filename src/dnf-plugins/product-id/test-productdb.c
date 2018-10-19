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

#include <glib.h>
#include "productdb.h"

typedef struct {
    ProductDb *db;
} dbFixture;

void setup(dbFixture *fixture, gconstpointer testData) {
    fixture->db = initProductDb();
}

void teardown(dbFixture *fixture, gconstpointer testData) {
    freeProductDb(fixture->db);
}

void testAdd(dbFixture *fixture, gconstpointer ignored) {

}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set1/test add", dbFixture, NULL, setup, testAdd, teardown);
    return g_test_run();
}