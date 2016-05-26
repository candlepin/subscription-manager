
import rhsmlib.dbus as common_constants

SUB_SERVICE_NAME = "Facts"

# com.redhat.Subscriptions1.Facts
FACTS_BUS_NAME = common_constants.SERVICE_NAME + '.' + SUB_SERVICE_NAME

# also, com.redhat.Subscriptions1.Facts
FACTS_DBUS_INTERFACE = common_constants.SERVICE_NAME + '.' + SUB_SERVICE_NAME

FACTS_SUB_DBUS_PATH = SUB_SERVICE_NAME
# /com/redhat/Subscriptions1/Facts
FACTS_ROOT_DBUS_PATH = common_constants.ROOT_DBUS_PATH + '/' + FACTS_SUB_DBUS_PATH

FACTS_ROOT_VERSION = "1.1e1"
FACTS_ROOT_NAME = "Red Hat Subscription Manager facts."

FACTS_HOST_SUB_DBUS_PATH = 'Host'
FACTS_HOST_DBUS_PATH = FACTS_ROOT_DBUS_PATH + '/' + FACTS_HOST_SUB_DBUS_PATH
FACTS_HOST_VERSION = "11.0-11.0.el11"
FACTS_HOST_NAME = "Red Hat Subscription Manager host facts."
FACTS_HOST_CACHE_FILE = common_constants.DBUS_SERVICE_CACHE_PATH + '/' + FACTS_BUS_NAME + '.' + FACTS_HOST_SUB_DBUS_PATH
# How long the facts cache is valid for in seconds
FACTS_HOST_CACHE_DURATION = 240

FACTS_USER_SUB_DBUS_PATH = 'User'
FACTS_USER_DBUS_PATH = FACTS_ROOT_DBUS_PATH + '/' + FACTS_USER_SUB_DBUS_PATH
FACTS_USER_VERSION = "11"
FACTS_USER_NAME = 'Red Hat Subscription Manager user facts.'

FACTS_READ_WRITE_SUB_DBUS_PATH = 'ReadWrite'
FACTS_READ_WRITE_DBUS_PATH = FACTS_ROOT_DBUS_PATH + '/' + FACTS_READ_WRITE_SUB_DBUS_PATH
FACTS_READ_WRITE_VERSION = "11.0"
FACTS_READ_WRITE_NAME = 'Red Hat Subscription Manager editable facts.'

FACTS_EXAMPLE_SUB_DBUS_PATH = 'Example'
FACTS_EXAMPLE_DBUS_PATH = FACTS_ROOT_DBUS_PATH + '/' + FACTS_EXAMPLE_SUB_DBUS_PATH
FACTS_EXAMPLE_VERSION = "10.plus_one_more"
FACTS_EXAMPLE_NAME = "Red Hat Subscription Manager example facts."

# policy kit
PK_ACTION_FACTS_COLLECT = common_constants.PK_ACTION_PREFIX + '.' + SUB_SERVICE_NAME + '.' + 'collect'
