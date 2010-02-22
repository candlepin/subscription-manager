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


import re
from connection import UEPConnection as UEP
from certificate import Certificate
from logutil import getLogger

log = getLogger(__name__)


class CertLib:
    
    def update(self):
        cd = CertDirectory()
        bundles = cd.bundles()
        pass
        
    def add(self, *bundles):
        pass
    
    def __fetch(self, serialnumbers):
        pass


class Bundle:
    
    KEY_PATTERN = re.compile(
        '(-----BEGIN.+KEY-----\n)(.+)(\n-----END.+KEY-----)',
        re.DOTALL)
    CERT_PATTERN = re.compile(
        '(-----BEGIN CERTIFICATE-----\n)(.+)(\n-----END CERTIFICATE-----)',
        re.DOTALL)
    
    @classmethod
    def split(cls, pem):
        m = cls.KEY_PATTERN.search(pem)
        key = m.group(2)
        m = cls.CERT_PATTERN.search(pem)
        cert = m.group(2)
        return Bundle(key, cert)
    
    @classmethod
    def join(cls):
        s = []
        s.append('-----BEGIN RSA PRIVATE KEY-----')
        s.append(self.key)
        s.append('-----END RSA PRIVATE KEY-----')
        s.append('-----BEGIN CERTIFICATE-----')
        s.append(self.cert)
        s.append('-----END CERTIFICATE-----')
        return '\n'.join(s)
    
    def __init__(self, key, cert):
        self.key = key
        self.cert = cert
