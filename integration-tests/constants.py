from dasbus.identifier import DBusObjectIdentifier, DBusServiceIdentifier
from dasbus.connection import SystemMessageBus


HOST_DETAILS: str = "/var/lib/insights/host-details.json"
MACHINE_ID_FILE: str = "/etc/insights-client/machine-id"
RHSM_CONFIG_FILE_PATH: str = "/etc/rhsm/rhsm.conf"

RHSM_NAMESPACE = ("com", "redhat", "RHSM1")

RHSM = DBusServiceIdentifier(namespace=RHSM_NAMESPACE, message_bus=SystemMessageBus())

RHSM_CONFIG = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Config")

RHSM_REGISTER_SERVER = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="RegisterServer")

RHSM_REGISTER = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Register")

RHSM_UNREGISTER = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Unregister")

RHSM_ENTITLEMENT = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Entitlement")

RHSM_SYSPURPOSE = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Syspurpose")

RHSM_CONSUMER = DBusObjectIdentifier(namespace=RHSM_NAMESPACE, basename="Consumer")
