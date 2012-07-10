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
#define INITIAL_DELAY 10 /* seconds */

typedef struct _Config {
	int heal_interval_seconds;
	int cert_interval_seconds;
} Config;

//TODO: we should be using glib's logging facilities
static FILE *log = NULL;

void
print_usage ()
{
	printf ("usage: rhsmcertd <certinterval> <healinterval>\n");
}

FILE *
get_log ()
{
	FILE *log = fopen (LOGFILE, "at");
	if (log == NULL) {
		printf ("Could not open %s, exiting\n", LOGFILE);
		exit (EXIT_FAILURE);
	}
	return log;
}

char *
ts ()
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
		fprintf (log, "%s: error opening %s to write timestamp: %s\n",
			 ts (), UPDATEFILE, strerror (errno));
		fflush (log);
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
		log = get_log ();
		fprintf (log, "%s: fork failed\n", ts ());
		fflush (log);
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
	log = get_log ();
	if (status == 0) {
		fprintf (log, "%s: certificates updated\n", ts ());
		fflush (log);
	} else {
		fprintf (log,
			 "%s: update failed (%d), retry will occur on next run\n",
			 ts (), status);
		fflush (log);
	}
	fclose (log);
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
	log = get_log ();
	if (config->cert_interval_seconds < 1) {
		fprintf (log, "%s: Defaulting cert interval to: %i second(s)\n",
			 ts (), DEFAULT_CERT_INTERVAL_SECONDS);
		config->cert_interval_seconds = DEFAULT_CERT_INTERVAL_SECONDS;
	}

	if (config->heal_interval_seconds < 1) {
		fprintf (log, "%s: Defaulting heal interval to: %i second(s)\n",
			 ts (), DEFAULT_HEAL_INTERVAL_SECONDS);
		config->heal_interval_seconds = DEFAULT_HEAL_INTERVAL_SECONDS;
	}
	fflush (log);
	fclose (log);
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

Config *
get_cli_configuration (char *argv[])
{
	return build_config (atoi (argv[1]), atoi (argv[2]));
}

int
main (int argc, char *argv[])
{
	//we open and immediately close the log on startup, in order to check that
	//it's accessible before we daemonize
	log = get_log ();
	fclose (log);

	Config *config;
	// Allow command line args to override configuration file values.
	if (argc > 1) {
		if (argc < 3) {
			print_usage ();
			return EXIT_FAILURE;
		}
		log = get_log ();
		fprintf (log, "%s: Loading configuration from command line\n",
			 ts ());
		fflush (log);
		fclose (log);

		config = get_cli_configuration (argv);
	} else {
		// Load configuration values from the configuration file.
		log = get_log ();
		fprintf (log, "%s: Loading configuration from: %s\n", ts (),
			 RHSM_CONFIG_FILE);
		GKeyFile *key_file = g_key_file_new ();
		if (!g_key_file_load_from_file
		    (key_file, RHSM_CONFIG_FILE, G_KEY_FILE_NONE, NULL)) {
			fprintf (log,
				 "%s: ERROR: Unable to load configuration file.",
				 ts ());
			fflush (log);
			fclose (log);
			return EXIT_FAILURE;
		}
		fflush (log);
		fclose (log);
		config = get_file_configuration (key_file);
		g_key_file_free (key_file);
	}

	// Pull values from the config object so that we can free
	// up its resources more reliably in case of error.
	int cert_interval_seconds = config->cert_interval_seconds;
	int heal_interval_seconds = config->heal_interval_seconds;
	free (config);

	log = get_log ();
	fprintf (log, "%s: Cert Frequency: %d seconds\n", ts (),
		 cert_interval_seconds);
	fprintf (log, "%s: Heal Frequency: %d seconds\n", ts (),
		 heal_interval_seconds);
	fflush (log);
	fclose (log);

	daemon (0, 0);
	log = get_log ();
	if (get_lock () != 0) {
		fprintf (log, "%s: unable to get lock, exiting\n", ts ());
		fflush (log);
		fclose (log);	//need to close FD before we return out of main()
		return EXIT_FAILURE;
	}
	fclose (log);

	log = get_log ();
	fprintf (log, "%s: healing check started: interval = %i minute(s)\n",
		 ts (), heal_interval_seconds / 60);
	fprintf (log, "%s: cert check started: interval = %i minute(s)\n",
		 ts (), cert_interval_seconds / 60);
	fflush (log);

	// note that we call the function directly first, before assigning a timer
	// to it. Otherwise, it would only get executed when the timer went off, and
	// not at startup.
	//
	// NOTE: We put the initial checks on a timer so that in the case of systemd,
	// we can ensure that the network interfaces are all up before the initial
	// checks are done.
	bool heal = true;
	g_timeout_add (INITIAL_DELAY * 1000,
			(GSourceFunc) initial_cert_check,
			(gpointer) heal);
	g_timeout_add (heal_interval_seconds * 1000,
		       (GSourceFunc) cert_check, (gpointer) heal);

	heal = false;
	g_timeout_add (INITIAL_DELAY * 1000,
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
