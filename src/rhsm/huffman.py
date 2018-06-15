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

import heapq
import itertools


class HuffmanNode(object):
    """
    Represents a node in a Huffman tree.
    """

    def __init__(self, weight, value=None, left=None, right=None, parent=None):
        """
        :param weight:  number representing the weight/priority of this node
        :type  weight:  int
        :param value:   any value carried by this node, such as a symbol to be
                        used in reconstructing (uncompressing) some data.
        :param left:    child node on the left, should have weight <= right
        :type  left:    rhsm.huffman.HuffmanNode
        :param right:   child node on the right, should have weight >= left
        :type  right:   rhsm.huffman.HuffmanNode
        :param parent:  parent node
        :type  parent:  rhsm.huffman.HuffmanNode
        """
        self.weight = weight
        self.value = value
        self.left = left
        self.right = right
        self.parent = parent

    @classmethod
    def combine(cls, left, right):
        """
        Combine two nodes according to Huffman's tree-building algorithm. The
        weight of the left node should be <= that of the right node. If weights
        are equal, left should be the node that was in the queue longer. This
        creates a new node and sets it as the parent attribute of each child.

        :param left:    child node on the left, should have weight <= right
        :type  left:    rhsm.huffman.HuffmanNode
        :param right:   child node on the right, should have weight >= left
        :type  right:   rhsm.huffman.HuffmanNode

        :return:        new node that is the combination of left and right
        :rtype:         rhsm.huffman.HuffmanNode
        """
        node = cls(left.weight + right.weight, None, left, right)
        left.parent = node
        right.parent = node
        return node

    @property
    def is_leaf(self):
        """
        :return:    True iff left and right are None, else False
        :rtype:     bool
        """
        return self.right is None and self.left is None

    @property
    def direction_from_parent(self):
        """
        :return:    '0' if self is left of its parent, or '1' if right of parent.
        :rtype:     str
        """
        if self.parent is None:
            raise AttributeError
        if self.parent.left is self:
            return '0'
        else:
            return '1'

    @property
    def code(self):
        """
        :return:    Huffman code for this node as a series of characters '0' and '1'
        :rtype:     str
        """
        if not self.is_leaf:
            raise AttributeError('node is not a leaf')
        turns = []
        next_node = self
        while next_node is not None:
            if next_node.parent is not None:
                turns.insert(0, next_node.direction_from_parent)
            next_node = next_node.parent
        return ''.join(turns)

    @classmethod
    def build_tree(cls, nodes):
        """
        :param nodes:   list of HuffmanNode instances that will become leaves
                        in a Huffman tree.
        :type  nodes:   list
        :return:        HuffmanNode instance that is the root node of the tree
        :rtype:         rhsm.huffman.HuffmanNode
        """
        # the counter makes sure that when nodes of equal weight are compared,
        # the one most recently added gets chosen
        counter = itertools.count()
        # We use the heapq module to make a min priority queue
        queue = [(node, next(counter)) for node in nodes]
        heapq.heapify(queue)
        while True:
            left, count = heapq.heappop(queue)
            try:
                right, count = heapq.heappop(queue)
            except IndexError:
                # no more nodes to compare, so a is the root node of the tree
                return left
            heapq.heappush(queue, (cls.combine(left, right), next(counter)))

    def __lt__(self, other):
        return self.weight < other.weight

    def __le__(self, other):
        return self.weight <= other.weight

    def __gt__(self, other):
        return self.weight > other.weight

    def __ge__(self, other):
        return self.weight >= other.weight

    def __eq__(self, other):
        if not hasattr(other, 'weight'):
            return False
        return self.weight == other.weight

    def __ne__(self, other):
        if not hasattr(other, 'weight'):
            return True
        return self.weight != other.weight

    def __hash__(self):
        return self.value

    def __repr__(self):
        return 'HuffmanNode(%d, "%s")' % (self.weight, self.value)
