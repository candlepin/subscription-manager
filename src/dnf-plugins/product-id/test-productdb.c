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
#include <stdio.h>
#include <gio/gio.h>
#include <string.h>

#include "productdb.h"

typedef struct {
    ProductDb *db;
} dbFixture;

void setup(dbFixture *fixture, gconstpointer testData) {
    (void)testData;
    fixture->db = initProductDb();
}

void teardown(dbFixture *fixture, gconstpointer testData) {
    (void)testData;
    freeProductDb(fixture->db);
}

void testAdd(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
}

void testAddDuplicateRepoId(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    addRepoId(db, "69", "rhel");
    addRepoId(db, "69", "jboss");

    gpointer repoIdList = g_hash_table_lookup(db->repoMap, "69");
    guint listLength = g_slist_length((GSList *) repoIdList);
    g_assert_cmpint(2, ==, listLength);
}

void testHasProductId(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    g_assert_true(hasProductId(db, "69"));
    g_assert_false(hasProductId(db, "notPresentProdId"));
}

void testRemoveProductId(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    g_assert_true(hasProductId(db, "69"));
    g_assert_true(removeProductId(db, "69"));
    g_assert_false(hasProductId(db, "69"));

    g_assert_false(removeProductId(db, "0"));
}

void testHasRepoId(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    g_assert_true(hasRepoId(db, "69", "rhel"));
    g_assert_false(hasRepoId(db, "69", "notPresentRepoId"));
    g_assert_false(hasRepoId(db, "notPresentProdId", "rhel"));
}

void testRemoveRepoId(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    addRepoId(db, "69", "jboss");
    g_assert_true(hasRepoId(db, "69", "rhel"));
    g_assert_true(removeRepoId(db, "69", "rhel"));
    g_assert_false(hasRepoId(db, "69", "rhel"));
    g_assert_true(hasRepoId(db, "69", "jboss"));

    g_assert_false(hasRepoId(db, "69", "notPresentRepoId"));
}

void testGetRepoIds(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "testing";
    addRepoId(db, "69", "rhel");
    addRepoId(db, "69", "jboss");
    GSList *list = getRepoIds(db, "69");
    g_assert_cmpint(g_slist_length(list), ==, 2);

}

void testReadMissingFile(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    db->path = "/does/not/exist";
    GError *err = NULL;
    readProductDb(db, &err);
    g_assert_nonnull(err);
    g_error_free(err);
}

void testReadFile(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    GError *err = NULL;

    GFileIOStream *ioStream;

    GFile *testJsonFile = g_file_new_tmp("productidTest-XXXXXX", &ioStream, &err);

    if (err) {
        g_test_fail();
    }

    gchar *testJson = "{'69': ['rhel'], '81': ['jboss', 'ceph']}\n";
    GOutputStream *outStream = g_io_stream_get_output_stream((GIOStream*) ioStream);
    g_output_stream_write_all(outStream, testJson, strlen(testJson), NULL, NULL, &err);
    g_io_stream_close((GIOStream*) ioStream, NULL, &err);
    gchar *path = g_file_get_path(testJsonFile);
    db->path = path;

    readProductDb(db, &err);

    g_assert_true(g_hash_table_contains(db->repoMap, "69"));
    GSList *result = g_hash_table_lookup(db->repoMap, "69");
    g_assert_cmpstr("rhel", ==, result->data);

    g_free(path);
    g_file_delete(testJsonFile, NULL, NULL);
    g_object_unref(ioStream);
    g_object_unref(testJsonFile);
}

void testReadCorruptedFile(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    GError *err = NULL;

    GFileIOStream *ioStream;

    GFile *testJsonFile = g_file_new_tmp("productidTest-XXXXXX", &ioStream, &err);

    if (err) {
        g_test_fail();
    }

    gchar *testJson = "{'69: ['rhel' '81': 'jboss', ceph']}\n";
    GOutputStream *outStream = g_io_stream_get_output_stream((GIOStream*) ioStream);
    g_output_stream_write_all(outStream, testJson, strlen(testJson), NULL, NULL, &err);
    g_io_stream_close((GIOStream*) ioStream, NULL, &err);
    gchar *path = g_file_get_path(testJsonFile);
    db->path = path;

    readProductDb(db, &err);

    g_assert_nonnull(err);
    g_error_free(err);
    g_assert_cmpint(g_hash_table_size(db->repoMap), ==, 0);
}

void testReadFileWrongData(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    GError *err = NULL;

    GFileIOStream *ioStream;

    GFile *testJsonFile = g_file_new_tmp("productidTest-XXXXXX", &ioStream, &err);
    gchar *path = g_file_get_path(testJsonFile);
    db->path = path;

    if (err) {
        g_test_fail();
    }

    GOutputStream *outStream;
    // Value is not array. Right content would be: "{'69': ['rhel']}\n"
    gchar *testJson01 = "{'69': 'rhel'}\n";
    outStream = g_io_stream_get_output_stream((GIOStream*) ioStream);
    g_output_stream_write_all(outStream, testJson01, strlen(testJson01), NULL, NULL, &err);
    readProductDb(db, &err);
    g_assert_nonnull(err);
    g_error_free(err);

    // Key is not string, but it is integer
    gchar *testJson02 = "{69: ['rhel']}\n";
    outStream = g_io_stream_get_output_stream((GIOStream*) ioStream);
    g_output_stream_write_all(outStream, testJson02, strlen(testJson02), NULL, NULL, &err);
    readProductDb(db, &err);
    g_assert_nonnull(err);
    g_error_free(err);

    // Value in array is not string, but it is integer
    gchar *testJson03 = "{'69': [100]}\n";
    outStream = g_io_stream_get_output_stream((GIOStream*) ioStream);
    g_output_stream_write_all(outStream, testJson03, strlen(testJson03), NULL, NULL, &err);
    readProductDb(db, &err);
    g_assert_nonnull(err);
    g_error_free(err);

    g_io_stream_close((GIOStream*) ioStream, NULL, &err);
}

void testWriteFile(dbFixture *fixture, gconstpointer ignored) {
    (void)ignored;
    ProductDb *db = fixture->db;
    GError *err = NULL;

    addRepoId(db, "69", "rhel");
    addRepoId(db, "69", "jboss");

    GFileIOStream *ioStream;
    GFile *testJsonFile = g_file_new_tmp("productidTest-XXXXXX", &ioStream, &err);
    gchar *path = g_file_get_path(testJsonFile);
    db->path = path;

    writeProductDb(db, &err);

    g_free(path);
    g_file_delete(testJsonFile, NULL, NULL);
    g_object_unref(ioStream);
    g_object_unref(testJsonFile);
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set1/test add", dbFixture, NULL, setup, testAdd, teardown);
    g_test_add("/set1/test add duplicate repo id", dbFixture, NULL, setup, testAddDuplicateRepoId, teardown);
    g_test_add("/set1/test has product id", dbFixture, NULL, setup, testHasProductId, teardown);
    g_test_add("/set1/test remove product id", dbFixture, NULL, setup, testRemoveProductId, teardown);
    g_test_add("/set1/test has repo id", dbFixture, NULL, setup, testHasRepoId, teardown);
    g_test_add("/set1/test remove repo id", dbFixture, NULL, setup, testRemoveRepoId, teardown);
    g_test_add("/set1/test get repo ids", dbFixture, NULL, setup, testGetRepoIds, teardown);
    g_test_add("/set1/test read missing file", dbFixture, NULL, setup, testReadMissingFile, teardown);
    g_test_add("/set1/test read corrupted file", dbFixture, NULL, setup, testReadCorruptedFile, teardown);
    g_test_add("/set1/test read wrong data file", dbFixture, NULL, setup, testReadFileWrongData, teardown);
    g_test_add("/set1/test read file", dbFixture, NULL, setup, testReadFile, teardown);
    g_test_add("/set1/test write file", dbFixture, NULL, setup, testWriteFile, teardown);
    return g_test_run();
}
