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
#define WORKER_NAME "/usr/libexec/rhsmcertd-worker"
#define DEFAULT_CERT_INTERVAL 14400	/* 4 hours */
#define DEFAULT_HEAL_INTERVAL 86400	/* 24 hours */
#define BUF_MAX 256

//TODO: we should be using glib's logging facilities
static FILE *log = NULL;
GMainLoop *main_loop = NULL;

void
printUsage ()
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
logUpdate (int delay)
{
	time_t update = time (NULL);
	struct tm update_tm = *localtime (&update);
	char buf[BUF_MAX];

	update_tm.tm_min += delay;
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

int
main (int argc, char *argv[])
{
	//we open and immediately close the log on startup, in order to check that
	//it's accessible before we daemonize
	log = get_log ();
	fclose (log);

	if (argc < 3) {
		printUsage ();
		return EXIT_FAILURE;
	}

	int cert_interval = atoi (argv[1]) * 60;
	int heal_interval = atoi (argv[2]) * 60;

	daemon (0, 0);
	log = get_log ();
	if (get_lock () != 0) {
		fprintf (log, "%s: unable to get lock, exiting\n", ts ());
		fflush (log);
		fclose (log);	//need to close FD before we return out of main()
		return EXIT_FAILURE;
	}
	fclose (log);

	if (cert_interval < 1) {
		cert_interval = DEFAULT_CERT_INTERVAL;
	}
	if (heal_interval < 1) {
		heal_interval = DEFAULT_HEAL_INTERVAL;
	}

	log = get_log ();
	fprintf (log, "%s: healing check started: interval = %i\n", ts (),
		 heal_interval / 60);
	fprintf (log, "%s: cert check started: interval = %i\n", ts (),
		 cert_interval / 60);
	fflush (log);

	//note that we call the function directly first, before assigning a timer
	//to it. Otherwise, it would only get executed when the timer went off, and
	//not at startup.

	bool heal = true;
	cert_check (heal);
	g_timeout_add (heal_interval * 1000, (GSourceFunc) cert_check,
		       (gpointer) heal);

	heal = false;
	cert_check (heal);
	g_timeout_add (cert_interval * 1000, (GSourceFunc) cert_check,
		       (gpointer) heal);

	logUpdate (cert_interval);
	g_timeout_add (cert_interval * 1000, (GSourceFunc) logUpdate,
		       GINT_TO_POINTER (cert_interval));

	main_loop = g_main_loop_new (NULL, FALSE);
	g_main_loop_run (main_loop);
	//we will never get past here

	return EXIT_SUCCESS;
}
