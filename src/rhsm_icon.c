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
#include <gconf/gconf-client.h>
#include <gtk/gtk.h>
#include <libnotify/notify.h>
#include <dbus/dbus-glib.h>

#define ONE_DAY 86400
#define INITIAL_DELAY 240
#define _(STRING)   gettext(STRING)
#define N_(x)   x

static int check_period = ONE_DAY;
static bool debug = false;
static char *force_icon = NULL;
static bool check_immediately = false;

#define NAME_TO_CLAIM "com.redhat.subscription-manager.Icon"

static GOptionEntry entries[] = {
	{"check-period", 'c', 0, G_OPTION_ARG_INT, &check_period,
	 N_("How often to check for validity (in seconds)"), NULL},
	{"debug", 'd', 0, G_OPTION_ARG_NONE, &debug,
	 N_("Show debug messages"), NULL},
	{"force-icon", 'f', 0, G_OPTION_ARG_STRING, &force_icon,
	 N_("Force display of the icon (expired, partial or warning)"),
	 "TYPE"},
	{"check-immediately", 'i', 0, G_OPTION_ARG_NONE, &check_immediately,
	 N_("Run the first status check right away"), NULL},
	{NULL}
};

typedef struct _Context {
	bool is_visible;
	bool show_registration;
	GtkStatusIcon *icon;
	NotifyNotification *notification;
	DBusGProxy *entitlement_status_proxy;
	gulong handler_id;
} Context;

typedef enum _StatusType {
	RHSM_VALID,
	RHSM_EXPIRED,
	RHSM_WARNING,
	RHN_CLASSIC,
	RHSM_PARTIALLY_VALID,
	RHSM_REGISTRATION_REQUIRED
} StatusType;

/* prototypes */

static void hide_icon (Context *);
static void display_icon (Context *, StatusType);
static void alter_icon (Context *, StatusType);
static void run_smg (Context *);
static void icon_clicked (GtkStatusIcon *, Context *);
static void icon_right_clicked (GtkStatusIcon *, guint, guint, Context *);
static void remind_me_later_clicked (NotifyNotification *, gchar *, Context *);
static void manage_subs_clicked (NotifyNotification *, gchar *, Context *);
static void register_now_clicked (NotifyNotification *, gchar *, Context *);
static void register_icon_click_listeners (Context *);
static void do_nothing_logger (const gchar *, GLogLevelFlags, const gchar *,
			       gpointer);
static void status_changed_cb (NotifyNotification *, gint, Context *);
static bool check_status (Context *);
static StatusType check_status_over_dbus ();
static StatusType create_status_type (int);

static StatusType
create_status_type (int status)
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
		case 4:
			return RHSM_PARTIALLY_VALID;
		case 5:
			return RHSM_REGISTRATION_REQUIRED;
		default:
			// we don't know this one, better to play it safe
			return RHSM_EXPIRED;
	}
}

static void
hide_icon (Context * context)
{
	if (!context->is_visible) {
		return;
	}
	gtk_status_icon_set_visible (context->icon, false);
	context->is_visible = false;

	notify_notification_close (context->notification, NULL);
}

static void
run_smg (Context * context)
{
	if (context->show_registration) {
		g_spawn_command_line_async
			("subscription-manager-gui --register", NULL);
	} else {
		g_spawn_command_line_async ("subscription-manager-gui", NULL);
	}
	hide_icon (context);
}

static void
icon_clicked (GtkStatusIcon * icon G_GNUC_UNUSED, Context * context)
{
	g_debug ("icon click detected");
	run_smg (context);
}

static void
icon_right_clicked (GtkStatusIcon * icon G_GNUC_UNUSED,
		    guint button G_GNUC_UNUSED,
		    guint activate_time G_GNUC_UNUSED, Context * context)
{
	g_debug ("icon right click detected");
	run_smg (context);
}

static void
remind_me_later_clicked (NotifyNotification * notification G_GNUC_UNUSED,
			 gchar * action G_GNUC_UNUSED, Context * context)
{
	g_debug ("Remind me later clicked");
	hide_icon (context);
}

static void
manage_subs_clicked (NotifyNotification * notification G_GNUC_UNUSED,
		     gchar * action G_GNUC_UNUSED, Context * context)
{
	g_debug ("Manage my subscriptions clicked");
	run_smg (context);
}

static void
register_now_clicked (NotifyNotification * notification G_GNUC_UNUSED,
		      gchar * action G_GNUC_UNUSED, Context * context)
{
	g_debug ("Register now clicked");
	run_smg (context);
}

/*
 * This signal handler waits for the status icon to first appear in the status
 * bar after we set its visibility to true. We have to do this for el5 era
 * notification display, which needs a fully initialized status icon to attach
 * to, in order to display in the correct location. We disconnect the signal
 * handler afterwards, because we don't care about the location once we display
 * the icon (and trying to reshow the notification could mess things up).
 */
static void
on_icon_size_changed (GtkStatusIcon * icon,
		      gint size G_GNUC_UNUSED, Context * context)
{
	notify_notification_show (context->notification, NULL);
	g_signal_handler_disconnect (icon, context->handler_id);
}

static void
display_icon (Context * context, StatusType status_type)
{
	static char *tooltip;
	static char *notification_title;
	static char *notification_body;

	if (status_type == RHSM_REGISTRATION_REQUIRED) {
		tooltip = _("Register System For Support And Updates");
		notification_title = tooltip;
		notification_body =
			_("In order for Subscription Manager to provide your "
			  "system with updates, your system must be registered "
			  "with the Customer Portal. Please enter your Red Hat "
			  "login to ensure your system is up-to-date.");
	} else if (status_type == RHSM_EXPIRED) {
		tooltip = _("Invalid or Missing Entitlement Subscriptions");
		notification_title = tooltip;
		notification_body =
			_("This system is missing one or more "
			  "subscriptions.");
	} else if (status_type == RHSM_PARTIALLY_VALID) {
		tooltip = _("Partially Entitled Products");
		notification_title = tooltip;
		notification_body =
			_("This system is missing one or more "
			  "subscriptions to fully cover its "
			  "products.");
	} else {
		tooltip = _("This System's Subscriptions Are About to Expire");
		notification_title = tooltip;
		notification_body =
			_("One or more of this system's "
			  "subscriptions are about to expire.");
	}

	gtk_status_icon_set_tooltip (context->icon, tooltip);
	context->is_visible = true;

	context->notification =
		notify_notification_new_with_status_icon (notification_title,
							  notification_body,
							  "subscription-manager",
							  context->icon);

	notify_notification_add_action (context->notification,
					"remind-me-later",
					_("Remind Me Later"),
					(NotifyActionCallback)
					remind_me_later_clicked, context, NULL);

	if (status_type == RHSM_REGISTRATION_REQUIRED) {
		notify_notification_add_action (context->notification,
						"register-system",
						_("Register Now"),
						(NotifyActionCallback)
						register_now_clicked, context,
						NULL);
	} else {
		notify_notification_add_action (context->notification,
						"manage-subscriptions",
						_("Manage My Subscriptions..."),
						(NotifyActionCallback)
						manage_subs_clicked, context,
						NULL);
	}

	gtk_status_icon_set_visible (context->icon, true);
	context->handler_id = g_signal_connect (context->icon, "size-changed",
						(GCallback)
						on_icon_size_changed, context);
}

static void
alter_icon (Context * context, StatusType status_type)
{
	context->show_registration = status_type == RHSM_REGISTRATION_REQUIRED;
	if ((status_type != RHN_CLASSIC) && (status_type != RHSM_VALID)) {
		display_icon (context, status_type);
	} else {
		hide_icon (context);
	}
}

static void
do_nothing_logger (const gchar * log_domain G_GNUC_UNUSED,
		   GLogLevelFlags log_level G_GNUC_UNUSED,
		   const gchar * message G_GNUC_UNUSED,
		   gpointer data G_GNUC_UNUSED)
{
	/* really, do nothing */
}

static StatusType
check_status_over_dbus (Context * context)
{
	GError *error;
	int status;

	error = NULL;
	if (!dbus_g_proxy_call (context->entitlement_status_proxy,
				"check_status", &error, G_TYPE_INVALID,
				G_TYPE_INT, &status, G_TYPE_INVALID)) {
		g_printerr ("Error: %s\n", error->message);
		g_error_free (error);
		exit (1);
	}

	return create_status_type (status);
}

static bool
check_status (Context * context)
{
	StatusType status_type;
	g_debug ("Running entitlement status check");

	if (force_icon) {
		g_debug ("Forcing display of icon (simulated invalidity)");
		if (g_str_equal (force_icon, "registration_required")) {
			status_type = RHSM_REGISTRATION_REQUIRED;
		} else if (g_str_equal (force_icon, "expired")) {
			status_type = RHSM_EXPIRED;
		} else if (g_str_equal (force_icon, "partial")) {
			status_type = RHSM_PARTIALLY_VALID;
		} else if (g_str_equal (force_icon, "warning")) {
			status_type = RHSM_WARNING;
		} else {
			g_print (N_("Unknown argument to force-icon: %s\n"),
				 force_icon);
			exit (1);
		}
		alter_icon (context, status_type);
	} else {
		status_type = check_status_over_dbus (context);
	}
	return true;
}

/*
 * initial status check, 4 mins after launch (so the panel can load).
 * return false so it won't run again.
 */
static bool
initial_check_status (Context * context)
{
	check_status (context);
	return false;
}

static void
status_changed_cb (NotifyNotification * notification G_GNUC_UNUSED,
		   gint status, Context * context)
{
	g_debug ("in callback, received value: %i", status);
	alter_icon (context, create_status_type (status));
}

static DBusGProxy *
get_entitlement_status_proxy (void)
{
	DBusGConnection *connection;
	GError *error;
	DBusGProxy *proxy;

	error = NULL;
	connection = dbus_g_bus_get (DBUS_BUS_SYSTEM, &error);
	if (connection == NULL) {
		g_printerr (N_("Failed to open connection to bus: %s\n"),
			    error->message);
		g_error_free (error);
		exit (1);
	}

	proxy = dbus_g_proxy_new_for_name (connection,
					   "com.redhat.SubscriptionManager",
					   "/EntitlementStatus",
					   "com.redhat.SubscriptionManager.EntitlementStatus");

	dbus_g_connection_unref (connection);
	return proxy;
}

static void
add_signal_listener (Context * context)
{
	dbus_g_proxy_add_signal (context->entitlement_status_proxy,
				 "entitlement_status_changed", G_TYPE_INT,
				 G_TYPE_INVALID);
	dbus_g_proxy_connect_signal (context->entitlement_status_proxy,
				     "entitlement_status_changed",
				     G_CALLBACK (status_changed_cb), context,
				     NULL);
}

static void
register_icon_click_listeners (Context * context)
{
	g_signal_connect (context->icon, "activate",
			  G_CALLBACK (icon_clicked), context);
	g_signal_connect (context->icon, "popup-menu",
			  G_CALLBACK (icon_right_clicked), context);
}

int
main (int argc, char **argv)
{
	GError *error = NULL;
	GOptionContext *option_context;
	DBusGProxy *proxy;
	DBusGConnection *connection;
	guint32 result;
	Context context;
	context.is_visible = false;
	context.show_registration = false;

	setlocale (LC_ALL, "");
	bindtextdomain ("rhsm", "/usr/share/locale");
	textdomain ("rhsm");

	option_context = g_option_context_new ("");
	g_option_context_add_main_entries (option_context, entries, NULL);
	g_option_context_add_group (option_context,
				    gtk_get_option_group (TRUE));

	if (!g_option_context_parse (option_context, &argc, &argv, &error)) {
		g_print (N_("option parsing failed: %s\n"), error->message);
		return 1;
	}

	g_option_context_free (option_context);

	if (!debug) {
		g_log_set_handler (NULL, G_LOG_LEVEL_DEBUG, do_nothing_logger,
				   NULL);
	}

	gtk_init (&argc, &argv);
	gconf_init (argc, argv, NULL);

	// read conf and quit if we shouldn't be running
	GConfClient *config;
	config = gconf_client_get_default ();

	// NB: if something goes awry, FALSE will be returned
	gboolean icon_setting =
		gconf_client_get_bool (config, "/apps/rhsm-icon/hide_icon",
				       NULL);
	g_debug ("icon setting: %i", icon_setting);
	if (icon_setting == TRUE) {
		g_warning
			("GConf setting \"/apps/rhsm-icon/hide_icon\" set to true, exiting");
		return 0;
	}

	g_object_unref (config);

	connection = dbus_g_bus_get (DBUS_BUS_SESSION, &error);
	if (connection == NULL) {
		g_printerr (N_("Failed to open connection to bus: %s\n"),
			    error->message);
		g_error_free (error);
		return 1;
	}

	proxy = dbus_g_proxy_new_for_name (connection,
					   "org.freedesktop.DBus",
					   "/org/freedesktop/DBus",
					   "org.freedesktop.DBus");
	error = NULL;
	if (!dbus_g_proxy_call (proxy,
				"RequestName",
				&error,
				G_TYPE_STRING, NAME_TO_CLAIM,
				G_TYPE_UINT, 0,
				G_TYPE_INVALID,
				G_TYPE_UINT, &result, G_TYPE_INVALID)) {
		g_printerr ("Couldn't acquire name: %s\n", error->message);
		return 1;
	}

	if (result != DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER) {
		if (error != NULL) {
			g_warning ("Failed to acquire %s: %s",
				   NAME_TO_CLAIM, error->message);
			g_error_free (error);
		} else {
			g_debug ("Failed to acquire %s", NAME_TO_CLAIM);
		}
		g_critical ("rhsm-icon is already running. exiting.");
		return 0;
	}

	notify_init ("rhsm-icon");

	context.icon =
		gtk_status_icon_new_from_icon_name ("subscription-manager");
	register_icon_click_listeners (&context);
	gtk_status_icon_set_visible (context.icon, false);

	context.entitlement_status_proxy = get_entitlement_status_proxy ();
	if (check_immediately) {
		check_status (&context);
	} else {
		g_timeout_add (INITIAL_DELAY * 1000,
			       (GSourceFunc) initial_check_status, &context);
	}
	//convert sec to msec before passing in
	g_timeout_add (check_period * 1000, (GSourceFunc) check_status,
		       &context);

	add_signal_listener (&context);
	gtk_main ();

	g_debug ("past main");
	g_object_unref (context.entitlement_status_proxy);
	g_object_unref (context.icon);
	g_object_unref (context.notification);
	g_object_unref (proxy);
	dbus_g_connection_unref (connection);
	return 0;
}
