/*
* Copyright (c) 2010 Red Hat, Inc.
*
* Authors: Jeff Ortel <jortel@redhat.com>
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
#define _GNU_SOURCE

#include <linux/version.h>
#include <sys/file.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stdlib.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <wait.h>
#include <glib.h>
#include <glib-unix.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <libintl.h>
#include <locale.h>

typedef enum {
    LOG_LEVEL_ERROR = 0,
    LOG_LEVEL_WARNING = 1,
    LOG_LEVEL_INFO = 2,
    LOG_LEVEL_DEBUG = 3
} LOG_LEVEL;

#define LOGDIR "/var/log/rhsm"
#define LOGFILE LOGDIR"/rhsmcertd.log"
#define LOCKFILE "/var/lock/subsys/rhsmcertd"
#define NEXT_CERT_UPDATE_FILE "/run/rhsm/next_cert_check_update"
#define NEXT_AUTO_ATTACH_UPDATE_FILE "/run/rhsm/next_auto_attach_update"
#define NEXT_AUTO_REGISTER_UPDATE_FILE "/run/rhsm/next_auto_register_update"
#define WORKER LIBEXECDIR"/rhsmcertd-worker"
#define WORKER_NAME WORKER
#define PACKAGE_PROFILE_UPLOADER LIBEXECDIR"/rhsm-package-profile-uploader"
#define INITIAL_DELAY_SECONDS 120
#define DEFAULT_AUTO_REG_INTERVAL_SECONDS 3600 /* 1 hour */
#define DEFAULT_CERT_INTERVAL_SECONDS 14400    /* 4 hours */
#define DEFAULT_HEAL_INTERVAL_SECONDS 86400    /* 24 hours */
#define DEFAULT_SPLAY_ENABLED true
#define DEFAULT_AUTO_REGISTRATION false
#define DEFAULT_LOG_LEVEL LOG_LEVEL_INFO
#define DEFAULT_LOG_LEVEL_NAME "INFO"
#define BUF_MAX 256
#define RHSM_CONFIG_FILE "/etc/rhsm/rhsm.conf"

#define _(STRING) gettext(STRING)
#define N_(x) x
#define CONFIG_KEY_NOT_FOUND (0)


#if !GLIB_CHECK_VERSION(2, 58, 0)
#define G_SOURCE_FUNC(f) ((GSourceFunc) (void (*)(void)) (f))
#endif

#if defined(__linux)
# if LINUX_VERSION_CODE >= KERNEL_VERSION(3,17,0)
#  ifdef HAVE_LINUX_GETRANDOM
#   include <linux/random.h>
#  else
#   include <sys/syscall.h>
#   undef getrandom
#   define getrandom(dst,s,flags) syscall(SYS_getrandom, (void*)dst, (size_t)s, (unsigned int)flags)
#  endif
# else
#  include <sys/time.h>
#  define FAKE_RANDOM
# endif
#endif

static LOG_LEVEL log_level = DEFAULT_LOG_LEVEL;
static gboolean show_debug = FALSE;
static gboolean run_now = FALSE;
static gint arg_cert_interval_minutes = -1;
static gint arg_heal_interval_minutes = -1;
static gint arg_reg_interval_minutes = -1;
static gboolean arg_no_splay = FALSE;
static gboolean arg_auto_registration = FALSE;
static int fd_lock = -1;

struct CertCheckData {
    int interval_seconds;
    bool heal;
    char *next_update_file;
};

static GOptionEntry entries[] = {
    /* marked deprecated as of 02-19-2013, needs to be removed...? */
    {"cert-interval", 0, 0, G_OPTION_ARG_INT, &arg_heal_interval_minutes,
     N_("deprecated, see --cert-check-interval"),
     "MINUTES"},
    {"cert-check-interval", 'c', 0, G_OPTION_ARG_INT, &arg_cert_interval_minutes,
     N_("interval to run cert check (in minutes)"),
     "MINUTES"},
    /* marked deprecated as of 11-16-2012, needs to be removed...? */
    {"heal-interval", 0, 0, G_OPTION_ARG_INT, &arg_heal_interval_minutes,
     N_("deprecated, see --auto-attach-interval"),
     "MINUTES"},
    {"auto-attach-interval", 'i', 0, G_OPTION_ARG_INT, &arg_heal_interval_minutes,
     N_("interval to run auto-attach (in minutes)"),
     "MINUTES"},
    {"auto-registration-interval", 'r', 0, G_OPTION_ARG_INT, &arg_reg_interval_minutes,
            N_("interval to run auto-registration (in minutes)"),
            "MINUTES"},
    {"now", 'n', 0, G_OPTION_ARG_NONE, &run_now,
     N_("run the initial checks immediately, with no delay"),
     NULL},
    {"debug", 'd', 0, G_OPTION_ARG_NONE, &show_debug,
     N_("show debug messages"), NULL},
    {"no-splay", 's', 0, G_OPTION_ARG_NONE, &arg_no_splay,
     N_("do not add an offset to the initial checks."),
     NULL},
    {"auto-registration", 'a', 0, G_OPTION_ARG_NONE, &arg_auto_registration,
            N_("try to perform auto-registration."),
            NULL},
    {NULL}
};

typedef struct _Config {
    int auto_reg_interval_seconds;
    int heal_interval_seconds;
    int cert_interval_seconds;
    bool splay;
    bool auto_registration;
} Config;

const char *
timestamp ()
{
    time_t tm = time (0);
    char *ts = asctime (localtime (&tm));
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

void
r_log (const char *level, const char *message, ...)
{
    bool use_stdout = false;
    va_list argp;
    FILE *log_file = NULL;
    struct stat log_dir_stat;

    /* When log directory does not exist, then try to create this directory */
    if (stat(LOGDIR, &log_dir_stat) != 0) {
        mkdir(LOGDIR, 0755);
    }
    log_file = fopen (LOGFILE, "a");
    if (!log_file) {
        // redirect message to stdout
        log_file = stdout;
        use_stdout = true;
    }
    va_start (argp, message);

    fprintf (log_file, "%s [%s] ", timestamp (), level);
    vfprintf (log_file, message, argp);
    putc ('\n', log_file);

    if (!use_stdout) {
        fclose (log_file);
    }

    va_end(argp);
}

#define error(msg, ...) if (log_level >= LOG_LEVEL_ERROR) r_log ("ERROR", msg, ##__VA_ARGS__)
#define warn(msg, ...) if (log_level >= LOG_LEVEL_WARNING) r_log ("WARN", msg, ##__VA_ARGS__)
#define info(msg, ...) if (log_level >= LOG_LEVEL_INFO) r_log ("INFO", msg, ##__VA_ARGS__)
#define debug(msg, ...) if (log_level >= LOG_LEVEL_DEBUG) r_log ("DEBUG", msg, ##__VA_ARGS__)

static gboolean
log_update (int delay, char *path_to_file)
{
    time_t update = time (NULL);
    struct tm update_tm = *localtime (&update);
    char buf[BUF_MAX];

    update_tm.tm_sec += delay;
    strftime (buf, BUF_MAX, "%s", &update_tm);

    FILE *updatefile = fopen (path_to_file, "w");
    if (updatefile == NULL) {
        warn ("unable to open %s to write timestamp: %s",
              path_to_file, strerror (errno));
    } else {
        fprintf (updatefile, "%s", buf);
        fclose (updatefile);
    }
    return TRUE;
}

static gboolean
log_update_from_cert_data(gpointer data)
{
    struct CertCheckData *cert_data = data;
    return log_update(cert_data->interval_seconds, cert_data->next_update_file);
}

long long gen_random(long long max) {
    // This function will return a random number between [0, max]
    // Find the nearest number to RAND_MAX that is divisible by the given max
    // The rand function will generate a random number in the range [0, RAND_MAX]
    // This function will constrain the output of rand to the range [0, max] while ensuring the output has no bias.
    // See http://www.azillionmonkeys.com/qed/random.html for an explanation of why this is necessary
    long long true_max = max + (long long) 1;
    // 1 must be type cast to a long int to avoid integer overflow on certain systems
    long long rand_max = (long long) RAND_MAX;
    long long range_max = ((rand_max + (long long) 1) / true_max) * true_max;
    long long random_num = -1;
    do {
        random_num = rand();
    } while(!(random_num < range_max));
    return random_num % true_max;
}

/**
 * Try to run Python script package-profile-uploader. This script tries to upload DNF profile
 * to server, when server supports profile. New process is spawned in blocking way.
 * Note: this script is spawned with --force-upload. Thus report_package_config configuration
 * option is ignored and this configuration option should be checked before using this approach.
 * @return Return true, when uploading was successful. Otherwise, return false.
 */
static gboolean
upload_package_profile ()
{
    gboolean ret;
    const char * argv[] = {PACKAGE_PROFILE_UPLOADER, "--force-upload", NULL};
    gchar *standard_output = NULL;
    gchar *standard_error = NULL;
    gint wait_status = 0;
    GError *error = NULL;

    debug ("Spawning new process of uploading package profile...");

    // Following function will block until process is finished. Other signals
    // are queued and will be processed, when following process is finished.
    // It means other signals (SIGTERM) are blocked too. systemd can resolve
    // this issue. When sending SIGTERM does not terminate daemon, then it
    // sends SIGKILL signal after some timeout.
    ret = g_spawn_sync(
            "/",                // Working directory
            (gchar**)argv,      // Executable with arguments
            NULL,               // List of environments is read from parent process
            G_SPAWN_DEFAULT,    // Default flags
            NULL,               // No function running before spawning process
            NULL,               // No argument for such function is needed as well
            &standard_output,   // stdout if any
            &standard_error,    // stderr if any
            &wait_status,       // status if any
            &error);            // Error if any

    debug ("Spawning of uploading package profile finished: %d", ret);

    // Print stdout/stderr to log file only in the case, when stdout/stderr are not empty strings
    if (standard_output != NULL && standard_output[0] != 0) {
        debug ("stdout of uploading package profile: %s", standard_output);
        g_free(standard_output);
        standard_output = NULL;
    }
    if (standard_error != NULL && standard_error[0] != 0) {
        debug ("stderr of uploading package profile: %s", standard_error);
        g_free(standard_error);
        standard_error = NULL;
    }

    // Error is usually not NULL, when it wasn't possible to span child process
    // for some reason (e.g. file does not exist)
    if (error != NULL) {
        error ("Spawning of child process (uploading profile) failed: %s", error->message);
        g_error_free(error);
        error = NULL;
        return false;
    }

#if GLIB_MAJOR_VERSION >= 2 && GLIB_MINOR_VERSION >= 70
    // Following function is available since Fedora 35 (not RHEL7, RHEL8, RHEL9)
    ret = g_spawn_check_wait_status(wait_status, &error);
#else
    // Following function is available on RHEL7, RHEL8, RHEL9 (not RHEL6),
    // and it was deprecated on Fedora 35
    ret = g_spawn_check_exit_status(wait_status, &error);
#endif

    if (error != NULL) {
        error ("Child process exited abnormally: %s", error->message);
        g_error_free(error);
        error = NULL;
        return false;
    }

    info ("Uploading of package profile performed successfully");

    return ret;
}

/**
 * Callback function for SIGUSR1 signal
 * @return Always returns G_SOURCE_CONTINUE
 */
gboolean
sigusr1_callback(void) {
    debug ("Received SIGUSR1 signal");
    upload_package_profile();
    // Return this value to signal that this callback function
    // should remain in main loop
    return G_SOURCE_CONTINUE;
}

/**
 * Callback function for SIGTERM signal
 * @return Always returns G_SOURCE_REMOVE
 */
gboolean
sigterm_callback(void) {
    int ret;
    info ("rhsmcertd is shutting down...");
    /* Close lock file and release lock on this file */
    if (fd_lock != -1) {
        /* Truncate lock file to zero value (delete PID before unlinking),
         * because unlinking could fail for several reasons. Thus, it should not
         * contain at least non-valid value of PID. */
        ret = ftruncate(fd_lock, 0);
        if (ret == -1) {
            warn ("Unable to truncate lock file: %s, %s", LOCKFILE, strerror (errno));
        }
        close(fd_lock);
        fd_lock = -1;
    }
    /* Try to delete lock file */
    ret = unlink(LOCKFILE);
    if (ret == -1) {
        error ("Unable to unlink lock file: %s, %s", LOCKFILE, strerror(errno));
    }
    // Set handler to SIGTERM to default
    signal (SIGTERM, SIG_DFL);
    // Raise the signal once again to terminate this process
    raise (SIGTERM);
    return G_SOURCE_REMOVE;
}

/**
 * Try to lock file /var/lock/subsys/rhsmcertd and write current PID to this file
 * @return Return 0, when it was possible lock file and write PID to lock file.
 *         Otherwise, return non-zero value.
 */
int
get_lock ()
{
    fd_lock = open (LOCKFILE, O_WRONLY | O_CREAT, 0640);
    int ret = 0;

    if (fd_lock == -1) {
        error ("Unable to open file: %s, %s", LOCKFILE, strerror(errno));
        ret = 1;
    } else {
        if (flock (fd_lock, LOCK_EX | LOCK_NB) == -1) {
            debug ("Unable to lock file: %s, %s", LOCKFILE, strerror(errno));
            close (fd_lock);
            fd_lock = -1;
            ret = 2;
        } else {
            pid_t pid = getpid ();
            debug ("Writing PID: %d to lock file: %s", pid, LOCKFILE);
            /* Lock file in /var/lock should use HDB UUCP lock file format. More details could be found here:
             * https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s09.html */
            int num = dprintf (fd_lock, "%10d\n", pid);
            if (num < 0) {
                error ("Unable to write PID to lock file: %s, %s", LOCKFILE, strerror (errno));
                ret = 3;
            }
        }
    }

    return ret;
}

static gboolean
auto_register(gpointer data)
{
    (void)data;
    int status = 0;

    int pid = fork ();
    if (pid < 0) {
        error ("fork failed");
        exit (EXIT_FAILURE);
    }
    if (pid == 0) {
        debug ("(Auto-registration) executing: %s --auto-register", WORKER);
        execl (WORKER, WORKER_NAME, "--auto-register", NULL);
    }

    waitpid (pid, &status, 0);
    status = WEXITSTATUS (status);

    if (status == 0) {
        info ("(Auto-registration) performed successfully.");
        return false;
    } else {
        warn ("(Auto-registration) failed (%d)", status);
        return false;
    }
}

static gboolean
cert_check (gboolean heal)
{
    int status = 0;

    int pid = fork ();
    if (pid < 0) {
        error ("fork failed");
        exit (EXIT_FAILURE);
    }
    if (pid == 0) {
        if (heal) {
            debug ("(Auto-attach) executing: %s --autoheal", WORKER);
            execl (WORKER, WORKER_NAME, "--autoheal", NULL);
        } else {
            debug ("(Cert check) executing: %s", WORKER);
            execl (WORKER, WORKER_NAME, NULL);
        }
        _exit (errno);
    }
    waitpid (pid, &status, 0);
    status = WEXITSTATUS (status);

    char *action = "Cert Check";
    if (heal) {
        action = "Auto-attach";
    }

    if (status == 0) {
        info ("(%s) Certificates updated.", action);
    } else {
        warn ("(%s) Update failed (%d), retry will occur on next run.",
              action, status);
    }
    // Returning FALSE will unregister the timer, always return TRUE
    return TRUE;
}

static gboolean
initial_cert_check (gpointer data)
{
    struct CertCheckData *cert_data = data;
    cert_check (cert_data->heal);
    // Add the timeout to begin waiting on interval but offset by the initial
    // delay.
    g_timeout_add (cert_data->interval_seconds * 1000,
        (GSourceFunc) cert_check, (gpointer) cert_data->heal);
    g_timeout_add (cert_data->interval_seconds * 1000,
           (GSourceFunc) log_update_from_cert_data,
           (gpointer) cert_data);
    // Update timestamp
    log_update(cert_data->interval_seconds, cert_data->next_update_file);
    // Return false so that the timer does
    // not run this again.
    return false;
}

// FIXME Remove when glib is updated to >= 2.31.0 (see comment below).
// NOTE: 0 is used for error, so this can't return 0. For our cases, that
//       ok
int
get_int_from_config_file (GKeyFile * key_file, const char *group, const char *key)
{
    GError *error = NULL;
    int value = g_key_file_get_integer (key_file, group, key, &error);
    // If key does not exist in config file, return CONFIG_KEY_NOT_FOUND, aka 0
    if (error != NULL && error->code == G_KEY_FILE_ERROR_KEY_NOT_FOUND) {
        debug ("Key %s does not exists in the group %s", key, group);
        value = CONFIG_KEY_NOT_FOUND;
    }
    // Get the integer value from the config file. If value is 0 (due
    // to any unhandled errors), the default value will be used.
    else if (error != NULL && error->code == G_KEY_FILE_ERROR_INVALID_VALUE) {
        // There is a bug that was fixed in glib 2.31.0 that deals with
        // handling trailing white space for a config file value. Since
        // we are on a lesser version, we have to deal with it ourselves
        // since by default it returns 0.
        char *str_value = g_key_file_get_string (key_file, group, key, NULL);
        if(str_value != NULL) {
            g_strchomp(str_value);
            value = atoi(str_value);
            free(str_value);
        }
    }
    return value;
}

// Similar to the above,
bool
get_bool_from_config_file (GKeyFile *key_file, const char *group, const char *key, bool default_value)
{
    GError *error = NULL;
    bool value = g_key_file_get_boolean (key_file, group, key, &error);
    // If key does not exist in config file, return the default_value given
    if (error != NULL && (error->code == G_KEY_FILE_ERROR_KEY_NOT_FOUND || error->code == G_KEY_FILE_ERROR_INVALID_VALUE)) {
        debug ("Key %s does not exists in the group %s. Using default value: %d", key, group, default_value);
        value = default_value;
    }
    return value;
}

gchar *
get_string_from_config_file (GKeyFile *key_file, const char *group, const char *key)
{
    GError *error = NULL;
    gchar *value = g_key_file_get_string (key_file, group, key, &error);
    if (error != NULL) {
        if (error->code == G_KEY_FILE_ERROR_GROUP_NOT_FOUND) {
            debug ("Group %s does not exist", group);
        } else if (error->code == G_KEY_FILE_ERROR_KEY_NOT_FOUND) {
            debug ("Key %s does not exists in the group %s", key, group);
        }
    }
    return value;
}

GOptionContext *
get_option_context ()
{
    GOptionContext *option_context;
    option_context = g_option_context_new ("");
    g_option_context_set_ignore_unknown_options (option_context, true);
    g_option_context_add_main_entries (option_context, entries, NULL);
    return option_context;
}

void print_argument_error (const char *message, ...);

void
print_argument_error (const char *message, ...)
{
    va_list argp;

    va_start (argp, message);
    vprintf(message, argp);
    printf(N_("For more information run: rhsmcertd --help\n"));
    va_end(argp);
}

void
set_log_level (const gchar *conf_log_level, const char *conf_option_name)
{
    bool using_default_log_level = false;
    if (g_strcmp0(conf_log_level, "DEBUG") == 0) {
        log_level = LOG_LEVEL_DEBUG;
    } else if (g_strcmp0(conf_log_level, "INFO") == 0) {
        log_level = LOG_LEVEL_INFO;
    } else if (g_strcmp0(conf_log_level, "WARN") == 0) {
        log_level = LOG_LEVEL_WARNING;
    } else if (g_strcmp0(conf_log_level, "ERROR") == 0) {
        log_level = LOG_LEVEL_ERROR;
    } else {
        warn ("Unsupported log level: %s of configuration option: %s in file: %s",
              conf_log_level, conf_option_name, RHSM_CONFIG_FILE);
        log_level = DEFAULT_LOG_LEVEL;
        using_default_log_level = true;
    }
    if (using_default_log_level == false) {
        debug ("Using log level: %s of configuration option: %s in file: %s",
               conf_log_level, conf_option_name, RHSM_CONFIG_FILE);
    } else {
        info ("Using default log level: %s", DEFAULT_LOG_LEVEL_NAME);
    }
}

void
key_file_init_config (Config * config, GKeyFile * key_file)
{
    // non-existent entries will return 0
    int cert_frequency = get_int_from_config_file (key_file, "rhsmcertd",
                               "certFrequency");
    int cert_check_interval = get_int_from_config_file (key_file, "rhsmcertd",
                               "certCheckInterval");

    // unfound or invalid entries return CONFIG_KEY_NOT_FOUND, (aka, 0)
    // so let it fall back to the default
    if (cert_check_interval > 0) {
        config->cert_interval_seconds = cert_check_interval * 60;
    }
    else if (cert_frequency > 0) {
        config->cert_interval_seconds = cert_frequency * 60;
    }

    int heal_frequency = get_int_from_config_file (key_file, "rhsmcertd",
                               "healFrequency");
    int auto_attach_interval = get_int_from_config_file (key_file, "rhsmcertd",
                               "autoAttachInterval");
    if (auto_attach_interval > 0) {
        config->heal_interval_seconds = auto_attach_interval * 60;
    }
    else if (heal_frequency > 0) {
        config->heal_interval_seconds = heal_frequency * 60;
    }

    bool splay_enabled = get_bool_from_config_file (key_file, "rhsmcertd",
                            "splay", DEFAULT_SPLAY_ENABLED);
    config->splay = splay_enabled;

    int auto_reg_interval = get_int_from_config_file (
            key_file,
            "rhsmcertd",
            "auto_registration_interval"
    );
    if (auto_reg_interval > 0) {
        config->auto_reg_interval_seconds = auto_reg_interval * 60;
    }

    bool auto_registration_enabled = get_bool_from_config_file (
            key_file,
            "rhsmcertd",
            "auto_registration",
            DEFAULT_AUTO_REGISTRATION
            );
    config->auto_registration = auto_registration_enabled;

    gchar *default_log_level = get_string_from_config_file(
            key_file,
            "logging",
            "default_log_level"
    );

    gchar *rhsmcertd_log_level = get_string_from_config_file(
            key_file,
            "logging",
            "rhsmcertd"
    );

    if (show_debug) {
        // When --debug CLI option is used, then ignore configuration options related to logging, and
        // print debug log about it
        if (rhsmcertd_log_level != NULL) {
            debug("Ignoring logging.rhsmcertd configuration option, because --debug CLI option was used");
        } else if (default_log_level != NULL) {
            debug("Ignoring logging.default_log_level configuration option, because --debug CLI option was used");
        }
    } else {
        if (rhsmcertd_log_level != NULL) {
            set_log_level(rhsmcertd_log_level, "logging.rhsmcertd");
        } else if (default_log_level != NULL) {
            set_log_level(default_log_level, "logging.default_log_level");
        }
    }

    g_free(default_log_level);
    g_free(rhsmcertd_log_level);
}

void
deprecated_arg_init_config (Config * config, int argc, char *argv[])
{
    if (argc != 3) {
        error ("Wrong number of arguments specified.");
        print_argument_error(N_("Wrong number of arguments specified.\n"));
        free (config);
        exit (EXIT_FAILURE);
    }

    config->cert_interval_seconds = atoi (argv[1]) * 60;
    config->heal_interval_seconds = atoi (argv[2]) * 60;
}

bool
opt_parse_init_config (Config * config)
{
    // Load the values from the options into the config
    if (arg_cert_interval_minutes != -1) {
        config->cert_interval_seconds = arg_cert_interval_minutes * 60;
    }

    if (arg_heal_interval_minutes != -1) {
        config->heal_interval_seconds = arg_heal_interval_minutes * 60;
    }

    if (arg_reg_interval_minutes != -1) {
        config->auto_reg_interval_seconds = arg_reg_interval_minutes * 60;
    }

    if (arg_no_splay) {
        config->splay = FALSE;
    }

    if (arg_auto_registration) {
        config->auto_registration = TRUE;
    }
    // Let the caller know if opt parser found arg values
    // for the intervals.
    return arg_cert_interval_minutes != -1
        || arg_heal_interval_minutes != -1
        || arg_reg_interval_minutes != -1
        || arg_no_splay != FALSE
        || arg_auto_registration != FALSE;
}

Config *
get_config (int argc, char *argv[])
{
    Config *config;
    config = malloc (sizeof (Config));

    // Set the default values
    config->auto_reg_interval_seconds = DEFAULT_AUTO_REG_INTERVAL_SECONDS;
    config->cert_interval_seconds = DEFAULT_CERT_INTERVAL_SECONDS;
    config->heal_interval_seconds = DEFAULT_HEAL_INTERVAL_SECONDS;
    config->splay = DEFAULT_SPLAY_ENABLED;
    config->auto_registration = DEFAULT_AUTO_REGISTRATION;

    // Load configuration values from the configuration file
    // which, if defined, will overwrite the current defaults.
    debug ("Loading configuration from: %s", RHSM_CONFIG_FILE);
    GKeyFile *key_file = g_key_file_new ();
    if (!g_key_file_load_from_file
        (key_file, RHSM_CONFIG_FILE, G_KEY_FILE_NONE, NULL)) {
        warn ("Unable to read configuration file values, ignoring.");
    } else {
        key_file_init_config (config, key_file);
    }
    g_key_file_free (key_file);

    // Set any values provided from the option parser.
    bool options_provided = opt_parse_init_config (config);

    // If there are any args that were ignored by opt_parse, we assume
    // that old school args were used.
    if (argc > 1) {
        if (options_provided) {
            // New style args were used, assume error.
            // We do not support both at once, other than
            // debug and wait.
            print_argument_error (N_("Invalid argument specified.\n"));
            exit (EXIT_FAILURE);
        } else {
            // Old style args are being used.
            warn ("Deprecated CLI arguments are being used.");
            printf (N_
                ("WARN: Deprecated CLI arguments are being used.\n"));
            deprecated_arg_init_config (config, argc, argv);
        }
    }

    return config;
}

void
parse_cli_args (int *argc, char *argv[])
{
    GError *error = NULL;
    GOptionContext *option_context = get_option_context ();
    if (!g_option_context_parse (option_context, argc, &argv, &error)) {
        error ("Invalid option: %s", error->message);
        print_argument_error (N_("Invalid option: %s\n"), error->message);
        g_option_context_free (option_context);
        exit (EXIT_FAILURE);
    }

    g_option_context_free (option_context);

    // Since we are ignoring unknown args to support
    // old style arguments, we need to ensure that
    // there are no opt style args tagging along.
    int i;
    for (i = 1; i < *argc; i++) {
        if (argv[i][0] == '-') {
            error ("Invalid argument specified: %s\n", argv[i]);
            print_argument_error (N_("Invalid argument specified: %s\n"),
                argv[i]);
            exit (EXIT_FAILURE);
        }
    }

    // When --debug CLI option is set, then set log_level to DEBUG now, because
    // 1. we want to override configuration options from rhsm.conf
    // 2. we want to see debug messages during parsing of configuration file
    if (show_debug) {
        log_level = LOG_LEVEL_DEBUG;
    }
}

int
main (int argc, char *argv[])
{
    setlocale (LC_ALL, "");
    bindtextdomain ("rhsm", "/usr/share/locale");
    textdomain ("rhsm");
    parse_cli_args (&argc, argv);

    Config *config = get_config (argc, argv);

    // Pull values from the config object so that we can free
    // up its resources more reliably in case of error.
    int auto_reg_interval_seconds = config->auto_reg_interval_seconds;
    int cert_interval_seconds = config->cert_interval_seconds;
    int heal_interval_seconds = config->heal_interval_seconds;
    bool splay_enabled = config->splay;
    bool auto_reg_enabled = config->auto_registration;
    free (config);

    if (daemon (0, 0) == -1)
        return EXIT_FAILURE;

    if (get_lock () != 0) {
        error ("Unable to get lock, exiting");
        return EXIT_FAILURE;
    }

    // NOTE: it is important to create callback function for signals after calling daemon()
    // Create main context for main loop
    GMainContext *main_context;
    main_context = g_main_context_default ();

    // Create sources for handling SIGUSR1 and SIGTERM signal
    GSource *sigusr1_source, *sigterm_source;
    sigusr1_source = g_unix_signal_source_new (SIGUSR1);
    sigterm_source = g_unix_signal_source_new (SIGTERM);

    // Attach callback function to the source. We don't pass any data to callback functions
    g_source_set_callback (sigusr1_source, G_SOURCE_FUNC(sigusr1_callback), NULL, NULL);
    g_source_set_callback (sigterm_source, G_SOURCE_FUNC(sigterm_callback), NULL, NULL);

    // Attach signal sources to the main_context
    g_source_attach (sigusr1_source, main_context);
    g_source_attach (sigterm_source, main_context);

    info ("Starting rhsmcertd...");
    if (auto_reg_enabled) {
        info ("Auto-registration interval: %.1f minutes [%d seconds]",
              auto_reg_interval_seconds / 60.0, auto_reg_interval_seconds);
    } else {
        debug ("Auto-registration disabled");
    }
    info ("Auto-attach interval: %.1f minutes [%d seconds]",
          heal_interval_seconds / 60.0, heal_interval_seconds);
    info ("Cert check interval: %.1f minutes [%d seconds]",
          cert_interval_seconds / 60.0, cert_interval_seconds);

    // note that we call the function directly first, before assigning a timer
    // to it. Otherwise, it would only get executed when the timer went off, and
    // not at startup.
    //
    // NOTE: We put the initial checks on a timer so that in the case of systemd,
    // we can ensure that the network interfaces are all up before the initial
    // checks are done.
    int auto_attach_initial_delay = 0;
    int cert_check_initial_delay = 0;
    if (run_now) {
        info ("Initial checks will be run now!");
    } else {
        int auto_attach_offset = 0;
        int cert_check_offset = 0;
        if (splay_enabled == true) {
            unsigned long int seed;
#ifndef FAKE_RANDOM
            // Grab a seed using the getrandom syscall
            int getrandom_num_bytes = 0;
            do {
                getrandom_num_bytes = getrandom(&seed, sizeof(unsigned long int), 0);
            } while (getrandom_num_bytes < sizeof(unsigned long int));
#else
            // When SYS_getrandom nor getrandom() are not defined, then try to set
            // initial seed using directly from /dev/urandom
            int num_of_items_read = 0;
            bool urandom_opened = false;
            FILE *urandom = fopen("/dev/urandom", "r");
            if (urandom != NULL) {
                urandom_opened = true;
                num_of_items_read = fread (&seed, sizeof(unsigned long int), 1, urandom);
                if (num_of_items_read != 1) {
                    warn ("Unable to read random data from /dev/urandom, using fake random seed");
                }
                fclose (urandom);
                urandom = NULL;
            } else {
                warn ("Unable to open /dev/urandom: %s, using fake random seed.",
                      strerror (errno));
            }
            if (!urandom_opened || num_of_items_read != 1) {
                // When /dev/urandom does not exists or it is not possible data from
                // this file, then try to generate something at least a little bit random.
                // No need to be concerned, because we do not use it for cryptography.
                struct timeval tv;
                gettimeofday (&tv, NULL);
                seed = tv.tv_sec % tv.tv_usec;
            }
#endif
            srand((unsigned int) seed);
            auto_attach_offset = gen_random(heal_interval_seconds);
            cert_check_offset = gen_random(cert_interval_seconds);
        }

        auto_attach_initial_delay = INITIAL_DELAY_SECONDS + auto_attach_offset;
        info ("Waiting %.1f minutes plus %d splay seconds [%d seconds total] before performing first auto-attach.",
                INITIAL_DELAY_SECONDS / 60.0, auto_attach_offset, auto_attach_initial_delay);
        cert_check_initial_delay = INITIAL_DELAY_SECONDS + cert_check_offset;
        info ("Waiting %.1f minutes plus %d splay seconds [%d seconds total] before performing first cert check.",
                INITIAL_DELAY_SECONDS / 60.0, cert_check_offset, cert_check_initial_delay);
    }

    struct CertCheckData auto_register_data;
    auto_register_data.interval_seconds = auto_reg_interval_seconds;
    auto_register_data.heal = false;
    auto_register_data.next_update_file = NEXT_AUTO_REGISTER_UPDATE_FILE;

    struct CertCheckData cert_check_data;
    cert_check_data.interval_seconds = cert_interval_seconds;
    cert_check_data.heal = false;
    cert_check_data.next_update_file = NEXT_CERT_UPDATE_FILE;

    struct CertCheckData auto_attach_data;
    auto_attach_data.interval_seconds = heal_interval_seconds;
    auto_attach_data.heal = true;
    auto_attach_data.next_update_file = NEXT_AUTO_ATTACH_UPDATE_FILE;

    if (auto_reg_enabled) {
        auto_register((gpointer) &auto_register_data);
    }
    g_timeout_add (cert_check_initial_delay * 1000,
               (GSourceFunc) initial_cert_check, (gpointer) &cert_check_data);
    g_timeout_add (auto_attach_initial_delay * 1000,
               (GSourceFunc) initial_cert_check, (gpointer) &auto_attach_data);

    // NB: we only use cert_interval_seconds when calculating the next update
    // time. This works for most users, since the cert_interval aligns with
    // runs of heal_interval (i.e., heal_interval % cert_interval = 0)
    if (auto_reg_enabled) {
        log_update (0, NEXT_AUTO_REGISTER_UPDATE_FILE);
    }
    log_update (cert_check_initial_delay, NEXT_CERT_UPDATE_FILE);
    log_update (auto_attach_initial_delay, NEXT_AUTO_ATTACH_UPDATE_FILE);

    GMainLoop *main_loop = g_main_loop_new (main_context, FALSE);
    g_main_loop_run (main_loop);
    // we will never get past here

    return EXIT_SUCCESS;
}
