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
#ifndef PRODUCT_ID_UTIL_H
#define PRODUCT_ID_UTIL_H

#include <glib.h>

#define RHSM_LOG_DIR "/var/log/rhsm/"
#define LOGFILE RHSM_LOG_DIR "productid.log"

#ifndef NDEBUG
#define SHOW_DEBUG TRUE
#else
#define SHOW_DEBUG FALSE
#endif

#define info(msg, ...) r_log ("INFO", msg, ##__VA_ARGS__)
#define warn(msg, ...) r_log ("WARN", msg, ##__VA_ARGS__)
#define error(msg, ...) r_log ("ERROR", msg, ##__VA_ARGS__)
#define debug(msg, ...) if (SHOW_DEBUG) r_log ("DEBUG", msg, ##__VA_ARGS__)

void r_log (const char *level, const char *message, ...);

void printError(const char *msg, GError *err);

#endif //PRODUCT_ID_UTIL_H
