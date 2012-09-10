#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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


import os
import logging

from rhsm.certificate import Key, create_from_file

from rhsm.config import initConfig


log = logging.getLogger('rhsm-app.' + __name__)

import gettext
_ = gettext.gettext

cfg = initConfig()


class Directory:

    def __init__(self, path):
        self.path = Path.abs(path)

    def listAll(self):
        all_items = []
        if not os.path.exists(self.path):
            return all_items

        for fn in os.listdir(self.path):
            p = (self.path, fn)
            all_items.append(p)
        return all_items

    def list(self):
        files = []
        for p, fn in self.listAll():
            path = self.abspath(fn)
            if Path.isdir(path):
                continue
            else:
                files.append((p, fn))
        return files

    def listdirs(self):
        dirs = []
        for p, fn in self.listAll():
            path = self.abspath(fn)
            if Path.isdir(path):
                dirs.append(Directory(path))
        return dirs

    def create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def delete(self):
        self.clean()
        os.rmdir(self.path)

    def clean(self):
        if not os.path.exists(self.path):
            return

        for x in os.listdir(self.path):
            path = self.abspath(x)
            if Path.isdir(path):
                d = Directory(path)
                d.delete()
            else:
                os.unlink(path)

    def abspath(self, filename):
        """
        Return path for a filename relative to this directory.
        """
        # NOTE: self.path is already aware of the Path.ROOT setting, so we
        # can just join normally.
        return os.path.join(self.path, filename)

    def __str__(self):
        return self.path


class CertificateDirectory(Directory):

    KEY = 'key.pem'

    def __init__(self, path):
        Directory.__init__(self, path)
        self.create()
        self._listing = None

    def refresh(self):
        # simply clear the cache. the next list() will reload.
        self._listing = None

    def list(self):
        if self._listing is not None:
            return self._listing
        listing = []
        for p, fn in Directory.list(self):
            if not fn.endswith('.pem') or fn.endswith(self.KEY):
                continue
            path = self.abspath(fn)
            listing.append(create_from_file(path))
        self._listing = listing
        return listing

    def listValid(self):
        valid = []
        for c in self.list():
            if c.is_valid():
                valid.append(c)
        return valid

    def listExpired(self):
        expired = []
        for c in self.list():
            if c.is_expired():
                expired.append(c)
        return expired

    def find(self, sn):
        # TODO: could optimize to just load SERIAL.pem? Maybe not in all cases.
        for c in self.list():
            if c.serial == sn:
                return c
        return None

    def findAllByProduct(self, p_hash):
        certs = []
        for c in self.list():
            for p in c.products:
                if p.id == p_hash:
                    certs.append(c)
        return certs

    def findByProduct(self, p_hash):
        for c in self.list():
            for p in c.products:
                if p.id == p_hash:
                    return c
        return None


class ProductDirectory(CertificateDirectory):

    PATH = cfg.get('rhsm', 'productCertDir')

    def __init__(self):
        CertificateDirectory.__init__(self, self.PATH)

    def get_provided_tags(self):
        """
        Iterates all product certificates in the directory and extracts a master
        set of all tags they provide.
        """
        tags = set()
        for prod_cert in self.listValid():
            for product in prod_cert.products:
                for tag in product.provided_tags:
                    tags.add(tag)
        return tags


class EntitlementDirectory(CertificateDirectory):

    PATH = cfg.get('rhsm', 'entitlementCertDir')
    PRODUCT = 'product'

    @classmethod
    def productpath(cls):
        return cls.PATH

    def __init__(self):
        CertificateDirectory.__init__(self, self.productpath())

    def _check_key(self, cert):
        """
        If the new key file (SERIAL-key.pem) does not exist, check for
        the old style (key.pem), and if found write it out as the new style.

        Return false if neither is found, indicating we have no key for this
        certificate.

        See bz #711133.
        """
        key_path = "%s/%s-key.pem" % (self.path, cert.serial)
        if not os.access(key_path, os.R_OK):
            # read key from old key path
            old_key_path = "%s/key.pem" % self.path

            # if we don't have a new style or old style key, consider the
            # cert invalid
            if not os.access(old_key_path, os.R_OK):
                return False

            # write the key/cert out again in new style format
            key = Key.read(old_key_path)
            cert_writer = Writer(self)
            cert_writer.write(key, cert)
        return True

    def listValid(self):
        valid = []
        for c in self.list():

            # If something is amiss with the key for this certificate, consider
            # it invalid:
            if not self._check_key(c):
                continue

            if c.is_valid():
                valid.append(c)

        return valid


class Path:

    # Used during Anaconda install by the yum pidplugin to ensure we operate
    # beneath /mnt/sysimage/ instead of /.
    ROOT = '/'

    @classmethod
    def join(cls, a, b):
        path = os.path.join(a, b)
        return cls.abs(path)

    @classmethod
    def abs(cls, path):
        """ Append the ROOT path to the given path. """
        if os.path.isabs(path):
            return os.path.join(cls.ROOT, path[1:])
        else:
            return os.path.join(cls.ROOT, path)

    @classmethod
    def isdir(cls, path):
        return os.path.isdir(path)


class Writer:

    def __init__(self, entitlement_dir=None):
        self.entdir = entitlement_dir or EntitlementDirectory()

    def write(self, key, cert):
        serial = cert.serial
        ent_dir_path = self.entdir.productpath()

        key_filename = '%s-key.pem' % str(serial)
        key_path = Path.join(ent_dir_path, key_filename)
        key.write(key_path)

        cert_filename = '%s.pem' % str(serial)
        cert_path = Path.join(ent_dir_path, cert_filename)
        cert.write(cert_path)
