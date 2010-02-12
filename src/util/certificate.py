#
# Subscription Manager
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
Usage:
  from certificate import Certificate

  x509 = Certificate('/tmp/mycert.pem')
  
  # textual representation of the cert
  print x509

  ext = x509.extensions()

  # get the value of a specific OID
  value = ext.get('1.3.1')
  print value

  # get a list of (OID, value) using wildcard OID.
  values = ext.find('1.*.3')
  print values
"""

import re
from M2Crypto import X509


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
    
    def serial_number(self):
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
        self.__parse(cert)
        
    def get(self, oid):
        """
        Get the value of an extension by I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str
        @return: The value of the first extension matched.
        @rtype: str
        """
        ext = self.find(oid)
        if ext:
            return ext[0][1]
        else:
            return None
    
    def find(self, oid):
        """
        Find all extensions matching the I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str
        @return: A list of matching items.
        @rtype: (OID, value)
        @see: OID.match()
        """
        ext = []
        if isinstance(oid, str):
            oid = OID(oid)
        for item in self.items():
            if item[0].match(oid):
                ext.append(item)
        return ext
    
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
        
    def match(self, oid):
        """
        Match the specified OID considering wildcards.
        Patterns:
          - 1.4.5.6.74 (not wildcarded)
          -    .5.6.74 (match only last 4)
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
