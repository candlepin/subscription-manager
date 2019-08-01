#
# Regular cron jobs for the subscription-manager package
#
0 4	* * *	root	[ -x /usr/bin/subscription-manager_maintenance ] && /usr/bin/subscription-manager_maintenance
