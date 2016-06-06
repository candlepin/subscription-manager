# Copyright (c) 2012 Red Hat, Inc.
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

import os
import unittest
import zlib

from rhsm.bitstream import GhettoBitStream

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'entitlement_data.bin')
entitlement_data = open(DATA).read()
decompresser = zlib.decompressobj()
decompresser.decompress(entitlement_data)
tree_data = decompresser.unused_data


class TestGhettoBitStream(unittest.TestCase):
    def setUp(self):
        self.bs = GhettoBitStream(tree_data)

    def test_pop_byte(self):
        length = len(self.bs.bytes)
        first = self.bs.pop_byte()
        self.assertEqual(first, 5)
        self.assertEqual(len(self.bs.bytes), length - 1)

    def test_as_iterator(self):
        self.bs.next()
        self.assertTrue(list(self.bs))

    def test_bit_buffer(self):
        byte_count = len(self.bs.bytes)
        # empty buffer
        self.assertEqual(len(self.bs._bit_buffer), 0)

        self.bs.next()
        # one byte decoded, then one bit consumed
        self.assertEqual(len(self.bs._bit_buffer), 7)
        # one byte removed
        self.assertEqual(len(self.bs.bytes), byte_count - 1)

        self.bs.next()
        # another bit consumed
        self.assertEqual(len(self.bs._bit_buffer), 6)
        # remaining bytes still stand
        self.assertEqual(len(self.bs.bytes), byte_count - 1)

    def test_byte_to_bits(self):
        # just spot-checking
        self.assertEqual(self.bs._byte_to_bits(0), '00000000')
        self.assertEqual(self.bs._byte_to_bits(6), '00000110')
        self.assertEqual(self.bs._byte_to_bits(213), '11010101')

    def test_bin_backport(self):
        # just spot-checking
        self.assertEqual(self.bs._bin_backport(0), '00000000')
        self.assertEqual(self.bs._bin_backport(6), '00000110')
        self.assertEqual(self.bs._bin_backport(213), '11010101')

    def test_combine_bytes(self):
        # just spot-checking
        self.assertEqual(self.bs.combine_bytes([1, 3]), 259)
        self.assertEqual(self.bs.combine_bytes([3]), 3)
        self.assertEqual(self.bs.combine_bytes([1, 1, 3]), 65795)
