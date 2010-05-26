from connection import UEPConnection
import managerlib

class UEP(object):

    def __init__(self, host, ssl_port, cert_file=None, key_file=None):
        if cert_file and key_file:
            self._uep = UEPConnection(host, ssl_port, "/candlepin", cert_file,
                    key_file)
        else:
            self._uep = UEPConnection(host, ssl_port, "/candlepin")

    def unBindBySerialNumber(self, uuid, psubs):
        return self._uep.unBindBySerialNumber(uuid, psubs)

    def unregisterConsumer(self, uuid):
        return self._uep.unregisterConsumer(uuid)

    def registerConsumer(self, username, password, register_info):
        return self._uep.registerConsumer(username, password, register_info)

    def bindByProduct(self, uuid, phash):
        return self._uep.bindByProduct(uuid, phash)

    def bindByRegNumber(self, uuid, reg_token):
        return self._uep.bindByRegNumber(uuid, reg_token)

    def bindByEntitlementPool(self, uuid, pool):
        return self._uep.bindByEntitlementPool(uuid, pool)

    def getCompatibleSubscriptions(self, uuid):
        return managerlib.getCompatibleSubscriptions(self._uep, uuid)

    def getAllAvailableSubscriptions(self, uuid):
        return managerlib.getAllAvailableSubscriptions(self._uep, uuid)

    def getAvailableEntitlements(self, uuid):
        return managerlib.getAvailableEntitlements(self_uep, uuid)
