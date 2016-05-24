
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
ROOT_DBUS_PATH = '/' + "/".join([TOP_LEVEL_DOMAIN, DOMAIN_NAME, SERVICE_SUB_DOMAIN_NAME_VER])

SUBMAND_PATH = ROOT_DBUS_PATH + '/' + "SubmanDaemon1"

SERVICE_VAR_PATH = '/var/lib/rhsm/cache'

DBUS_SERVICE_CACHE_PATH = SERVICE_VAR_PATH + '/' + 'dbus'

# Default base of policy kit action ids

# com.redhat.Subscriptions1
PK_ACTION_PREFIX = SERVICE_NAME

# com.redhat.Subscriptions1.default
PK_ACTION_DEFAULT = PK_ACTION_PREFIX + '.' + 'default'

# CONFIG
CONFIG_INTERFACE_VERSION = '1'
CONFIG_NAME = "Config" + CONFIG_INTERFACE_VERSION
CONFIG_INTERFACE = '.'.join([SERVICE_NAME,
                             CONFIG_NAME])
CONFIG_DBUS_PATH = ROOT_DBUS_PATH + '/' + CONFIG_NAME

# REGISTER SERVICE
REGISTER_INTERFACE_VERSION = '1'
REGISTER_SERVICE_NAME = "RegisterService" + REGISTER_INTERFACE_VERSION

REGISTER_INTERFACE = '.'.join([SERVICE_NAME,
                               REGISTER_SERVICE_NAME])
REGISTER_DBUS_PATH = ROOT_DBUS_PATH + '/' + REGISTER_SERVICE_NAME

# MAIN SERVICE
MAIN_SERVICE_NAME = "SubmanD"
MAIN_SERVICE_INTERFACE = '.'.join([SERVICE_NAME, MAIN_SERVICE_NAME])
