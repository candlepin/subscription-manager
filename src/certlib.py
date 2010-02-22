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


import os
from connection import UEPConnection as UEP
from certificate import ProductCertificate, Bundle
from logutil import getLogger

log = getLogger(__name__)


class CertLib:
    
    def update(self):
        pass
        
    def add(self, *bundles):
        for b in bundles:
            self.writeBundle(Bundle.split(b))
        return self
    
    def writeBundle(self, bundle):
        path = CertificateDirectory.keypath()
        f = open(path, 'w')
        f.write(bundle.key)
        f.close()
        cert = ProductCertificate(bundle.cert)
        product = cert.getProduct()
        path = CertificateDirectory.productpath()
        fn = '%s.pem' % product.getName()
        path = os.path.join(path, fn)
        f = open(path)
        f.write(bundle.cert)
        f.close()
    
    def fetch(self, serialnumbers):
        pass


class Directory:
    
    def __init__(self, path):
        self.path = path
        
    def list(self):
        entries = []
        for fn in os.listdir(self.path):
            p = (self.path, fn)
            entries.append(p)
        return entries
    
    def listdirs(self):
        dir = []
        for p,fn in self.list():
            path = os.path.join(p, fn)
            if os.path.isdir(path):
                dir.append(Directory(path))
        return dir
    
    def create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            
    def delete(self):
        self.clean()
        os.rmdir(self.path)
            
    def clean(self):
        for x in os.listdir(self.path):
            path = os.path.join(self.path, x)
            if os.path.isdir(path):
                d = Directory(path)
                d.delete()
            else:
                os.remove(path)
    
    def __str__(self):
        return self.path

    
class CertificateDirectory(Directory):
    
    ROOT = '/etc/pki/entitlement'
    KEY = 'key.pem'
    PRODUCT = 'product'
    
    @classmethod
    def keypath(cls):
        return os.path.join(cls.ROOT, cls.KEY)
    
    @classmethod
    def productpath(cls):
        return os.path.join(cls.ROOT, cls.PRODUCT)
    
    def __init__(self):
        Directory.__init__(self, self.productpath())
        self.create()
        
    def list(self):
        valid = []
        for p,fn in Directory.list(self):
            if not fn.endswith('.pem'):
                continue
            path = os.path.join(p, fn)
            crt = ProductCertificate.read(path)
            crt.path = path
            if crt.valid():
                valid.append(crt)
        return valid
