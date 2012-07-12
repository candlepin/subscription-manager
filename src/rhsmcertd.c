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

#include <sys/file.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <wait.h>
#include <glib.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>

#define LOGFILE "/var/log/rhsm/rhsmcertd.log"
#define LOCKFILE "/var/lock/subsys/rhsmcertd"
#define UPDATEFILE "/var/run/rhsm/update"
#define WORKER "/usr/libexec/rhsmcertd-worker"
#define WORKER_NAME WORKER
#define DEFAULT_CERT_INTERVAL_SECONDS 14400	/* 4 hours */
#define DEFAULT_HEAL_INTERVAL_SECONDS 86400	/* 24 hours */
#define BUF_MAX 256
#define RHSM_CONFIG_FILE "/etc/rhsm/rhsm.conf"

#define _(STRING) gettext(STRING)
#define N_(x) x

// XXX set this to false and let the option parsing take over when
// it is working properly
static bool show_debug = true;
static int initial_delay_seconds = 0;
static int cert_interval_seconds = DEFAULT_CERT_INTERVAL_SECONDS;
static int heal_interval_seconds = DEFAULT_HEAL_INTERVAL_SECONDS;

static GOptionEntry entries[] = {
	{"delay-startup", 'd', 0, G_OPTION_ARG_INT, &initial_delay_seconds,
		N_("How long to delay service startup (in seconds)"),
		NULL},
	{"cert-check-interval", 'c', 0, G_OPTION_ARG_INT, &cert_interval_seconds,
		N_("Interval to run cert check (in seconds)"),
		NULL},
	{"heal-interval", 'i', 0, G_OPTION_ARG_INT, &heal_interval_seconds,
		N_("Interval to run healing (in seconds)"),
		NULL},
	{"debug", '\0', 0, G_OPTION_ARG_NONE, &show_debug,
	 N_("Show debug messages"), NULL},
	{NULL}
};

typedef struct _Config {
	int heal_interval_seconds;
	int cert_interval_seconds;
} Config;

void
print_usage ()
{
	printf ("usage: rhsmcertd <certinterval> <healinterval>\n");
}

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
	__attribute__((format(printf, 2, 3)));

void r_log (const char *level, const char *message, ...)
{
	bool use_stdout;
	va_list argp;
	FILE *log_file = fopen (LOGFILE, "a");
	if (!log_file) {
		// redirect message to stdout
		log_file = stdout;
		use_stdout = true;
	}
	va_start (argp, message);

	fprintf (log_file, "%s [%s] ", timestamp(), level);
	vfprintf (log_file, message, argp);
	putc ('\n', log_file);

	if (!use_stdout) {
		fclose (log_file);
	}
}

#define info(msg, ...) r_log ("INFO", msg, ##__VA_ARGS__)
#define warn(msg, ...) r_log ("WARN", msg, ##__VA_ARGS__)
#define error(msg, ...) r_log ("ERROR", msg, ##__VA_ARGS__)
#define debug(msg, ...) if (show_debug) r_log ("DEBUG", msg, ##__VA_ARGS__)

void
log_update (int delay)
{
	time_t update = time (NULL);
	struct tm update_tm = *localtime (&update);
	char buf[BUF_MAX];

	update_tm.tm_sec += delay;
	strftime (buf, BUF_MAX, "%s", &update_tm);

	FILE *updatefile = fopen (UPDATEFILE, "w");
	if (updatefile == NULL) {
		warn ("unable to open %s to write timestamp: %s",
		     UPDATEFILE, strerror (errno));
	} else {
		fprintf (updatefile, "%s", buf);
		fclose (updatefile);
	}
}

int
get_lock ()
{
	int fdlock;

	if ((fdlock = open (LOCKFILE, O_WRONLY | O_CREAT, 0640)) == -1)
		return 1;

	if (flock (fdlock, LOCK_EX | LOCK_NB) == -1)
		return 1;

	return 0;
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
			execl (WORKER, WORKER_NAME, "--autoheal", NULL);
		} else {
			execl (WORKER, WORKER_NAME, NULL);
		}
		_exit (errno);
	}
	waitpid (pid, &status, 0);
	status = WEXITSTATUS (status);
	if (status == 0) {
		info ("certificates updated");
	} else {
		warn ("update failed (%d), retry will occur on next run",
		     status);
	}
	//returning FALSE will unregister the timer, always return TRUE
	return TRUE;
}

static gboolean
initial_cert_check(gboolean heal) {
	cert_check(heal);
	// Return false so that the timer does
	// not run this again.
	return false;
}

int
to_secs (int minutes)
{
	return minutes * 60;
}

void
check_defaults_required (Config * config)
{
	if (config->cert_interval_seconds < 1) {
		debug ("Defaulting cert interval to: %i second(s)",
		     DEFAULT_CERT_INTERVAL_SECONDS);
		config->cert_interval_seconds = DEFAULT_CERT_INTERVAL_SECONDS;
	}

	if (config->heal_interval_seconds < 1) {
		debug ("Defaulting heal interval to: %i second(s)",
		     DEFAULT_HEAL_INTERVAL_SECONDS);
		config->heal_interval_seconds = DEFAULT_HEAL_INTERVAL_SECONDS;
	}
}

Config *
build_config (int cert_frequency, int heal_frequency)
{
	Config *config;
	config = (Config *) malloc (sizeof (config));
	config->cert_interval_seconds = to_secs (cert_frequency);
	config->heal_interval_seconds = to_secs (heal_frequency);
	check_defaults_required (config);
	return config;
}

// FIXME Remove when glib is updated to >= 2.31.0 (see comment below).
int
get_int_from_config_file (GKeyFile * key_file, const char *group,
			  const char *key)
{
	GError *error = NULL;
	// Get the integer value from the config file. If value is 0 (due
	// to any unhandled errors), the default value will be used.
	int value = g_key_file_get_integer (key_file, group, key, &error);
	if (error != NULL && error->code == G_KEY_FILE_ERROR_INVALID_VALUE) {
		printf ("Found non standard value...");
		// There is a bug that was fixed in glib 2.31.0 that deals with
		// handling trailing white space for a config file value. Since
		// we are on a lesser version, we have to deal with it ourselves
		// since by default it returns 0.
		char *str_value =
			g_key_file_get_string (key_file, group, key, NULL);
		g_strchomp (str_value);
		value = atoi (str_value);
	}
	return value;
}

Config *
get_file_configuration (GKeyFile * key_file)
{
	// g_key_file_get_integer defaults to 0 if not found.
	int cert_frequency = get_int_from_config_file (key_file, "rhsmcertd",
						       "certFrequency");
	int heal_frequency = get_int_from_config_file (key_file, "rhsmcertd",
						       "healFrequency");
	return build_config (cert_frequency, heal_frequency);
}

bool
depricated_args_specified(int argc, char *argv[]) {
	if (argc == 1) {
		// No args specified, consider new style args.
		return false;
	}
	int arg_idx;
	for (arg_idx = 1; arg_idx < argc; arg_idx++) {
		
		if (argv[arg_idx] != NULL && argv[arg_idx][0] == '-') {
			return false;
		}
	}
	return true;
}

Config *
get_cli_configuration_depricated (char *argv[])
{
	return build_config (atoi (argv[1]), atoi (argv[2]));
}

Config *
get_cli_configuration (char *argv[])
{
	warn ("Running with old style arguements.");
	return build_config (atoi (argv[1]), atoi (argv[2]));
}

int
main (int argc, char *argv[])
{
	//we open and immediately close the log on startup, in order to check that
	//it's accessible before we daemonize

	Config *config;
	// Allow command line args to override configuration file values.
	if (argc > 1) {
                debug ("Loading configuration from command line");
		if (depricated_args_specified(argc, argv)) {
			if (argc < 3) {
				print_usage ();
				return EXIT_FAILURE;
			}
			debug ("Loading configuration from command line");
			config = get_cli_configuration_depricated (argv);
		} else {
			GError * error;
			GOptionContext *option_context;

			option_context = g_option_context_new ("");
			g_option_context_add_main_entries (option_context, entries, NULL);
			g_option_group_new("rhsmcertd", "", "rhsmcertd", NULL, NULL);
			g_option_context_add_group (option_context,
				g_option_group_new("rhsmcertd", "", "rhsmcertd", NULL, NULL)); 

			if (!g_option_context_parse (option_context, &argc, &argv, &error)) {
				debug ("Loading configuration from command line");
			}
			config = get_cli_configuration (argv);
		}
	} else {
		// Load configuration values from the configuration file.
		debug ("Loading configuration from: %s", RHSM_CONFIG_FILE);
		GKeyFile *key_file = g_key_file_new ();
		if (!g_key_file_load_from_file
		    (key_file, RHSM_CONFIG_FILE, G_KEY_FILE_NONE, NULL)) {
			error ("unable to load configuration file, exiting.");
			return EXIT_FAILURE;
		}
		config = get_file_configuration (key_file);
		g_key_file_free (key_file);
	}

	// Pull values from the config object so that we can free
	// up its resources more reliably in case of error.
	int cert_interval_seconds = config->cert_interval_seconds;
	int heal_interval_seconds = config->heal_interval_seconds;
	free (config);

	daemon (0, 0);
	if (get_lock () != 0) {
		error ("unable to get lock, exiting");
		return EXIT_FAILURE;
	}

	info ("healing check started: interval = %i minute(s)",
	     heal_interval_seconds / 60);
	info ("cert check started: interval = %i minute(s)",
	     cert_interval_seconds / 60);

	// note that we call the function directly first, before assigning a timer
	// to it. Otherwise, it would only get executed when the timer went off, and
	// not at startup.
	//
	// NOTE: We put the initial checks on a timer so that in the case of systemd,
	// we can ensure that the network interfaces are all up before the initial
	// checks are done.
	bool heal = true;
	g_timeout_add (initial_delay_seconds * 1000,
			(GSourceFunc) initial_cert_check,
			(gpointer) heal);
	g_timeout_add (heal_interval_seconds * 1000,
		       (GSourceFunc) cert_check, (gpointer) heal);

	heal = false;
	g_timeout_add (initial_delay_seconds * 1000,
			(GSourceFunc) initial_cert_check,
			(gpointer) heal);
	g_timeout_add (cert_interval_seconds * 1000,
		       (GSourceFunc) cert_check, (gpointer) heal);

	// NB: we only use cert_interval_seconds when calculating the next update
	// time. This works for most users, since the cert_interval aligns with
	// runs of heal_interval (i.e., heal_interval % cert_interval = 0)
	log_update (cert_interval_seconds);
	g_timeout_add (cert_interval_seconds * 1000,
		       (GSourceFunc) log_update,
		       GINT_TO_POINTER (cert_interval_seconds));

	GMainLoop *main_loop = g_main_loop_new (NULL, FALSE);
	g_main_loop_run (main_loop);
	// we will never get past here

	return EXIT_SUCCESS;
}
