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
#include <glib.h>
#include <stdarg.h>

#include "util.h"

const char *timestamp() {
    time_t tm = time(0);
    char *ts = asctime(localtime (&tm));
    char *p = ts;
    while (*p) {
        p++;
        if (*p == '\n') {
            *p = 0;
        }
    }
    return ts;
}

/*
 * log function. If we can't open the log, attempt to log to stdout
 * rather than fail. opening the log each time is OK since we log so rarely.
 *
 * prototype included here so we can use the printf format checking.
 */
void r_log (const char *level, const char *message, ...)
__attribute__ ((format (printf, 2, 3)));

void r_log (const char *level, const char *message, ...) {
    gboolean use_stdout = FALSE;
    gint ret;
    va_list argp;
    FILE *log_file;
    ret = g_mkdir_with_parents(RHSM_LOG_DIR, 0755);
    if (ret == 0) {
        log_file = fopen(LOGFILE, "a");
        if (!log_file) {
            // redirect message to stdout
            log_file = stdout;
            use_stdout = TRUE;
        }
    } else {
        log_file = stdout;
        use_stdout = TRUE;
    }
    va_start(argp, message);

    fprintf (log_file, "%s [%s] ", timestamp (), level);
    vfprintf (log_file, message, argp);
    putc ('\n', log_file);

    if (!use_stdout) {
        fclose (log_file);
    }

    va_end(argp);
}

void printError(const char *msg, GError *err) {
    error("%s, error: %d: %s", msg, err->code, err->message);
    g_error_free(err);
}
