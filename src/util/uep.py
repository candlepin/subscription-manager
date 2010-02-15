#
# Copyright (C) 2005-2008 Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# Jeff Ortel (jortel@redhat.com)
#

import sys
import httplib, urllib
import simplejson as json
import base64

class UEP:
    """
    Proxy for Unified Entitlement Platform.
    """
    
    HEADERS = {
        'Content-type':'application/json',
        'Accept':'application/json',
    }
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
    
    def registerConsumer(self, username, password, hardware, products):
        con = httplib.HTTPConnection(self.host, self.port)
        type = {'label':'system'}
        facts = {}
        params = {
            'type':type,
            'name':'whoknows',
            'facts':facts,
        }
        headers = self.__credentials(username, password)
        headers.update(self.HEADERS)
        con.request("POST", '/candlepin/consumer/', json.dumps(params), headers)
        fp = con.getresponse()
        reply = fp.read()
        p12 = json.loads(reply)['p12']
        con.close()
        return base64.decodestring(p12)
    
    def unregisterConsumer(self, consumerId):
        pass
    
    def syncCertificates(self, consumerId, serialNumbers):
        pass
    
    def bind(self, consumerId, regnum=None, pool=None, product=None):
        pass
    
    def unbind(self, consumerId, serialNumbers):
        pass
    
    def getEntitlementPools(self, consumerId):
        pass
    
    def ping(self):
        pass
    
    def __credentials(self, u, u):
        d = {}
        encoded = base64.encodestring(':'.join((u,p)))
        basic = 'Basic %s' % encoded[:-1]
        headers['Authorization'] = basic
        return d
