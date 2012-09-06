# Copyright (c) 2010 Red Hat, Inc.
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

import unittest
import mock
import tempfile
import os
import stat
import shutil
import types

import certdata

from subscription_manager import certlib
from subscription_manager import managerlib


class TestConsumerIdenity(unittest.TestCase):
    def setUp(self):
        self.orig_perms = managerlib.ID_CERT_PERMS
        managerlib.ID_CERT_PERMS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IWGRP

        self.certpath = tempfile.mkdtemp()
        certlib.ConsumerIdentity.PATH = self.certpath
        # little redundant since the class itself does this...
        self.orig_ci = certlib.ConsumerIdentity(keystring="", certstring=certdata.IDENTITY_CERT)
        self.orig_ci.write()

    def tearDown(self):
        managerlib.ID_CERT_PERMS = self.orig_perms
        shutil.rmtree(self.certpath)

        # just to be paranoid about the monkeypatching
        certlib.ConsumerIdentity.PATH = '/etc/pki/consumer'

    def test_init(self):
        certlib.ConsumerIdentity(keystring="", certstring=certdata.IDENTITY_CERT)

    def test_read(self):
        ci = certlib.ConsumerIdentity.read()
        self.assertEquals(ci.key, self.orig_ci.key)
        self.assertEquals(ci.cert, self.orig_ci.cert)

    def test_exists_and_valid(self):
        self.assertTrue(certlib.ConsumerIdentity.existsAndValid())

    def test_exists_and_value_not(self):
        try:
            certlib.ConsumerIdentity.PATH = '/Does/Not/Exist/I/Hope'
            self.assertFalse(certlib.ConsumerIdentity.existsAndValid())
        finally:
            certlib.ConsumerIdentity.PATH = '/etc/pki/consumer'

    @mock.patch.object(certlib, 'log')
    @mock.patch.object(certlib.ConsumerIdentity, 'read')
    def test_exists_and_value_exception(self, mock_read, mock_log):
        mock_read.side_effect = IOError()
        self.assertFalse(certlib.ConsumerIdentity.existsAndValid())
        self.assertTrue(mock_log.warn.called)

    def test_get_consumer_id(self):
        ci = certlib.ConsumerIdentity.read()
        c_id = ci.getConsumerId()
        # consumer uuid of our test cert
        self.assertEquals('eaadd6ea-852d-4430-94a7-73d5887d48e8', c_id)

    def test_get_consumer_name(self):
        ci = certlib.ConsumerIdentity.read()
        c_name = ci.getConsumerName()
        # consumer name from our test cert
        self.assertEquals('redhat.local.rm-rf.ca', c_name)

    def test_get_serial_number(self):
        ci = certlib.ConsumerIdentity.read()
        c_sn = ci.getSerialNumber()
        # consumer cert sn from our test cert
        self.assertEquals(5412106042110780569, c_sn)
        # see bz 848742
        self.assertTrue(c_sn > 0)
        self.assertTrue(isinstance(c_sn, types.LongType))

    def test_str(self):
        ci = certlib.ConsumerIdentity.read()
        str = "%s" % ci
        expected = """consumer: name="redhat.local.rm-rf.ca", uuid=eaadd6ea-852d-4430-94a7-73d5887d48e8"""
        self.assertEquals(expected, str)

    def test_mkdir(self):
        ci = certlib.ConsumerIdentity.read()
        ci.PATH = '%s/somesubdir/' % tempfile.mkdtemp()

        ci.write()

    def test_delete(self):
        ci = certlib.ConsumerIdentity.read()
        ci.delete()
        self.assertFalse(os.path.exists('%s/%s' % (self.certpath, "cert.pem")))
        self.assertFalse(os.path.exists('%s/%s' % (self.certpath, "key.pem")))

#FIXME: not sure how to monkey patch PATH
#    def test_delete_wrong_path(self):
#        ci = certlib.ConsumerIdentity.read()
#        ci.PATH = '%s/somesubdir/' % tempfile.mkdtemp()
#        ci.delete()
#        self.assertFalse(os.path.exists('%s/%s' % (self.certpath, "cert.pem")))
#        self.assertFalse(os.path.exists('%s/%s' % (self.certpath, "key.pem")))

    def test_exists(self):
        self.assertTrue(certlib.ConsumerIdentity.exists())

    def test_keypath(self):
        certlib.ConsumerIdentity.keypath()

    def test_certpath(self):
        certlib.ConsumerIdentity.certpath()
