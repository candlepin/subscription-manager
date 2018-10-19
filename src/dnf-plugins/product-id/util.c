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
    va_list argp;
    FILE *log_file = fopen (LOGFILE, "a");
    if (!log_file) {
        // redirect message to stdout
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


