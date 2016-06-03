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

from collections import deque
import os
import unittest

from rhsm.bitstream import GhettoBitStream
from rhsm.huffman import HuffmanNode
from rhsm.pathtree import PathTree, PATH_END

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'entitlement_data.bin')


class TestPathTree(unittest.TestCase):
    def test_get_leaf_from_dict(self):
        codes = {'1010': 'abc'}
        bitstream = '10101111110000'
        ret = PathTree._get_leaf_from_dict(codes, bitstream)
        self.assertEqual(ret, 'abc')

    # see v3 entitlement cert format docs for explanation of how node count
    # is represented, which will explain the following tests

    def test_get_node_count_small(self):
        bs = GhettoBitStream([])
        bs.bytes = deque([6])
        ret = PathTree._get_node_count(bs)
        self.assertEqual(ret, 6)

    def test_get_node_count_medium(self):
        bs = GhettoBitStream([])
        # count bigger than 127, only need 1 byte to represent it
        bs.bytes = deque([129, 150])
        ret = PathTree._get_node_count(bs)
        self.assertEqual(ret, 150)

    def test_get_node_count_big(self):
        bs = GhettoBitStream([])
        # count bigger than 127, need next 2 bytes to represent it
        bs.bytes = deque([130, 1, 17])
        ret = PathTree._get_node_count(bs)
        self.assertEqual(ret, 273)

    def test_unpack_data(self):
        data = open(DATA).read()
        nodes, bits = PathTree._unpack_data(data)
        self.assertEqual(len(nodes), 6)
        # first node always gets weight of 1
        self.assertEqual(nodes[0].weight, 1)
        self.assertEqual(nodes[0].value, 'never')
        self.assertEqual(nodes[5].weight, 6)
        self.assertEqual(nodes[5].value, '')
        self.assertEqual(len(bits), 6)

    def test_generate_path_leaves(self):
        data = open(DATA).read()
        nodes, bits = PathTree._unpack_data(data)
        ret = PathTree._generate_path_leaves(GhettoBitStream(bits))

        self.assertEqual(len(ret), 4)
        for node in ret:
            self.assertTrue(isinstance(node, HuffmanNode))

    def test_generate_path_tree(self):
        data = open(DATA).read()
        pt = PathTree(data).path_tree
        self.assertTrue('foo' in pt)
        self.assertEqual(len(pt.keys()), 1)

    def test_match_path(self):
        data = open(DATA).read()
        pt = PathTree(data)
        self.assertTrue(pt.match_path('/foo/path'))
        self.assertTrue(pt.match_path('/foo/path/'))
        # the '2' should match against "$releasever"
        self.assertTrue(pt.match_path('/foo/path/always/2'))
        self.assertTrue(pt.match_path('/foo/path/bar'))
        self.assertTrue(pt.match_path('/foo/path/bar/a/b/c'))
        self.assertFalse(pt.match_path('/foo'))
        self.assertFalse(pt.match_path('/bar'))

    def test_match_path_listing(self):
        tree = {'foo': [{'path': [{'bar': [{PATH_END: None}]}]}]}
        data = open(DATA).read()
        pt = PathTree(data)
        pt.path_tree = tree
        self.assertTrue(pt.match_path('/foo/path/bar/listing'))
        self.assertTrue(pt.match_path('/foo/path/listing'))
        self.assertTrue(pt.match_path('/foo/listing'))
        self.assertFalse(pt.match_path('/foo/path/alfred'))
        self.assertFalse(pt.match_path('/foo/path/listing/for/alfred'))

    def test_match_variable(self):
        tree = {'foo': [{'$releasever': [{'bar': [{PATH_END: None}]}]}]}
        data = open(DATA).read()
        pt = PathTree(data)
        # just swap out the pre-cooked data with out with
        pt.path_tree = tree
        self.assertTrue(pt.match_path('/foo/path/bar'))
        self.assertFalse(pt.match_path('/foo/path/abc'))

    def test_match_first_variable(self):
        tree = {'$anything': [{'$releasever': [{'bar': [{PATH_END: None}]}]}]}
        data = open(DATA).read()
        pt = PathTree(data)
        # just swap out the pre-cooked data with out with
        pt.path_tree = tree
        self.assertTrue(pt.match_path('/foo/path/bar'))
        self.assertFalse(pt.match_path('/foo/path/abc'))

    def test_match_last_variable(self):
        tree = {'foo': [{'$releasever': [{'$bar': [{PATH_END: None}]}]}]}
        data = open(DATA).read()
        pt = PathTree(data)
        # just swap out the pre-cooked data with out with
        pt.path_tree = tree
        self.assertTrue(pt.match_path('/foo/path/bar'))
        self.assertTrue(pt.match_path('/foo/path/abc'))
        self.assertFalse(pt.match_path('/boo/path/abc'))

    def test_match_different_variables(self):
        tree1 = {'foo': [{'$releasever': [{'bar': [{PATH_END: None}]}],
                         'jarjar': [{'binks': [{PATH_END: None}]}]}]}
        tree2 = {'foo': [{'jarjar': [{'binks': [{PATH_END: None}]}],
                         '$releasever': [{'bar': [{PATH_END: None}]}]}]}
        tree3 = {'foo': [{'$releasever': [{'bar': [{PATH_END: None}]}]},
                         {'jarjar': [{'binks': [{PATH_END: None}]}]}]}
        tree4 = {'foo': [{'jarjar': [{'binks': [{PATH_END: None}]}]},
                         {'$releasever': [{'bar': [{PATH_END: None}]}]}]}
        trees = [tree1, tree2, tree3, tree4]
        data = open(DATA).read()
        pt = PathTree(data)
        #just swap out the pre-cooked data with out with
        for tree in trees:
            pt.path_tree = tree
            self.assertTrue(pt.match_path('/foo/path/bar'))
            self.assertFalse(pt.match_path('/foo/path/abc'))
            self.assertFalse(pt.match_path('/foo/path/abc'))
            self.assertTrue(pt.match_path('/foo/jarjar/binks'))
            self.assertTrue(pt.match_path('/foo/jarjar/bar'))
            self.assertFalse(pt.match_path('/foo/jarjar/notbinks'))
