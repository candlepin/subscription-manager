from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2011 - 2012 Red Hat, Inc.
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

from rhsm.certificate import Key, Content, create_from_file, CertificateException


class CertTest(unittest.TestCase):

    def test_non_existent_file(self):
        with self.assertRaises(CertificateException):
            create_from_file("/foo/non_existent_cert.pem")


class KeyTests(unittest.TestCase):

    def test_empty_key(self):
        keyString = ""
        key = Key(keyString)
        self.assertTrue(key.bogus())

    def test_garbage_key(self):
        keyString = "Some Garbage Data"
        key = Key(keyString)
        self.assertTrue(key.bogus())

    def test_valid_key(self):
        keyString = """
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAgxWvHJCNGD8YWKKdQ3m0bMc7RjOWyoopeqAJ72DkOg41HFfU
g1rGmaQcu0OanUx4HWOcT5xevypm2jUIpUnV3BAt9vLI3oSxe8v8iivHHYmcCIFL
pP5SPNTcmn2A1O9jDtUcG6SRMBeERTBUU0GuRad7Rg0lSYOUCkvdg1XC8gLVror+
y1hE1HdPMfW7mW5aTZ+qWnNrUuFL6WC0nvL4JKOi1LyQlZlimIWxILIjs2M2s6na
mnfht2hdhf6of4cpGdOTgQ4YgPg4hlSb51yyq9KSJoova7GAvcGB2jBlvm2No7vp
j7UG+/XTivtXNPgjV3SHzSZxypnws9Kurd0QLQIDAQABAoIBAFl0js/7hY4qYL78
Gj5V697gB39c7WbC6pOYa69Ee/tyfqQc/BW3+RgYetMAy57U9JN5ys45dB8ZHJ+E
2aWSwbMwB24jORlBjK1jA7B3N6bcpfLX6XtrY0vIJ9P2Gdk2lG8m18u1fq9HHSjq
VmGKzRcTuHiRuAR3Gqv8Ierit+rXMYeCZIJ4jHkk2nyCN0C0qEmbV3naD2zDna7q
LVpVixPBgAZuBElOd+b06ICviiuTIifavw6tX+kGO2e9uhezGmE//lvYvVafReIF
rqhFsgKKfsA+tSNREDLBaOyr/lV4wuY/Roj+3FYm/CzqW+zJ++nrauDaBu2JiGBI
JZ2tcIECgYEAxsP9fp8pTj99/jv7WGbF9zaxbSrdS5Vd1ifEN4X97skGlWw43Ekh
9H6XtzrhcvEqZzjUJmoZyWaZzqdelgh9uZ4lRQiRMW72QesDTF9Hd0D9mk1iS59E
fpbUmtEc3XfKbCoC+h5UO0VBshdxqPI3OKrnwmrSVPz5h+RXphDzPekCgYEAqNSY
jy/6ZmtLrNuHeVJSy9NjvCkBqLvTH76W/fne6TRX9BvNHb0Te3EFcpih8YN6vbII
JmLOEH6QTSt1LW2khV6im+IFSYbXpg0c93CFXRKzzrBBV54j8zmTkG5RLIvVhc+1
D7mD7ve7a9FrdASr8KCl1mrLflHZKFkPQFquQaUCgYB2fc431vBL2mPk1KMw/wuT
JYK+HqiP73piOZCqvPE1kZegKkT3ZY2dcH5HWA2gdQ6fPGyUffnja4vTe0lSzbsN
la6IKeRMgObDQzPTKpWzDQZiHzGy/T5a7NXPeUvo5wnAU4c0zjHOp6nTXlB+s+6h
lJjW+NFsouaq0UBDGqW3SQKBgEYRTWuHrvVYrGSGC5iHWQNsrOTHY//iS8HN+J5Z
WHESnzoZW6xu7yn5AxjHTdaNCaC2xXkg4oKn9D2CvrPm4DPVzcjCKg2U3+TzZkUv
Nrok6+jo74VshWEJUTvM/PVu52QMiwmGpcHEoM0jceQJmE5abdkqI2A+mdCL/a9o
sw9dAoGAPxzIiKU606m7m8GKr3IuRjMPqwP7qC9HOdc+NXIyJqnK+nvwReCAIOEL
pzqLRw7mjUfdCJ5Gdx0TPYl8ckRKQAwuSWm4a8XaUCP73NCIe6e3lVn/29wsVtTI
2XQsAKrvBHQ9834wJ6XEn4j6LnUxbLIiSdV8wJqOhjRxEZKwu4w=
-----END RSA PRIVATE KEY-----
"""
        key = Key(keyString)

        self.assertFalse(key.bogus())


class ContentTests(unittest.TestCase):

    def test_compare(self):
        ext1 = {'1': 'mycontent',
               '2': 'mycontent',
               '8': True}
        c = Content(ext1)
        ext2 = {'1': 'othercontent',
                '2': 'othercontent'}
        d = c
        e = Content(ext1)
        f = Content(ext2)

        self.assertEqual(c, c)
        self.assertNotEqual(c, None)
        self.assertNotEqual(c, "not a content")
        self.assertEqual(c, d)
        self.assertEqual(c, e)
        self.assertNotEqual(c, f)
