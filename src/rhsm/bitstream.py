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
from typing import List, Union


class GhettoBitStream:
    """
    Accepts binary data and makes it available as a stream of bits or one byte
    at a time. Python does not provide a built-in way to read a stream of bits,
    or a way to represent a single bit. Thus, this class uses character '0'
    or '1' to represent the status of each bit.

    Data is converted into the '0' and '1' characters one byte at a time, since
    that operation multiplies the size of the data by a factor of 8, and it may
    not be desirable to inflate all the data at once.
    """

    def __init__(self, data: Union[bytes, str]) -> None:
        """
        :param data:    binary data in a string
        """
        self.bytes = deque(bytearray(data))
        self._bit_buffer = deque()

    def __iter__(self) -> "GhettoBitStream":
        return self

    def __next__(self) -> str:
        """
        converts one byte at a time into a bit representation, waiting until
        those bits have been consumed before converting another byte

        :return:    next bit in the stream, either '0' or '1'
        :rtype:     string
        """
        if not self._bit_buffer:
            try:
                byte: int = self.pop_byte()
            except IndexError:
                raise StopIteration
            bits: str = self._byte_to_bits(byte)
            self._bit_buffer.extend(bits)
        return self._bit_buffer.popleft()

    def pop_byte(self) -> int:
        """
        :return:    next entire byte in the stream, as an int
        """
        return self.bytes.popleft()

    @classmethod
    def _byte_to_bits(cls, byte: int) -> str:
        """
        Produces a string representation of a byte as a base-2 number.
        Python versions < 2.6 lack the "bin()" builtin as well as the
        below "format()" method of strings, so this method falls back
        to using a home-brew implementation.

        :param byte:    positive int < 256
        :return:        binary representation of byte as 8-char string
        """
        try:
            return "{0:08b}".format(byte)
        except AttributeError:
            # python < 2.6, so we must do this ourselves
            return cls._bin_backport(byte)

    @staticmethod
    def _bin_backport(x: int) -> str:
        """
        In python versions < 2.6, there is no built-in way to produce a string
        representation of base-2 data. Thus, we have to do it manually.

        :param byte:    positive int < 256
        :return:        binary representation of byte as 8-char string
        """
        chars: List[str] = []
        for n in range(7, -1, -1):
            y: int = x - 2**n
            if y >= 0:
                chars.append("1")
                x = y
            else:
                chars.append("0")
        return "".join(chars)

    @staticmethod
    def combine_bytes(data: List[int]) -> int:
        """
        combine unsigned ints read from a bit stream into one unsigned number,
        reading data as big-endian

        :param data:    iterable of positive ints, each representing a byte of
                        uint binary data that should be combined
                        such that the right-most byte stays as-is, and then
                        each byte to the left gets left-shifted by 8 * n bits.
                        For example, [1, 2] would give you 258 ((1 << 8) + 2)
        :type  data:    iterable of positive ints
        :return:        positive int, composed from input bytes combined as
                        one int
        """
        copy: List[int] = data[:]
        copy.reverse()
        return sum(x << n * 8 for n, x in enumerate(copy))
