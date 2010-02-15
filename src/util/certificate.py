#!/usr/bin/python
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

"""
Contains classes for working with x.509 certificates.
The backing implementation is M2Crypto.X509 which has insufficient
support for custom v3 extensions.  It is not intended to be a
replacement of full wrapper but instead and extension.
"""

import re
from M2Crypto import X509


class ProductCertificate:
    """
    Represents a Red Hat product/entitlement certificate.
    It is OID schema aware and provides methods to get
    product and entitlement information.
    @cvar REDHAT: The Red Hat base OID.
    @type REDHAT: str
    """
    
    REDHAT = '1.3.6.1.4.1.2312'
    
    def __init__(self, path):
        """
        @param path: The path to the .pem file.
        @type path: str
        """
        x509 = Certificate(path)
        redhat = OID(self.REDHAT)
        self.ext = x509.extensions().ltrim(len(redhat))
        self.x509 = x509
        
    def getConsumerId(self):
        """
        Get the consumer ID.
        @return: The serial number.
        @rtype: str
        """
        return self.x509.serialnumber()

    def getProduct(self):
        """
        Get the product defined in the certificate.
        @return: A list of product object.
        @rtype: [L{Product},..]
        """
        products = self.ext.find('2.7.1', 1)
        if products:
            p = products[0]
            oid = p[0]
            root = oid.rtrim(1)
            ext = self.ext.branch(root)
            return Product(ext)
        return None
    
    def getEntitlements(self):
        """
        Get the entitlements defined in the certificate.
        @return: A list of entitlement object.
        @rtype: [L{Entitlement},..]
        """
        lst = []
        entitlements = self.ext.find('3.*.1')
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = self.ext.branch(root)
            lst.append(Entitlement(ext))
        return lst
    
    def __str__(self):
        s = []
        s.append(str(self.getProduct()))
        s.append('')
        for e in self.getEntitlements():
            s.append(str(e))
            s.append('')
        return '\n'.join(s)


class Product:

    def __init__(self, ext):
        self.ext = ext
        
    def getName(self):
        return self.ext.get('1')
    
    def getDescription(self):
        return self.ext.get('2')
    
    def getArch(self):
        return self.ext.get('3')
    
    def getVersion(self):
        return self.ext.get('4')
    
    def getQuantity(self):
        return self.ext.get('5')
    
    def getSubtype(self):
        return self.ext.get('6')
    
    def getVirtLimit(self):
        return self.ext.get('7')
    
    def getSocketLimit(self):
        return self.ext.get('8')
    
    def getProductOptionCode(self):
        return self.ext.get('9')
    
    def __str__(self):
        s = []
        s.append('Product {')
        s.append('\tName = %s' % self.getName())
        s.append('\tDescription = %s' % self.getDescription())
        s.append('\tArchitecture = %s' % self.getArchitecture())
        s.append('\tVersion = %s' % self.getVersion())
        s.append('\tQuantity = %s' % self.getQuantity())
        s.append('\tSubtype = %s' % self.getSubtype())
        s.append('\tVirtualization Limit = %s' % self.getVirtualizationLimit())
        s.append('\tSocket Limit = %s' % self.getSocketLimit())
        s.append('\tProduct Code = %s' % self.getProductOptionCode())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)
    
    
class Entitlement:

    def __init__(self, ext):
        self.ext = ext
        
    def getName(self):
        return self.ext.get('1')
    
    def getDescription(self):
        return self.ext.get('2')
    
    def getArch(self):
        return self.ext.get('3.1')
    
    def getVersion(self):
        return self.ext.get('4')
    
    def getGuestQuantity(self):
        return self.ext.get('5')
    
    def getQuantity(self):
        return self.ext.get('6')
    
    def getUpdatesAllowd(self):
        return self.ext.get('7')
    
    def getVendor(self):
        return self.ext.get('8')
    
    def getUrl(self):
        return self.ext.get('9')
    
    def __str__(self):
        s = []
        s.append('Entitlement {')
        s.append('\tName = %s' % self.getName())
        s.append('\tDescription = %s' % self.getDescription())
        s.append('\tArchitecture = %s' % self.getArchitecture())
        s.append('\tVersion = %s' % self.getVersion())
        s.append('\tGuest Quantity = %s' % self.getGuestQuantity())
        s.append('\tQuantity = %s' % self.getQuantity())
        s.append('\tUpdates Allowd = %s' % self.getUpdatesAllowd())
        s.append('\tVendor = %s' % self.getVendor())
        s.append('\tURL = %s' % self.getUrl())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


##########################################################################
# Lower level x.509 classes
#
# x509 = Certificate('/tmp/mycert.pem')
# print x509  # textual representation of the cert
# ext = x509.extensions()
# value = ext.get('1.3.1')  # get the value of a specific OID
# print value
# values = ext.find('1.*.3') get a list of (OID, value) using wildcard OID.
# print values
##########################################################################


class Certificate(object):
    """
    Represents and x.509 certificate.
    @ivar x509: The M2Crypto.X509 backing object.
    @type x509: L{X509}
    @ivar __ext: A dictionary of extensions L{OID}:value
    @type __ext: L{Extensions} 
    """

    def __init__(self, path):
        """
        @param path: The path to the .pem file.
        @type path: str
        """
        self.x509 = X509.load_cert(path)
        self.__ext = Extensions(self)
        
    def extensions(self):
        """
        Get the x.509 extensions object.
        @return: The L{Extensions} object for the certificate.
        @rtype: L{Extensions}
        """
        return self.__ext
    
    def serialnumber(self):
        """
        Get the serial number
        @return: The x.509 serial number
        @rtype: str
        """
        return self.x509.get_serial_number()
            
    def __str__(self):
        return self.x509.as_text()


class Extensions(dict):
    """
    Represents x.509 (v3) I{custom} extensions.
    """
    
    pattern = re.compile('([0-9]+\.)+[0-9]:')
    
    def __init__(self, cert):
        """
        @param cert: A certificate object.
        @type cert: L{Certificate}
        """
        if isinstance(cert, Certificate):
            self.__parse(cert)
        else:
            self.update(cert)
        
    def ltrim(self, n):
        """
        Left trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{Extensions}
        """
        d = {}
        for oid,v in self.items():
            d[oid.ltrim(n)] = v
        return Extensions(d)
                
    def get(self, oid):
        """
        Get the value of an extension by I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str|L{OID}
        @return: The value of the first extension matched.
        @rtype: str
        """
        ext = self.find(oid, 1)
        if ext:
            return ext[0][1]
        else:
            return None
    
    def find(self, oid, limit=0):
        """
        Find all extensions matching the I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str|L{OID}
        @param limit: Limit the number returned, 0=unlimited
        @type limit: int
        @return: A list of matching items.
        @rtype: (OID, value)
        @see: OID.match()
        """
        ext = []
        if isinstance(oid, str):
            oid = OID(oid)
        keyset = sorted(self.keys())
        for k in keyset:
            v = self[k]
            if k.match(oid):
                ext.append((k, v))
            if limit and len(ext) == limit:
                break
        return ext
    
    def branch(self, root):
        """
        Find a subtree by matching the oid.
        @param root: An OID that may contain (*) wildcards.
        @type root: str|L{OID}
        @return: A subtree.
        @rtype: L{Extensions}
        """
        d = {}
        if isinstance(root, str):
            root = OID(root)
        if root[-1]:
            root = root.append('')
        ln = len(root)-1
        for oid,v in self.find(root):
            trimmed = oid.ltrim(ln)
            d[trimmed] = v
        return Extensions(d)
    
    def __ext(self, cert):
        # get extensions substring
        text = str(cert)
        start = text.find('extensions:')
        end = text.rfind('Signature Algorithm:')
        text = text[start:end]
        return [s.strip() for s in text.split('\n')]
    
    def __parse(self, cert):
        # parse the extensions section
        oid = None
        for entry in self.__ext(cert):
            if oid is not None:
                self[oid] = entry[2:]
                oid = None
                continue
            m = self.pattern.match(entry)
            if m is None:
                continue
            oid = OID(entry[:-1])
            
    def __str__(self):
        s = []
        for item in self.items():
            s.append('%s = "%s"' % item)
        return '\n'.join(s)


class OID(object):
    """
    The Object Identifier object.
    @ivar part: The oid parts.
    @type part: [str,]
    @cvar WILDCARD: The wildcard character.
    @type WILDCARD: str
    """
    
    WILDCARD = '*'
    
    @classmethod
    def join(cls, *oid):
        return '.'.join(oid)
    
    @classmethod
    def split(cls, s):
        """
        Split an OID string.
        @param s: An OID string Eg: (1.2.3)
        @type s: str
        @return: A list of OID parts.
        @rtype: [str,]
        """
        return s.split('.')
    
    def __init__(self, oid):
        """
        @param oid: The OID value.
        @type oid: str|[str,]
        """
        if isinstance(oid, str):
            self.part = self.split(oid)
        else:
            self.part = oid
        
    def parent(self):
        """
        Get the parent OID.
        @return: The parent OID.
        @rtype: L{OID}
        """
        p = self.part[:-1]
        if p:
            return OID(p)
        
    def ltrim(self, n):
        """
        Left trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{OID}
        """
        return OID(self.part[n:])
    
    def rtrim(self, n):
        """
        Right trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{OID}
        """
        return OID(self.part[:-n])
    
    def append(self, oid):
        """
        Append the specified OID fragment.
        @param oid: An OID fragment.
        @type oid: str|L{OID}
        @return: The concatenated OID.
        @rtype: L{OID}
        """
        if isinstance(oid, str):
            oid = OID(oid)
        part = self.part + oid.part
        return OID(part)
        
    def match(self, oid):
        """
        Match the specified OID considering wildcards.
        Patterns:
          - 1.4.5.6.74 (not wildcarded)
          -    .5.6.74 (match on only last 4)
          -    5.6.74. (match only first 4)
          - 1.4.*.6.*  (wildcard pattern)
        @param oid: An OID string or object.
        @type oid: str|L{OID}
        @return: True if matched
        """
        i = 0
        if isinstance(oid, str):
            oid = OID(oid)
        try:
            if not oid[0]:
                oid = OID(oid[1:])
                parts = self.part[-len(oid):]
            elif not oid[-1]:
                oid = OID(oid[:-1])
                parts = self.part[:len(oid)]
            else:
                parts = self.part
            for x in parts:
                if ( x == oid[i] or oid[i] == self.WILDCARD ):
                    i += 1
                else:
                    raise Exception()
        except:
            return False
        return True
    
    def __len__(self):
        return len(self.part)
    
    def __getitem__(self, index):
        return self.part[index]
    
    def __repr__(self):
        return str(self)
    
    def __hash__(self):
        return hash(str(self))
    
    def __eq__(self, other):
        return ( str(self) == str(other) )
    
    def __str__(self):
        return '.'.join(self.part)


import sys
if __name__ == '__main__':
    for path in sys.argv[1:]:
        print path
        pc = ProductCertificate(path)
        print pc.x509
        print pc
