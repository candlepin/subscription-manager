from __future__ import print_function, division, absolute_import

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

import unittest

from rhsm.huffman import HuffmanNode


class TestHuffmanNode(unittest.TestCase):
    def setUp(self):
        self.node1 = HuffmanNode(1)
        self.node2 = HuffmanNode(2)
        self.parent = HuffmanNode.combine(self.node1, self.node2)

    def test_combine(self):
        self.assertEqual(self.parent.weight, 3)
        self.assertEqual(self.parent.left, self.node1)
        self.assertEqual(self.parent.right, self.node2)
        self.assertEqual(self.node1.parent, self.parent)
        self.assertEqual(self.node2.parent, self.parent)

    def test_build_tree(self):
        leaves = [HuffmanNode(weight) for weight in range(1, 5)]
        root = HuffmanNode.build_tree(leaves)

        # assertions based on calculating these by hand
        self.assertEqual(root.weight, 10)
        self.assertEqual(leaves[0].code, '110')
        self.assertEqual(leaves[1].code, '111')
        self.assertEqual(leaves[2].code, '10')
        self.assertEqual(leaves[3].code, '0')

        for leaf in leaves:
            self.assertTrue(leaf.is_leaf)

    def test_code_non_leaf(self):
        self.assertRaises(AttributeError, getattr, self.parent, 'code')

    def test_is_leaf(self):
        self.assertTrue(self.node1.is_leaf)
        self.assertTrue(self.node2.is_leaf)
        self.assertFalse(self.parent.is_leaf)

    def test_direction_from_parent_left(self):
        self.assertEqual(self.node1.direction_from_parent, '0')

    def test_direction_from_parent_right(self):
        self.node1.right = self.node2
        self.assertEqual(self.node2.direction_from_parent, '1')

    def test_compare_lt(self):
        self.assertTrue(self.node1 < self.node2)

    def test_compare_gt(self):
        self.assertTrue(self.node2 > self.node1)

    def test_compare_eq(self):
        node = HuffmanNode(3)
        self.assertEqual(self.parent, node)

    def test_root_weight(self):
        # sanity check that total weight should be sum of all node weights
        for n in range(4, 100):
            leaves = [HuffmanNode(weight) for weight in range(1, n)]
            tree = HuffmanNode.build_tree(leaves)
            self.assertEqual(tree.weight, sum(leaf.weight for leaf in leaves))
