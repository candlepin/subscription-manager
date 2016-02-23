
TOP_LEVEL_DOMAIN = "com"
DOMAIN_NAME = "redhat"
SERVICE_DOMAIN = TOP_LEVEL_DOMAIN + '.' + DOMAIN_NAME
SERVICE_SUB_DOMAIN_BASE = "Subscriptions"
SERVICE_VERSION = "1"

# "Subscriptions1"
SERVICE_SUB_DOMAIN_NAME_VER = SERVICE_SUB_DOMAIN_BASE + SERVICE_VERSION

# The base of the 'well known name' used for bus and service names, as well
# as interface names and object paths.
#
# "com.redhat.Subscriptions1"
SERVICE_NAME = SERVICE_DOMAIN + '.' + SERVICE_SUB_DOMAIN_NAME_VER

# The default interface name for objects we share on this service.
# Also "com.redhat.Subscriptions1"
DBUS_INTERFACE = SERVICE_NAME

# The root of the objectpath tree for our services.
# Note: No trailing '/'
#
# /com/redhat/Subscriptions1
ROOT_DBUS_PATH = '/' + TOP_LEVEL_DOMAIN + '/' + DOMAIN_NAME + '/' + SERVICE_SUB_DOMAIN_NAME_VER

# Default base of policy kit action ids

# com.redhat.Subscriptions1
PK_ACTION_PREFIX = SERVICE_NAME

# com.redhat.Subscriptions1.default
PK_ACTION_DEFAULT = PK_ACTION_PREFIX + '.' + 'default'
