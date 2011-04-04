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
* rhsm-icon - display an icon in the systray if the system has invalid
* 	      entitlements
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

#define NAME_TO_CLAIM "com.redhat.subscription-manager.Icon"

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

typedef struct _Context {
	bool is_visible;
	GtkStatusIcon *icon;
	NotifyNotification *notification;
} Context;

typedef enum _StatusType {
	RHSM_VALID,
	RHSM_EXPIRED,
	RHSM_WARNING,
	RHN_CLASSIC
} StatusType;

/* prototypes */

static void destroy_icon(Context*);
static void display_icon(Context*, StatusType);
static void alter_icon(Context*, StatusType);
static void run_smg(Context*);
static void icon_clicked(GtkStatusIcon*, Context*);
static void icon_right_clicked(GtkStatusIcon*, guint, guint, Context*);
static void remind_me_later_clicked(NotifyNotification*, gchar*, Context*);
static void manage_subs_clicked(NotifyNotification*, gchar*, Context*);
static void do_nothing_logger(const gchar*, GLogLevelFlags, const gchar*, gpointer);
static void status_changed_cb(NotifyNotification*, gint, Context*);
static bool check_status(Context*);
static DBusGProxy* add_signal_listener(Context*);
static StatusType check_status_over_dbus();
static StatusType create_status_type(int);


static StatusType
create_status_type(int status)
{
	switch (status) {
		case 0:
			return RHSM_VALID;
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
destroy_icon(Context *context)
{
	if (!context->is_visible) {
		return;
	}
	gtk_status_icon_set_visible(context->icon, false);
	g_object_unref(context->icon);
	context->is_visible = false;

	notify_notification_close(context->notification, NULL);
	g_object_unref(context->notification);
}

static void
run_smg(Context *context)
{
	g_spawn_command_line_async("subscription-manager-gui", NULL);
	destroy_icon(context);
}

static void
icon_clicked(GtkStatusIcon *icon G_GNUC_UNUSED, Context *context)
{
	g_debug("icon click detected");
	run_smg(context);
}

static void
icon_right_clicked(GtkStatusIcon *icon G_GNUC_UNUSED,
		   guint button G_GNUC_UNUSED,
		   guint activate_time G_GNUC_UNUSED,
		   Context *context)
{
	g_debug("icon right click detected");
	run_smg(context);
}

static void
remind_me_later_clicked(NotifyNotification *notification G_GNUC_UNUSED,
			gchar *action G_GNUC_UNUSED,
			Context *context)
{
	g_debug("Remind me later clicked");
	destroy_icon(context);
}

static void
manage_subs_clicked(NotifyNotification *notification G_GNUC_UNUSED,
		    gchar *action G_GNUC_UNUSED,
		    Context *context)
{
	g_debug("Manage my subscriptions clicked");
	run_smg(context);
}

static void
display_icon(Context *context, StatusType status_type)
{
	static char *tooltip;
	static char *notification_title;
	static char *notification_body;

	if (context->is_visible) {
		g_debug("Icon already visible");
		return;
	}

	if (status_type == RHSM_EXPIRED) {
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

	context->icon = gtk_status_icon_new_from_icon_name("subscription-manager");
	gtk_status_icon_set_tooltip(context->icon, tooltip);
	g_signal_connect(context->icon, "activate",
			 G_CALLBACK(icon_clicked), context);
	g_signal_connect(context->icon, "popup-menu",
			 G_CALLBACK(icon_right_clicked), context);
	context->is_visible = true;

	context->notification = notify_notification_new_with_status_icon(
		notification_title, notification_body, "subscription-manager",
		context->icon);
	
	notify_notification_add_action(context->notification,
				       "remind-me-later",
				       _("Remind Me Later"),
				       (NotifyActionCallback)
				       remind_me_later_clicked,
				       context, NULL);
	notify_notification_add_action(context->notification,
				       "manage-subscriptions",
				       _("Manage My Subscriptions..."),
				       (NotifyActionCallback)
				       manage_subs_clicked,
				       context, NULL);

	notify_notification_show(context->notification, NULL);
}

static void
alter_icon(Context *context, StatusType status_type) {
	if ((status_type != RHN_CLASSIC) && (status_type != RHSM_VALID)) {
		display_icon(context, status_type);
	} else {
		destroy_icon(context);
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

static StatusType
check_status_over_dbus()
{
	DBusGConnection *connection;
	GError *error;
	DBusGProxy *proxy;
	int status;
  
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
					  "/EntitlementStatus",
					  "com.redhat.SubscriptionManager.EntitlementStatus");

	error = NULL;
	if (!dbus_g_proxy_call(proxy, "check_status", &error,
			       G_TYPE_INVALID, G_TYPE_INT, &status,
			       G_TYPE_INVALID)) {
		g_printerr("Error: %s\n", error->message);
		g_error_free(error);
		exit(1);
	}

	g_object_unref(proxy);
	dbus_g_connection_unref(connection);
	return create_status_type(status);
}

static bool
check_status(Context *context)
{
	StatusType status_type;
	g_debug("Running entitlement status check");

	if (force_icon) {
		g_debug("Forcing display of icon (simulated invalidity)");
		if (g_str_equal(force_icon, "expired")) {
			status_type = RHSM_EXPIRED;
		} else if (g_str_equal(force_icon, "warning")) {
			status_type = RHSM_WARNING;
		} else {
			g_print(N_("Unknown argument to force-icon: %s\n"),
				force_icon);
			exit(1);
		}
	} else {
		status_type = check_status_over_dbus();
	}

	alter_icon(context, status_type);

	return true;
}


static void
status_changed_cb(NotifyNotification *notification G_GNUC_UNUSED,
	   gint status, Context *context)
{
	g_debug("in callback, received value: %i", status);
	alter_icon(context, create_status_type(status));
}

static DBusGProxy* 
add_signal_listener(Context *context)
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
		     "/EntitlementStatus",
		     "com.redhat.SubscriptionManager.EntitlementStatus");

	dbus_g_proxy_add_signal(proxy, "status_changed", G_TYPE_INT,
				G_TYPE_INVALID);
	dbus_g_proxy_connect_signal(proxy, "status_changed",
				    G_CALLBACK(status_changed_cb), context,
				    NULL);
	return proxy;

}

int
main(int argc, char **argv)
{
	setlocale(LC_ALL, "");
	bindtextdomain("rhsm", "/usr/share/locale");
	textdomain("rhsm");
	GError *error = NULL;
	GOptionContext *option_context;
	DBusGProxy *proxy;
	DBusGConnection *connection;
	Context context;
	context.is_visible = false;
	guint32 result;

	option_context = g_option_context_new ("rhsm icon");
	g_option_context_add_main_entries (option_context, entries, NULL);
	g_option_context_add_group (option_context,
				    gtk_get_option_group (TRUE));
	
	if (!g_option_context_parse (option_context, &argc, &argv, &error)) {
		g_print (N_("option parsing failed: %s\n"), error->message);
		return 1;
	}

	g_option_context_free (option_context);

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
		g_debug("rhsm-icon is already running. exiting.");
		return 0;
	}


	notify_init("rhsm-icon");

	check_status(&context);
	//convert sec to msec before passing in
	g_timeout_add(check_period * 1000, (GSourceFunc) check_status,
			      &context);

	proxy = add_signal_listener(&context);
	gtk_main();

	g_debug("past main");
	g_object_unref(proxy);
	return 0;
}

