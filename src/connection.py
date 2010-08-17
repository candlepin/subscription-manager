#
# A proxy interface to initiate and interact communication with Unified Entitlement Platform server such as candlepin.
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import sys
import locale
import httplib
import simplejson as json
import base64
import os
from M2Crypto import SSL, httpslib
from logutil import getLogger, trace_me
from config import initConfig

import gettext
_ = gettext.gettext


log = getLogger(__name__)
DEFAULT_CA_FILE="/etc/pki/CA/candlepin.pem"
class RestlibException(Exception):
    def __init__(self, code, msg = ""):
        self.code = code
        self.msg = msg

    def __str__(self):
        return self.msg

class Restlib(object):
    """
     A wrapper around httplib to make rest calls easier
    """
    def __init__(self, host, ssl_port, apihandler, cert_file=None, key_file=None, ca_file=None, insecure=False):
        self.host = host
        self.ssl_port = ssl_port
        self.apihandler = apihandler
        self.headers = {"Content-type":"application/json",
                        "Accept": "application/json",
                        "Accept-Language": locale.getdefaultlocale()[0].lower().replace('_', '-')}
        self.cert_file = cert_file
        self.key_file  = key_file
        self.ca_file = ca_file
        self.insecure = insecure

    def _request(self, request_type, method, info=None):
        handler = self.apihandler + method
        context = SSL.Context("sslv3")
        if self.ca_file != None:
            log.info('loading ca_file located at: %s', self.ca_file)
            context.load_verify_locations(self.ca_file)
        log.info('work in insecure mode ?:%s', self.insecure)
        if not self.insecure: #allow clients to work insecure mode if required..
            context.set_verify(SSL.verify_fail_if_no_peer_cert, 1)
        if self.cert_file:
            context.load_cert(self.cert_file, keyfile=self.key_file)
            conn = httpslib.HTTPSConnection(self.host, self.ssl_port, ssl_context=context)
        else:
            conn = httpslib.HTTPSConnection(self.host, self.ssl_port, ssl_context=context)
        conn.request(request_type, handler, body=json.dumps(info), \
                     headers=self.headers)
        response = conn.getresponse()
        result = {
            "content": response.read(),
            "status" : response.status
        }
        #TODO: change logging to debug.
        log.info('response:' + str(result['content']))
        log.info('status code: ' + str(result['status']))
        self.validateResponse(result)
        if not len(result['content']):
            return None
        return json.loads(result['content'])

    def validateResponse(self, response):
        if str(response['status']) not in ["200", "204"]:
            parsed = json.loads(response['content'])
            raise RestlibException(response['status'],
                    parsed['displayMessage'])

    def request_get(self, method):
        return self._request("GET", method)

    def request_post(self, method, params=""):
        return self._request("POST", method, params)

    def request_head(self, method):
        return self._request("HEAD", method)

    def request_put(self, method, params=""):
        return self._request("PUT", method, params)

    def request_delete(self, method):
        return self._request("DELETE", method)

class UEPConnection:
    """
    Proxy for Unified Entitlement Platform.
    """
    def __init__(self, host='localhost', ssl_port=8443, handler="/candlepin",
            cert_file=None, key_file=None):
        self.host = host
        self.ssl_port = ssl_port
        self.handler = handler
        self.conn = None
        self.basic_auth_conn = None
        self.cert_file = cert_file
        self.key_file = key_file
        config = initConfig()
        self.candlepin_ca_file = config['candlepin_ca_file']
        config_insecure = config['insecure_mode']
        self.insecure = False
        if config_insecure in ['True', 'true', 't', 1]:
            self.insecure = True
        if self.candlepin_ca_file == None:
            log.info("Value \'candlepin_ca_file\' not present in config file. Assuming default value: %s",
                     DEFAULT_CA_FILE)
            self.candlepin_ca_file = DEFAULT_CA_FILE
        # initialize connection
        self.conn = Restlib(self.host, self.ssl_port, self.handler, self.cert_file, self.key_file, self.candlepin_ca_file, self.insecure)
        log.info("Connection Established: host: %s, port: %s, handler: %s" %
                (self.host, self.ssl_port, self.handler))
        log.info("Connection using cert_file: %s, key_file: %s, ca_file: %s insecure_mode: %s" % (self.cert_file, self.key_file, self.candlepin_ca_file, self.insecure))
        #log.info("trace: %s" % trace_me())

    def add_ssl_certs(self, cert_file=None, key_file=None):
        self.cert_file = cert_file
        self.key_file = key_file
        self.conn = Restlib(self.host, self.ssl_port, self.handler, self.cert_file, self.key_file, self.candlepin_ca_file, self.insecure)

    def shutDown(self):
        self.conn.close()
        log.info("remote connection closed")

    def __authenticate(self, username, password):
        # a connection for basic auth stuff, aka, not using the consumer cert
        self.basic_auth_conn =  Restlib(self.host, self.ssl_port, self.handler,
              ca_file=self.candlepin_ca_file, insecure=self.conn.insecure)
        log.info("Basic Auth Connection Established: host: %s, port: %s, handler: %s" %
              (self.host, self.ssl_port, self.handler))
        encoded = base64.encodestring(':'.join((username,password)))
        basic = 'Basic %s' % encoded[:-1]
        self.basic_auth_conn.headers['Authorization'] = basic
        return self.basic_auth_conn.headers

    def ping(self):
        return self.conn.request_get("/status/")

    def registered(self):
        needToRegister=0
        if not os.access("/etc/pki/consumer/cert.pem", os.F_OK):
            needToRegister = 1
        return needToRegister

    def registerConsumer(self, username, password, name="unknown",
            type="system", facts={}):
        """
         Creates a consumer on candlepin server
        """
        params = {
                "type": type,
                "name": name,
                "facts": facts
        }
        self.__authenticate(username, password)
        return self.basic_auth_conn.request_post('/consumers/', params)

    def updateConsumerFacts(self, consumer_uuid, facts={}):
        """
        Update a consumers facts on candlepin server
        """
        params = {
            "facts": facts
            }
        method = "/consumers/%s" % consumer_uuid
        ret = self.conn.request_put(method, params)
        return ret

    def getConsumerById(self, consumerId, username, password):
        """
        Returns a consumer object with pem/key for existing consumers
        """
        self.__authenticate(username, password)
        method = '/consumers/%s' % consumerId
        return self.basic_auth_conn.request_get(method)

    def unregisterConsumer(self, consumerId):
        """
         Deletes a consumer from candlepin server
        """
        method = '/consumers/%s' % consumerId
        return self.conn.request_delete(method)

    def syncCertificates(self, consumerId):
        """
        Sync all applicable certificates for a given consumer\
        """
        method = '/consumers/%s/certificates' % consumerId
        return self.conn.request_get(method)

    def getCertificates(self, consumer_uuid, serials=[]):
        """
        Fetch all entitlement certificates for this consumer.
        Specify a list of serial numbers to filter if desired.
        """
        method = '/consumers/%s/certificates' % (consumer_uuid)
        if len(serials) > 0:
            serials_str = ','.join(serials)
            method = "%s?serials=%s" % (method, serials_str)
        return self.conn.request_get(method)

    def getCertificateSerials(self, consumerId):
        """
        Get serial numbers for certs for a given consumer
        """
        method = '/consumers/%s/certificates/serials' % consumerId
        return self.conn.request_get(method)

    def bindByRegNumber(self, consumerId, regnum, email=None, lang=None):
        """
        Subscribe consumer to a subscription token
        """
        method = "/consumers/%s/entitlements?token=%s" % (consumerId, regnum)
        if email:
            method += "&email=%s" % email
            if not lang:
                lang = locale.getdefaultlocale()[0].lower().replace('_', '-')
            method += "&email_locale=%s" % lang
        return self.conn.request_post(method)

    def bindByEntitlementPool(self, consumerId, poolId, quantity=None):
        """
         Subscribe consumer to a subscription by poolId
        """
        method = "/consumers/%s/entitlements?pool=%s" % (consumerId, poolId)
        if quantity:
            method = "%s&quantity=%s" % (method, quantity)
        return self.conn.request_post(method)

    def bindByProduct(self, consumerId, product=None):
        """
         Subscribe consumer directly to a product by Name
        """
        product = product.replace(" ", "%20")
        method = "/consumers/%s/entitlements?product=%s" % (consumerId, product)
        return self.conn.request_post(method)

    def unBindBySerialNumber(self, consumerId, serial):
        method = "/consumers/%s/certificates/%s" % (consumerId, serial)
        return self.conn.request_delete(method)

    def unBindByEntitlementId(self, consumerId, entId):
        method = "/consumers/%s/entitlements/%s" % (consumerId, entId)
        return self.conn.request_delete(method)

    def unbindAll(self, consumerId):
        method = "/consumers/%s/entitlements" % consumerId
        return self.conn.request_delete(method)

    def getPoolsList(self, consumerId):
        method = "/pools?consumer=%s" % consumerId
        return self.conn.request_get(method)

    def getPool(self, poolId):
        method = "/pools/%s" % poolId
        return self.conn.request_get(method)

    def getEntitlementList(self, consumerId):
        method = "/consumers/%s/entitlements" % consumerId
        return self.conn.request_get(method)

    def getEntitlementById(self, consumerId, entId):
        method = "/consumers/%s/entitlements/%s" % (consumerId, entId)
        return self.conn.request_get(method)
    
    # TODO: Bad method name, this is listing pools, not entitlements.
    # Also nearly the same as getPoolsList.
    def getAllAvailableEntitlements(self, consumerId):
        method = "/pools?consumer=%s&listall=true" % consumerId
        return self.conn.request_get(method)

    def regenIdCertificate(self, consumerId):
        method = "/consumers/%s" % consumerId
        return self.conn.request_post(method)
        

if __name__ == '__main__':
    if len(sys.argv) > 1:
        uep = UEPConnection(sys.argv[1])
    else:
        uep = UEPConnection()
    # create a consumer
    stype = {'label':'system'}
    product = {"id":"1","label":"RHEL AP","name":"rhel"}
    facts = {
        "arch": "i386",
        "cpu": "Intel" ,
        "cores": 4,
    }

    params = {
        "type": 'system',
        "name": 'admin',
        "facts": facts,
    }
    try:
        consumer = uep.registerConsumer('admin', 'admin', info=params)
        print "Created a consumer ", consumer
        # sync certs
        print "Get Consumer By Id", uep.getConsumerById(consumer['uuid'], 'admin', 'admin')
        print uep.syncCertificates(consumer['uuid']) 
        print "All available", uep.getAllAvailableEntitlements(consumer['uuid'])
        print "GetCertBySerials",uep.getCertificates(consumer['uuid'],
                serials=['SERIAL001','SERIAL001'])
        # bind consumer to regNumber
        #uep.bindByRegNumber(consumer['uuid'],"1234-5334-4e23-2432-4345") 
        # bind consumer by poolId
        #uep.bindByEntitlementPool(consumer['uuid'], "1001")
        # bind consumer By Product
        print "bind by product", uep.bindByProduct(consumer['uuid'], "monitoring") #product["label"])
        print "ZZZZZZZZZZZ",uep.getCertificateSerials(consumer['uuid'])
        # Unbind All
        #print uep.unbindAll(consumer['uuid'])
        # Unbind serialNumbers
        #uep.unBindBySerialNumbers(consumer['uuid'], ['SERIAL001','SERIAL001'])
        print "Pools List",uep.getPoolsList(consumer['uuid'])
        # lookup Entitlement Info by PoolId
        #print uep.getEntitlementById("4")
        print "print get Ent list", uep.getEntitlementList(consumer['uuid'])
        print uep.getEntitlementById(consumer['uuid'], "3")
        # delete a consumer
        print uep.unregisterConsumer('admin', 'password', consumer['uuid'])
        print "consumer unregistered"
    except RestlibException, e:
        print"Error:", e
        sys.exit(-1)
