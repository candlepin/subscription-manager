/*
* Copyright (c) 2010 Red Hat, Inc.
*
* Authors: James Bowes <jbowes@redhat.com>
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
*
* rhsm-compliance-icon - display an icon in the systray if the system is
*                        non-compliant.
*/

#include <stdbool.h>
#include <stdlib.h>

#include <glib.h>
#include <gtk/gtk.h>
#include <unique/unique.h>
#include <libnotify/notify.h>
#include <dbus/dbus-glib.h>

#define ONE_DAY 86400

static int check_period = ONE_DAY;
static bool debug = false;
static char *force_icon = NULL;

static GOptionEntry entries[] =
{
	{"check-period", 'c', 0, G_OPTION_ARG_INT, &check_period,
		"How often to check for compliance (in seconds)", NULL},
	{"debug", 'd', 0, G_OPTION_ARG_NONE, &debug,
		"Show debug messages", NULL},
	{"force-icon", 'f', 0, G_OPTION_ARG_STRING, &force_icon,
		"Force display of the compliance icon (expired or warning)",
		"TYPE"},
	{NULL}
};

typedef struct _Compliance {
	bool is_visible;
	GtkStatusIcon *icon;
	NotifyNotification *notification;
} Compliance;

typedef enum _ComplianceType {
	RHSM_COMPLIANT,
	RHSM_WARNING,
	RHSM_EXPIRED
} ComplianceType;

static void
destroy_icon(Compliance *compliance)
{
	if (!compliance->is_visible) {
		return;
	}
	gtk_status_icon_set_visible(compliance->icon, false);
	g_object_unref(compliance->icon);
	compliance->is_visible = false;

	notify_notification_close(compliance->notification, NULL);
	g_object_unref(compliance->notification);
}

static void
run_smg(Compliance *compliance)
{
	g_spawn_command_line_async("subscription-manager-gui", NULL);
	destroy_icon(compliance);
}

static void
icon_clicked(GtkStatusIcon *icon G_GNUC_UNUSED, Compliance *compliance)
{
	g_debug("icon click detected");
	run_smg(compliance);
}

static void
icon_right_clicked(GtkStatusIcon *icon G_GNUC_UNUSED,
		   guint button G_GNUC_UNUSED,
		   guint activate_time G_GNUC_UNUSED,
		   Compliance *compliance)
{
	g_debug("icon right click detected");
	run_smg(compliance);
}


static void
remind_me_later_clicked(NotifyNotification *notification G_GNUC_UNUSED,
			gchar *action G_GNUC_UNUSED,
			Compliance *compliance)
{
	g_debug("Remind me later clicked");
	destroy_icon(compliance);
}

static void
manage_subs_clicked(NotifyNotification *notification G_GNUC_UNUSED,
		    gchar *action G_GNUC_UNUSED,
		    Compliance *compliance)
{
	g_debug("Manage my subscriptions clicked");
	run_smg(compliance);
}

static void
display_icon(Compliance *compliance, ComplianceType compliance_type)
{
	static char *tooltip;
	static char *notification_title;
	static char *notification_body;

	if (compliance->is_visible) {
		g_debug("Icon already visible");
		return;
	}

	if (compliance_type == RHSM_EXPIRED) {
		tooltip = "This system is non-compliant";
		notification_title = "This System is Non-Compliant";
		notification_body = "This system is missing one or more "
			"subscriptions required for compliance with your "
			"software license agreements.";

	} else {
		tooltip ="This system's subscriptions are about to expire";
		notification_title =
			"This System's Subscriptions Are About to Expire";
		notification_body = "One or more of this system's "
			"subscriptions are about to expire. These "
			"subscriptions are required for compliance with your "
			"software license agreements.";
	}

	compliance->icon = gtk_status_icon_new_from_icon_name("subsmgr");
	gtk_status_icon_set_tooltip(compliance->icon, tooltip);
	g_signal_connect(compliance->icon, "activate",
			 G_CALLBACK(icon_clicked), compliance);
	g_signal_connect(compliance->icon, "popup-menu",
			 G_CALLBACK(icon_right_clicked), compliance);
	compliance->is_visible = true;

	compliance->notification = notify_notification_new_with_status_icon(
		notification_title, notification_body, "subsmgr",
		compliance->icon);
	
	notify_notification_add_action(compliance->notification,
				       "remind-me-later",
				       "Remind Me Later",
				       (NotifyActionCallback)
				       remind_me_later_clicked,
				       compliance, NULL);
	notify_notification_add_action(compliance->notification,
				       "manage-subscriptions",
				       "Manage My Subscriptions...",
				       (NotifyActionCallback)
				       manage_subs_clicked,
				       compliance, NULL);

	notify_notification_show(compliance->notification, NULL);
}

static void
do_nothing_logger(const gchar *log_domain G_GNUC_UNUSED,
		  GLogLevelFlags log_level G_GNUC_UNUSED,
		  const gchar *message G_GNUC_UNUSED,
		  gpointer data G_GNUC_UNUSED)
{
	/* really, do nothing */
}

static ComplianceType
check_compliance_over_dbus()
{
	DBusGConnection *connection;
	GError *error;
	DBusGProxy *proxy;
	int is_compliant;
  
  	error = NULL;
  	connection = dbus_g_bus_get(DBUS_BUS_SYSTEM, &error);
	if (connection == NULL) {
      		g_printerr("Failed to open connection to bus: %s\n",
			   error->message);
		g_error_free(error);
		exit(1);
	}

  	proxy = dbus_g_proxy_new_for_name(connection,
					  "com.redhat.SubscriptionManager",
					  "/Compliance",
					  "com.redhat.SubscriptionManager.Compliance");

  	error = NULL;
  	if (!dbus_g_proxy_call(proxy, "check_compliance", &error,
			       G_TYPE_INVALID, G_TYPE_INT, &is_compliant,
			       G_TYPE_INVALID)) {
        	g_printerr("Error: %s\n", error->message);
      		g_error_free(error);
      		exit(1);
	}

	g_object_unref(proxy);
	dbus_g_connection_unref(connection);

	switch (is_compliant) {
		case 0:
			return RHSM_EXPIRED;
		case 1:
			return RHSM_COMPLIANT;
		case 2:
			return RHSM_WARNING;
		default:
			// we don't know this one, better to play it safe
			return RHSM_EXPIRED;
	}
}

static bool
check_compliance(Compliance *compliance)
{
	ComplianceType compliance_type;
	g_debug("Running compliance check");

	if (force_icon) {
		g_debug("Forcing display of icon (simulated non-compliance)");
		if (g_str_equal(force_icon, "expired")) {
			compliance_type = RHSM_EXPIRED;
		} else if (g_str_equal(force_icon, "warning")) {
			compliance_type = RHSM_WARNING;
		} else {
			g_print("Unknown argument to force-icon: %s\n",
				force_icon);
			exit(1);
		}
	} else {
		compliance_type = check_compliance_over_dbus();
	}

	if (compliance_type != RHSM_COMPLIANT) {
		display_icon(compliance, compliance_type);
	}

	return true;
}

int
main(int argc, char **argv)
{
	GError *error = NULL;
	GOptionContext *context;
	UniqueApp *app;
	Compliance compliance;
	compliance.is_visible = false;

	context = g_option_context_new ("rhsm compliance icon");
	/* XXX: need to set translation domain */
	g_option_context_add_main_entries (context, entries, NULL);
	g_option_context_add_group (context, gtk_get_option_group (TRUE));
	
	if (!g_option_context_parse (context, &argc, &argv, &error)) {
		g_print ("option parsing failed: %s\n", error->message);
      		return 1;
	}

	g_option_context_free (context);

	if (!debug) {
		g_log_set_handler(NULL, G_LOG_LEVEL_DEBUG, do_nothing_logger,
				  NULL);
	}

	gtk_init(&argc, &argv);

	app = unique_app_new ("com.redhat.subscription-manager.ComplianceIcon",
			      NULL);

	if (unique_app_is_running(app)) {
		g_debug("rhsm-compliance-icon is already running. exiting.");
		g_object_unref(app);
		return 0;
	}

	notify_init("rhsm-compliance-icon");

	check_compliance(&compliance);
	g_timeout_add_seconds(check_period, (GSourceFunc) check_compliance,
			      &compliance);
	gtk_main();

	g_object_unref(app);
	return 0;
}

