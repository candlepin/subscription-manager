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
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <wait.h>
#include <glib.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <libintl.h>
#include <locale.h>

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

static gboolean show_debug = FALSE;
static gboolean run_now = FALSE;
static gint initial_delay_seconds = 60;	// One minute delay
static gint arg_cert_interval_minutes = -1;
static gint arg_heal_interval_minutes = -1;

static GOptionEntry entries[] = {
	{"wait", 'w', 0, G_OPTION_ARG_INT, &initial_delay_seconds,
	 N_("How long to delay service startup (in seconds)"),
	 "SECONDS"},
	{"cert-interval", 'c', 0, G_OPTION_ARG_INT, &arg_cert_interval_minutes,
	 N_("Interval to run cert check (in minutes)"),
	 "MINUTES"},
	{"heal-interval", 'i', 0, G_OPTION_ARG_INT, &arg_heal_interval_minutes,
	 N_("Interval to run healing (in minutes)"),
	 "MINUTES"},
	{"now", 'n', 0, G_OPTION_ARG_NONE, &run_now,
	 N_("Run the initial checks immediatly, with no delay."),
	 NULL},
	{"debug", 'd', 0, G_OPTION_ARG_NONE, &show_debug,
	 N_("Show debug messages"), NULL},
	{NULL}
};

typedef struct _Config {
	int heal_interval_seconds;
	int cert_interval_seconds;
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
	bool use_stdout;
	va_list argp;
	FILE *log_file = fopen (LOGFILE, "a");
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

/* Handle program signals */
void
signal_handler(int signo) {
	if (signo == SIGTERM) {
		info ("rhsmcertd is shutting down...");
		signal (signo, SIG_DFL);
		raise (signo);
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

	char *action = "Cert Check";
	if (heal) {
		action = "Healing";
	}

	if (status == 0) {
		info ("(%s) Certificates updated.", action);
	} else {
		warn ("(%s) Update failed (%d), retry will occur on next run.",
		      action, status);
	}
	//returning FALSE will unregister the timer, always return TRUE
	return TRUE;
}

static gboolean
initial_cert_check (gboolean heal)
{
	cert_check (heal);
	// Return false so that the timer does
	// not run this again.
	return false;
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

GOptionContext *
get_option_context ()
{
	GOptionContext *option_context;
	option_context = g_option_context_new ("");
	g_option_context_set_ignore_unknown_options (option_context, true);
	g_option_context_add_main_entries (option_context, entries, NULL);
	g_option_group_new ("rhsmcertd", "", "rhsmcertd", NULL, NULL);
	g_option_context_add_group (option_context,
				    g_option_group_new ("rhsmcertd", "",
							"rhsmcertd", NULL,
							NULL));
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
}

void
key_file_init_config (Config * config, GKeyFile * key_file)
{
	// g_key_file_get_integer defaults to 0 if not found.
	int cert_frequency = get_int_from_config_file (key_file, "rhsmcertd",
						       "certFrequency");
	if (cert_frequency > 0) {
		config->cert_interval_seconds = cert_frequency * 60;
	}

	int heal_frequency = get_int_from_config_file (key_file, "rhsmcertd",
						       "healFrequency");
	if (heal_frequency > 0) {
		config->heal_interval_seconds = heal_frequency * 60;
	}
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
	// Let the caller know if opt parser found arg values
	// for the intervals.
	return arg_cert_interval_minutes != -1
		|| arg_heal_interval_minutes != -1;
}

Config *
get_config (int argc, char *argv[])
{
	Config *config;
	config = (Config *) malloc (sizeof (config));

	// Set the default values
	config->cert_interval_seconds = DEFAULT_CERT_INTERVAL_SECONDS;
	config->heal_interval_seconds = DEFAULT_HEAL_INTERVAL_SECONDS;

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

	// Set any values provided from the options parser.
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
}

int
main (int argc, char *argv[])
{
	if (signal(SIGTERM, signal_handler) == SIG_ERR) {
		warn ("Unable to catch SIGTERM\n");
	}
	setlocale (LC_ALL, "");
	bindtextdomain ("rhsm", "/usr/share/locale");
	textdomain ("rhsm");
	parse_cli_args (&argc, argv);

	Config *config = get_config (argc, argv);

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

	info ("Starting rhsmcertd...");
	info ("Healing interval: %.1f minute(s) [%d second(s)]",
	      heal_interval_seconds / 60.0, heal_interval_seconds);
	info ("Cert check interval: %.1f minute(s) [%d second(s)]",
	      cert_interval_seconds / 60.0, cert_interval_seconds);

	// note that we call the function directly first, before assigning a timer
	// to it. Otherwise, it would only get executed when the timer went off, and
	// not at startup.
	//
	// NOTE: We put the initial checks on a timer so that in the case of systemd,
	// we can ensure that the network interfaces are all up before the initial
	// checks are done.
	if (run_now) {
		info ("Initial checks will be run now!");
		initial_delay_seconds = 0;
	} else {
		info ("Waiting %d second(s) [%.1f minute(s)] before running updates.",
				initial_delay_seconds, initial_delay_seconds / 60.0);
	}
	bool heal = true;
	g_timeout_add (initial_delay_seconds * 1000,
		       (GSourceFunc) initial_cert_check, (gpointer) heal);
	g_timeout_add (heal_interval_seconds * 1000,
		       (GSourceFunc) cert_check, (gpointer) heal);

	heal = false;
	g_timeout_add (initial_delay_seconds * 1000,
		       (GSourceFunc) initial_cert_check, (gpointer) heal);
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
