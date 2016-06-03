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

import itertools
import zlib

from bitstream import GhettoBitStream
from huffman import HuffmanNode

# this is the "sentinel" value used for the path node that indicates the end
# of a path
PATH_END = 'PATH END'
LISTING = 'listing'


class PathTree(object):
    """
    This builds and makes available a tree that represents matchable paths. A
    path must be matched starting from its root and the root of the tree,
    matching one segment at a time.

    There are three trees involved in the process, and that can get confusing.

    1)  Word Tree: This is a Huffman tree made from the word list provided at
        the beginning of the data stream.
    2)  Huffman Path Tree: This is a Huffman tree made of nodes whose values
        will become nodes in the Path Tree. This tree exists so there can be
        a Huffman code associated with each node in the Path Tree. However,
        the Path Tree itself will arrange this data much differently.
    3)  Path Tree: This is the tree used to match paths. Each node is a
        dict where keys are path segments (the middle part of /.../) and each
        value is a list of other nodes.
    """

    def __init__(self, data):
        """
        Uncompresses data into a tree that can be traversed for matching paths

        :param data:    binary data as read from a file or pulled directly out
                        of a certificate extension. Data should be compressed
                        with huffman coding as described for v3 entitlement
                        certificates
        :type  data:    binary string
        """
        word_leaves, unused_bits = self._unpack_data(data)
        HuffmanNode.build_tree(word_leaves)
        word_dict = dict((node.code, node.value) for node in word_leaves)
        bitstream = GhettoBitStream(unused_bits)
        path_leaves = self._generate_path_leaves(bitstream)
        HuffmanNode.build_tree(path_leaves)
        path_dict = dict((node.code, node) for node in path_leaves)
        self.path_tree = self._generate_path_tree(
                path_dict, path_leaves, word_dict, bitstream)

    def match_path(self, path):
        """
        Given an absolute path, determines if the path tree contains any
        complete paths that exactly equal the beginning of this path. Thus,
        The tree is traversed from its root, and as long as the provided path
        does not hit its end before hitting the end of a tree path, this will
        return True.

        :param path:    absolute path to match against the tree
        :type  path:    str
        :return:        True iff there is a match, else False
        :rtype:         bool
        """
        if not path.startswith('/'):
            raise ValueError('path must start with "/"')
        return self._traverse_tree(self.path_tree, path.strip('/').split('/'))

    @classmethod
    def _traverse_tree(cls, tree, words):
        """
        Helper method for match_path that does recursive matching.

        :param tree:    A dict representing a node in the greater path tree.
        :type  tree:    dict
        :param words:   list of words to match, the result of spliting a path
                        by the "/" separator. Words must be sorted with the
                        next word to match being at words[0]
        :param words:   list
        :return:        True iff there is a match, else False
        :rtype:         bool
        """
        if PATH_END in tree:
            # we hit the end of a path in the tree, so the match was successful
            return True
        if words:
            words_to_try = []
            # Look fo an exact match
            if words[0] in tree:
                words_to_try.append(words[0])
            if words[0] == LISTING and len(words) == 1:
                return True

            # we allow any word to match against entitlement variables
            # such as "$releasever".
            for word in tree.keys():
                if word.startswith('$'):
                    words_to_try.append(word)

            for word in words_to_try:
                # keep trying for each child
                for child in tree[word]:
                    if cls._traverse_tree(child, words[1:]):
                        return True
        return False

    @staticmethod
    def _unpack_data(data):
        """
        :param data:    binary data as read from a file or pulled directly out
                        of a certificate extension. Data should be compressed
                        with huffman coding as described for v3 entitlement
                        certificates
        :type  data:    binary string
        :return:        tuple: (list of HuffmanNode instances not yet in a
                        tree, binary string of leftover bits that were not
                        part of the zlib-compressed word list
        :rtype:         tuple(list, binary string)
        """
        decompress = zlib.decompressobj()
        decompressed_data = decompress.decompress(data)
        # ordered list of words that will be composed into a huffman tree
        words = decompressed_data.split('\0')

        # enumerate() would be better here, but lacks a 'start' arg in 2.4
        weighted_words = zip(itertools.count(1), words)
        # huffman nodes, without having put them in a tree. These will all be
        # leaves in the tree.
        nodes = [
            HuffmanNode(weight, value) for weight, value in weighted_words
        ]
        return nodes, decompress.unused_data

    @staticmethod
    def _get_node_count(bitstream):
        """
        Determine the total number of nodes in the uncompressed tree. The
        algorithm for doing so is described in the v3 entitlement cert
        format documentation.

        :param bitstream:   the full bit stream following the zlib-compressed
                            word list. As defined in the v3 entitlement cert
                            format, the beginning of this stream defines how
                            many total nodes exist. This method retrieves that
                            value.
        :type  bitstream:   rhsm.bitstream.GhettoBitStream
        :return:            number of nodes
        :rtype:             int
        """
        first_byte = bitstream.pop_byte()
        # less than 128 nodes, so only the first byte is used to define the
        # length
        if first_byte < 128:
            return first_byte
        # 128 or more nodes, so first byte tells us how many more bytes are used
        # to define the number of nodes
        else:
            num_bytes = first_byte - 128
            count_bytes = [bitstream.pop_byte() for x in range(num_bytes)]
            node_count = bitstream.combine_bytes(count_bytes)
            return node_count

    @classmethod
    def _generate_path_leaves(cls, bitstream):
        """
        Given the remaining bits after decompressing the word list, this
        generates HummanNode objects to represent each node (besides root)
        that will end up in the path tree.

        :param bitstream:   stream of bits remaining after decompressing the
                            word list
        :type  bitstream:   rhsm.bitstream.GhettoBitStream
        :return:            list of HuffmanNode objects that can be used to
                            build a path tree
        :rtype:             list of HuffmanNode objects
        """
        node_count = cls._get_node_count(bitstream)
        nodes = []
        # make leaves for a huffman tree and exclude the root node of the path
        # tree, because we don't need a reference code for that.
        for weight in range(1, node_count):
            node = HuffmanNode(weight, {})
            nodes.append(node)
        return nodes

    @staticmethod
    def _get_leaf_from_dict(code_dict, bitstream):
        """
        Given a bit stream and dictionary where keys are huffman codes, return
        the value from that dictionary that corresponds to the next huffman
        code in the stream. This is a substitute for actually traversing the
        tree, and this likely performs better in large data sets.

        :param code_dict:   any dictionary where keys are huffman codes
        :type  code_dict:   dict
        :param bitstream:   bit stream with a huffman code as the next value
        :type  bitstream:   rhsm.bitstream.GhettoBitStream
        :return:            value from the dict
        """
        code = ''
        for bit in bitstream:
            code += bit
            if code in code_dict:
                return code_dict[code]

    @classmethod
    def _generate_path_tree(cls, path_dict, path_leaves, word_dict, bitstream):
        """
        Once huffman trees have been generated for the words and for the path
        nodes, this method uses them and the bit stream to create the path tree
        that can be traversed to match potentially authorized paths.

        :param path_dict:   dictionary where keys are huffman codes and values
                            are path nodes.
        :type  path_dict:   dict
        :param path_leaves: leaf nodes from the huffman tree of path nodes. the
                            values will be constructed into a new tree that can
                            be traversed to match actual paths.
        :type  path_leaves: list of HuffmanNode instances
        :param word_dict:   dict where keys are huffman codes and values are
                            words from the zlib-compressed word list.
        :type  word_dict:   dict
        :param bitstream:   bit stream where the rest of the bits describe
                            how to use words as references between nodes in
                            the path tree. This format is described in detail
                            in the v3 entitlement certificate docs.
        :type  bitstream:   rhsm.bitstream.GhettoBitStream
        """
        values = [leaf.value for leaf in path_leaves]
        root = {}
        values.insert(0, root)
        for value in values:
            while True:
                word = cls._get_leaf_from_dict(word_dict, bitstream)
                # check for end of node
                if not word:
                    break
                path_node = cls._get_leaf_from_dict(path_dict, bitstream)
                value.setdefault(word, []).append(path_node.value)
        # add the sentinel value that marks this explicitly as the end of a path
        # there should usually only be one of these nodes
        for value in values:
            if not value:
                value[PATH_END] = None

        return root
