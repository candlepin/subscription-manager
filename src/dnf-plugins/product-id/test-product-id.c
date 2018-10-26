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

#include "product-id.h"

typedef struct {
    _PluginHandle *handle;
} handleFixture;

void setup(handleFixture *fixture, gconstpointer testData) {
}

void teardown(handleFixture *fixture, gconstpointer testData) {
}

void testAdd(handleFixture *fixture, gconstpointer ignored) {
}

int main(int argc, char **argv) {
    g_test_init(&argc, &argv, NULL);
    g_test_add("/set2/test add", handleFixture, NULL, setup, testAdd, teardown);
    return g_test_run();
}