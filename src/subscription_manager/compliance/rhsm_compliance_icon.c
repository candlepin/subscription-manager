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
#include <libintl.h>
#include <locale.h>

#include <glib.h>
#include <gtk/gtk.h>
#include <libnotify/notify.h>
#include <dbus/dbus-glib.h>

#define ONE_DAY 86400
#define _(STRING)   gettext(STRING)
#define N_(x)   x

static int check_period = ONE_DAY;
static bool debug = false;
static char *force_icon = NULL;

#define NAME_TO_CLAIM "com.redhat.subscription-manager.ComplianceIcon"

static GOptionEntry entries[] =
{
	{"check-period", 'c', 0, G_OPTION_ARG_INT, &check_period,
		N_("How often to check for validity (in seconds)"), NULL},
	{"debug", 'd', 0, G_OPTION_ARG_NONE, &debug,
		N_("Show debug messages"), NULL},
	{"force-icon", 'f', 0, G_OPTION_ARG_STRING, &force_icon,
		N_("Force display of the icon (expired or warning)"),
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
	RHSM_EXPIRED,
	RHSM_WARNING,
	RHN_CLASSIC
} ComplianceType;

/* prototypes */

static void destroy_icon(Compliance*);
static void display_icon(Compliance*, ComplianceType);
static void alter_icon(Compliance*, ComplianceType);
static void run_smg(Compliance*);
static void icon_clicked(GtkStatusIcon*, Compliance*);
static void icon_right_clicked(GtkStatusIcon*, guint, guint, Compliance*);
static void remind_me_later_clicked(NotifyNotification*, gchar*, Compliance*);
static void manage_subs_clicked(NotifyNotification*, gchar*, Compliance*);
static void do_nothing_logger(const gchar*, GLogLevelFlags, const gchar*, gpointer);
static void compliance_changed_cb(NotifyNotification*, gint, Compliance*);
static bool check_compliance(Compliance*);
static DBusGProxy* add_signal_listener(Compliance*);
static ComplianceType check_compliance_over_dbus();
static ComplianceType create_compliancetype(int);


static ComplianceType
create_compliancetype(int status)
{
	switch (status) {
		case 0:
			return RHSM_COMPLIANT;
		case 1:
			return RHSM_EXPIRED;
		case 2:
			return RHSM_WARNING;
		case 3:
			return RHN_CLASSIC;
		default:
			// we don't know this one, better to play it safe
			return RHSM_EXPIRED;
	}
}

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
		tooltip = _("Invalid or Missing Entitlement Certificates");
		notification_title = _("Invalid or Missing Entitlement Certificates");
		notification_body = _("This system is missing one or more "
			"valid entitlement certificates.");

	} else {
		tooltip = _("Some of the system's subscriptions are about to expire");
		notification_title =
			_("This System's Subscriptions Are About to Expire");
		notification_body = _("One or more of this system's "
			"subscriptions are about to expire.");
	}

	compliance->icon = gtk_status_icon_new_from_icon_name("subscription-manager");
	gtk_status_icon_set_tooltip(compliance->icon, tooltip);
	g_signal_connect(compliance->icon, "activate",
			 G_CALLBACK(icon_clicked), compliance);
	g_signal_connect(compliance->icon, "popup-menu",
			 G_CALLBACK(icon_right_clicked), compliance);
	compliance->is_visible = true;

	compliance->notification = notify_notification_new_with_status_icon(
		notification_title, notification_body, "subscription-manager",
		compliance->icon);
	
	notify_notification_add_action(compliance->notification,
				       "remind-me-later",
				       _("Remind Me Later"),
				       (NotifyActionCallback)
				       remind_me_later_clicked,
				       compliance, NULL);
	notify_notification_add_action(compliance->notification,
				       "manage-subscriptions",
				       _("Manage My Subscriptions..."),
				       (NotifyActionCallback)
				       manage_subs_clicked,
				       compliance, NULL);

	notify_notification_show(compliance->notification, NULL);
}

static void
alter_icon(Compliance *compliance, ComplianceType ct) {
	if ((ct != RHN_CLASSIC) && 
	(ct != RHSM_COMPLIANT)) {
		display_icon(compliance, ct);
	} else {
		destroy_icon(compliance);
	}
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
	return create_compliancetype(is_compliant);
}

static bool
check_compliance(Compliance *compliance)
{
	ComplianceType compliance_type;
	g_debug("Running compliance check");

	if (force_icon) {
		g_debug("Forcing display of icon (simulated invalidity)");
		if (g_str_equal(force_icon, "expired")) {
			compliance_type = RHSM_EXPIRED;
		} else if (g_str_equal(force_icon, "warning")) {
			compliance_type = RHSM_WARNING;
		} else {
			g_print(N_("Unknown argument to force-icon: %s\n"),
				force_icon);
			exit(1);
		}
	} else {
		compliance_type = check_compliance_over_dbus();
	}

	alter_icon(compliance, compliance_type);

	return true;
}


static void
compliance_changed_cb(NotifyNotification *notification G_GNUC_UNUSED,
	   gint status, Compliance* compliance)
{
	g_debug("in callback, received value: %i", status);
	alter_icon(compliance, create_compliancetype(status));
}

static DBusGProxy* 
add_signal_listener(Compliance *compliance)
{
	DBusGConnection *connection;
	GError *error;
	DBusGProxy *proxy;

	error = NULL;
	connection = dbus_g_bus_get(DBUS_BUS_SYSTEM, &error);
	if (connection == NULL) {
		g_printerr(N_("Failed to open connection to bus: %s\n"),
		      error->message);
		g_error_free(error);
		exit(1);
	}

	proxy = dbus_g_proxy_new_for_name(connection,
		     "com.redhat.SubscriptionManager",
		     "/Compliance",
		     "com.redhat.SubscriptionManager.Compliance");

	dbus_g_proxy_add_signal(proxy, "compliancechanged", G_TYPE_INT, G_TYPE_INVALID);
	dbus_g_proxy_connect_signal(proxy, "compliancechanged", G_CALLBACK(compliance_changed_cb), compliance, NULL);
	return proxy;

}

int
main(int argc, char **argv)
{
	setlocale(LC_ALL, "");
	bindtextdomain("rhsm", "/usr/share/locale");
	textdomain("rhsm");
	GError *error = NULL;
	GOptionContext *context;
	DBusGProxy *proxy;
	DBusGConnection *connection;
	Compliance compliance;
	compliance.is_visible = false;
	guint32 result;

	context = g_option_context_new ("rhsm compliance icon");
	g_option_context_add_main_entries (context, entries, NULL);
	g_option_context_add_group (context, gtk_get_option_group (TRUE));
	
	if (!g_option_context_parse (context, &argc, &argv, &error)) {
		g_print (N_("option parsing failed: %s\n"), error->message);
		return 1;
	}

	g_option_context_free (context);

	if (!debug) {
		g_log_set_handler(NULL, G_LOG_LEVEL_DEBUG, do_nothing_logger,
				  NULL);
	}

	gtk_init(&argc, &argv);


	connection = dbus_g_bus_get(DBUS_BUS_SESSION, &error);
	if (connection == NULL) {
		g_printerr(N_("Failed to open connection to bus: %s\n"),
			error->message);
		g_error_free(error);
		exit(1);
	}

	proxy = dbus_g_proxy_new_for_name(connection,
			"org.freedesktop.DBus",
			"/org/freedesktop/DBus",
			"org.freedesktop.DBus");
	error = NULL;
	if (!dbus_g_proxy_call (proxy,
		"RequestName",
		&error,
		G_TYPE_STRING, NAME_TO_CLAIM,
		G_TYPE_UINT,  0,
		G_TYPE_INVALID,
		G_TYPE_UINT,   &result,
		G_TYPE_INVALID)) {
			g_printerr("Couldn't acquire name: %s\n", error->message);
			exit(1);
	}

	if (result != DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER) {
		if (error != NULL) {
			g_warning ("Failed to acquire %s: %s",
				NAME_TO_CLAIM, error->message);
				g_error_free (error);
		}
		else {
			g_warning ("Failed to acquire %s", NAME_TO_CLAIM);
		}
		g_debug("rhsm-compliance-icon is already running. exiting.");
		return 0;
	}


	notify_init("rhsm-compliance-icon");

	check_compliance(&compliance);
	//convert sec to msec before passing in
	g_timeout_add(check_period * 1000, (GSourceFunc) check_compliance,
			      &compliance);

	proxy = add_signal_listener(&compliance);
	gtk_main();

	g_debug("past main");
	g_object_unref(proxy);
	return 0;
}

