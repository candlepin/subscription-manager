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
from logutil import getLogger
from config import initConfig 

log = getLogger(__name__)

import gettext
_ = gettext.gettext

config = initConfig()


class RestlibException(Exception):

    def __init__(self, code, msg=""):
        self.code = code
        self.msg = msg

    def __str__(self):
        return self.msg


class Restlib(object):
    """
     A wrapper around httplib to make rest calls easier
    """

    def __init__(self, host, ssl_port, apihandler,
            username=None, password=None,
            cert_file=None, key_file=None,
            ca_file=None, insecure=False):
        self.host = host
        self.ssl_port = ssl_port
        self.apihandler = apihandler
        self.headers = {"Content-type": "application/json",
                        "Accept": "application/json",
                        "Accept-Language": locale.getdefaultlocale()[0].lower().replace('_', '-')}
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.insecure = insecure
        self.username = username
        self.password = password

        # Setup basic authentication if specified:
        if username and password:
            encoded = base64.encodestring(':'.join((username, password)))
            basic = 'Basic %s' % encoded[:-1]
            self.headers['Authorization'] = basic

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
            "status": response.status}
        #TODO: change logging to debug.
       # log.info('response:' + str(result['content']))
        log.info('status code: ' + str(result['status']))
        self.validateResponse(result)
        if not len(result['content']):
            return None
        return json.loads(result['content'])

    def validateResponse(self, response):
        if str(response['status']) not in ["200", "204"]:
            parsed = {}
            try:
                parsed = json.loads(response['content'])
            except Exception, e:
                log.exception(e)
                raise RestlibException(response['status'], _("Network error. Please check the connection details."))

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
    Class for communicating with the REST interface of a Red Hat Unified
    Entitlement Platform.
    """

    def __init__(self, 
            host=config.get('server', 'hostname'),
            ssl_port=int(config.get('server', 'port')),
            handler=config.get('server', 'prefix'),
            username=None, password=None,
            cert_file=None, key_file=None):
        """
        Two ways to authenticate:
            - username/password for HTTP basic authentication. (owner admin role)
            - uuid/key_file/cert_file for identity cert authentication.
              (consumer role)

        Must specify one method of authentication or the other, not both.
        """
        self.host = host
        self.ssl_port = ssl_port
        self.handler = handler

        self.cert_file = cert_file
        self.key_file = key_file
        self.username = username
        self.password = password

        self.ca_cert = config.get('server', 'ca_cert')
        config_insecure = int(config.get('server', 'insecure'))
        self.insecure = False
        if config_insecure:
            self.insecure = True

        using_basic_auth = False
        using_id_cert_auth = False

        if username and password:
            using_basic_auth = True
        elif cert_file and key_file:
            using_id_cert_auth = True

        if using_basic_auth and using_id_cert_auth:
            raise Exception("Cannot specify both username/password and "
                    "cert_file/key_file")
        if not (using_basic_auth or using_id_cert_auth):
            raise Exception("Must specify either username/password or "
                    "cert_file/key_file")

        # initialize connection
        if using_basic_auth:
            self.conn = Restlib(self.host, self.ssl_port, self.handler,
                    username=self.username, password=self.password,
                    ca_file=self.ca_cert, insecure=self.insecure)
            log.info("Using basic authentication as: %s" % username)
        else:
            self.conn = Restlib(self.host, self.ssl_port, self.handler,
                    cert_file=self.cert_file, key_file=self.key_file,
                    ca_file=self.ca_cert, insecure=self.insecure)
            log.info("Using certificate authentication: key = %s, cert = %s, "
                    "ca = %s, insecure = %s" %
                    (self.key_file, self.cert_file, self.ca_cert, self.insecure))

        log.info("Connection Established: host: %s, port: %s, handler: %s" %
                (self.host, self.ssl_port, self.handler))


    def shutDown(self):
        self.conn.close()
        log.info("remote connection closed")

    def ping(self, username=None, password=None):
        return self.conn.request_get("/status/")

    def createOwner(name):
        owner = {
                'key': name,
                'displayName': name,
        }
        self.conn.request_post('/owners/', owner)

    def deleteOwner(key):
        self.conn.request_delete('/owners/%s' % key)

    def registerConsumer(self, name="unknown", type="system", facts={}):
        """
        Creates a consumer on candlepin server
        """
        params = {"type": type,
                  "name": name,
                  "facts": facts}
        return self.conn.request_post('/consumers/', params)

    def updateConsumerFacts(self, consumer_uuid, facts={}):
        """
        Update a consumers facts on candlepin server
        """
        params = {"facts": facts}
        method = "/consumers/%s" % consumer_uuid
        ret = self.conn.request_put(method, params)
        return ret

    def getConsumerById(self, consumerId, username, password):
        """
        Returns a consumer object with pem/key for existing consumers
        """
        method = '/consumers/%s' % consumerId
        return self.conn.request_get(method)

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

    def getPoolsList(self, consumerId, listAll=False):
        method = "/pools?consumer=%s" % consumerId
        if listAll:
            method = "%s?listall=true" % method
        results = self.conn.request_get(method)

        return results

    def getPool(self, poolId):
        method = "/pools/%s" % poolId
        return self.conn.request_get(method)

    def getEntitlementList(self, consumerId):
        method = "/consumers/%s/entitlements" % consumerId
        results = self.conn.request_get(method)
        return results

    def getEntitlementById(self, entId):
        method = "/entitlements/%s" % entId
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
    stype = {'label': 'system'}
    product = {"id": "1", "label": "RHEL AP", "name": "rhel"}
    facts = {
        "arch": "i386",
        "cpu": "Intel",
        "cores": 4,
    }

    params = {
        "type": 'system',
        "name": 'admin',
        "facts": facts,
    }
    try:
        admin_cp = UEPConnection(username='admin', password='admin')
        consumer = admin_cp.registerConsumer(info=params)
        print "Created a consumer ", consumer
        # sync certs
        print "Get Consumer By Id", uep.getConsumerById(consumer['uuid'], 'admin', 'admin')
        print uep.syncCertificates(consumer['uuid'])
        print "GetCertBySerials", uep.getCertificates(consumer['uuid'],
                serials=['SERIAL001', 'SERIAL001'])
        # bind consumer to regNumber
        #uep.bindByRegNumber(consumer['uuid'],"1234-5334-4e23-2432-4345")
        # bind consumer by poolId
        #uep.bindByEntitlementPool(consumer['uuid'], "1001")
        # bind consumer By Product
        print "bind by product", uep.bindByProduct(consumer['uuid'], "monitoring") #product["label"])
        print "ZZZZZZZZZZZ", uep.getCertificateSerials(consumer['uuid'])
        # Unbind All
        #print uep.unbindAll(consumer['uuid'])
        # Unbind serialNumbers
        #uep.unBindBySerialNumbers(consumer['uuid'], ['SERIAL001','SERIAL001'])
        print "Pools List", uep.getPoolsList(consumer['uuid'])
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
