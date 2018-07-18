# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
# Copyright (c) 2010 Ville Skyttä
# Copyright (c) 2009 Tim Lauridsen
# Copyright (c) 2007 Marcus Kuhn
#
# kitchen is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# kitchen is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
# more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with kitchen; if not, see <http://www.gnu.org/licenses/>
#
# Authors:
#   James Antill <james@fedoraproject.org>
#   Marcus Kuhn
#   Toshio Kuratomi <toshio@fedoraproject.org>
#   Tim Lauridsen
#   Ville Skyttä
#
# Portions of this are from yum/i18n.py
# NOTE: originally from kitchen,
#   see https://github.com/fedora-infra/kitchen/blob/develop/kitchen2/kitchen/text/display.py
"""
-----------------------
Format Text for Display
-----------------------

Functions related to displaying unicode text.  Unicode characters don't all
have the same width so we need helper functions for displaying them.

.. versionadded:: 0.2 kitchen.display API 1.0.0
"""

# This is ported from ustr_utf8_* which I got from:
#     http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c
#  I've tried to leave it close to the original C (same names etc.) so that
# it is easy to read/compare both versions... James Antilles

#
# Reimplemented quite a bit of this for speed.  Use the bzr log or annotate
# commands to see what I've changed since importing this file.-Toshio Kuratomi

# ----------------------------- BEG utf8 ------------------to-----------
# This is an implementation of wcwidth() and wcswidth() (defined in
# IEEE Std 1002.1-2001) for Unicode.
#
# http://www.opengroup.org/onlinepubs/007904975/functions/wcwidth.html
# http://www.opengroup.org/onlinepubs/007904975/functions/wcswidth.html
#
# In fixed-width output devices, Latin characters all occupy a single
# "cell" position of equal width, whereas ideographic CJK characters
# occupy two such cells. Interoperability between terminal-line
# applications and (teletype-style) character terminals using the
# UTF-8 encoding requires agreement on which character should advance
# the cursor by how many cell positions. No established formal
# standards exist at present on which Unicode character shall occupy
# how many cell positions on character terminals. These routines are
# a first attempt of defining such behavior based on simple rules
# applied to data provided by the Unicode Consortium.
#
# [...]
#
# Markus Kuhn -- 2007-05-26 (Unicode 5.0)
#
# Permission to use, copy, modify, and distribute this software
# for any purpose and without fee is hereby granted. The author
# disclaims all warranties with regard to this software.
#
# Latest version: http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c


# Renamed but still pretty much JA's port of MK's code
def _interval_bisearch(value, table):
    """Binary search in an interval table.

    :arg value: numeric value to search for
    :arg table: Ordered list of intervals.  This is a list of two-tuples.  The
        elements of the two-tuple define an interval's start and end points.
    :returns: If :attr:`value` is found within an interval in the :attr:`table`
        return :data:`True`.  Otherwise, :data:`False`

    This function checks whether a numeric value is present within a table
    of intervals.  It checks using a binary search algorithm, dividing the
    list of values in half and checking against the values until it determines
    whether the value is in the table.
    """
    minimum = 0
    maximum = len(table) - 1
    if value < table[minimum][0] or value > table[maximum][1]:
        return False

    while maximum >= minimum:
        mid = divmod(minimum + maximum, 2)[0]
        if value > table[mid][1]:
            minimum = mid + 1
        elif value < table[mid][0]:
            maximum = mid - 1
        else:
            return True

    return False


_COMBINING = (
        (0x300, 0x36f), (0x483, 0x489), (0x591, 0x5bd),
        (0x5bf, 0x5bf), (0x5c1, 0x5c2), (0x5c4, 0x5c5),
        (0x5c7, 0x5c7), (0x600, 0x603), (0x610, 0x61a),
        (0x64b, 0x65f), (0x670, 0x670), (0x6d6, 0x6e4),
        (0x6e7, 0x6e8), (0x6ea, 0x6ed), (0x70f, 0x70f),
        (0x711, 0x711), (0x730, 0x74a), (0x7a6, 0x7b0),
        (0x7eb, 0x7f3), (0x816, 0x819), (0x81b, 0x823),
        (0x825, 0x827), (0x829, 0x82d), (0x859, 0x85b),
        (0x8d4, 0x8e1), (0x8e3, 0x8ff), (0x901, 0x902),
        (0x93c, 0x93c), (0x941, 0x948), (0x94d, 0x94d),
        (0x951, 0x954), (0x962, 0x963), (0x981, 0x981),
        (0x9bc, 0x9bc), (0x9c1, 0x9c4), (0x9cd, 0x9cd),
        (0x9e2, 0x9e3), (0xa01, 0xa02), (0xa3c, 0xa3c),
        (0xa41, 0xa42), (0xa47, 0xa48), (0xa4b, 0xa4d),
        (0xa70, 0xa71), (0xa81, 0xa82), (0xabc, 0xabc),
        (0xac1, 0xac5), (0xac7, 0xac8), (0xacd, 0xacd),
        (0xae2, 0xae3), (0xb01, 0xb01), (0xb3c, 0xb3c),
        (0xb3f, 0xb3f), (0xb41, 0xb43), (0xb4d, 0xb4d),
        (0xb56, 0xb56), (0xb82, 0xb82), (0xbc0, 0xbc0),
        (0xbcd, 0xbcd), (0xc3e, 0xc40), (0xc46, 0xc48),
        (0xc4a, 0xc4d), (0xc55, 0xc56), (0xcbc, 0xcbc),
        (0xcbf, 0xcbf), (0xcc6, 0xcc6), (0xccc, 0xccd),
        (0xce2, 0xce3), (0xd3b, 0xd3c), (0xd41, 0xd43),
        (0xd4d, 0xd4d), (0xdca, 0xdca), (0xdd2, 0xdd4),
        (0xdd6, 0xdd6), (0xe31, 0xe31), (0xe34, 0xe3a),
        (0xe47, 0xe4e), (0xeb1, 0xeb1), (0xeb4, 0xeb9),
        (0xebb, 0xebc), (0xec8, 0xecd), (0xf18, 0xf19),
        (0xf35, 0xf35), (0xf37, 0xf37), (0xf39, 0xf39),
        (0xf71, 0xf7e), (0xf80, 0xf84), (0xf86, 0xf87),
        (0xf90, 0xf97), (0xf99, 0xfbc), (0xfc6, 0xfc6),
        (0x102d, 0x1030), (0x1032, 0x1032), (0x1036, 0x1037),
        (0x1039, 0x103a), (0x1058, 0x1059), (0x108d, 0x108d),
        (0x1160, 0x11ff), (0x135d, 0x135f), (0x1712, 0x1714),
        (0x1732, 0x1734), (0x1752, 0x1753), (0x1772, 0x1773),
        (0x17b4, 0x17b5), (0x17b7, 0x17bd), (0x17c6, 0x17c6),
        (0x17c9, 0x17d3), (0x17dd, 0x17dd), (0x180b, 0x180d),
        (0x18a9, 0x18a9), (0x1920, 0x1922), (0x1927, 0x1928),
        (0x1932, 0x1932), (0x1939, 0x193b), (0x1a17, 0x1a18),
        (0x1a60, 0x1a60), (0x1a75, 0x1a7c), (0x1a7f, 0x1a7f),
        (0x1ab0, 0x1abd), (0x1b00, 0x1b03), (0x1b34, 0x1b34),
        (0x1b36, 0x1b3a), (0x1b3c, 0x1b3c), (0x1b42, 0x1b42),
        (0x1b44, 0x1b44), (0x1b6b, 0x1b73), (0x1baa, 0x1bab),
        (0x1be6, 0x1be6), (0x1bf2, 0x1bf3), (0x1c37, 0x1c37),
        (0x1cd0, 0x1cd2), (0x1cd4, 0x1ce0), (0x1ce2, 0x1ce8),
        (0x1ced, 0x1ced), (0x1cf4, 0x1cf4), (0x1cf8, 0x1cf9),
        (0x1dc0, 0x1df9), (0x1dfb, 0x1dff), (0x200b, 0x200f),
        (0x202a, 0x202e), (0x2060, 0x2063), (0x206a, 0x206f),
        (0x20d0, 0x20f0), (0x2cef, 0x2cf1), (0x2d7f, 0x2d7f),
        (0x2de0, 0x2dff), (0x302a, 0x302f), (0x3099, 0x309a),
        (0xa66f, 0xa66f), (0xa674, 0xa67d), (0xa69e, 0xa69f),
        (0xa6f0, 0xa6f1), (0xa806, 0xa806), (0xa80b, 0xa80b),
        (0xa825, 0xa826), (0xa8c4, 0xa8c4), (0xa8e0, 0xa8f1),
        (0xa92b, 0xa92d), (0xa953, 0xa953), (0xa9b3, 0xa9b3),
        (0xa9c0, 0xa9c0), (0xaab0, 0xaab0), (0xaab2, 0xaab4),
        (0xaab7, 0xaab8), (0xaabe, 0xaabf), (0xaac1, 0xaac1),
        (0xaaf6, 0xaaf6), (0xabed, 0xabed), (0xfb1e, 0xfb1e),
        (0xfe00, 0xfe0f), (0xfe20, 0xfe2f), (0xfeff, 0xfeff),
        (0xfff9, 0xfffb), (0x101fd, 0x101fd), (0x102e0, 0x102e0),
        (0x10376, 0x1037a), (0x10a01, 0x10a03), (0x10a05, 0x10a06),
        (0x10a0c, 0x10a0f), (0x10a38, 0x10a3a), (0x10a3f, 0x10a3f),
        (0x10ae5, 0x10ae6), (0x11046, 0x11046), (0x1107f, 0x1107f),
        (0x110b9, 0x110ba), (0x11100, 0x11102), (0x11133, 0x11134),
        (0x11173, 0x11173), (0x111c0, 0x111c0), (0x111ca, 0x111ca),
        (0x11235, 0x11236), (0x112e9, 0x112ea), (0x1133c, 0x1133c),
        (0x1134d, 0x1134d), (0x11366, 0x1136c), (0x11370, 0x11374),
        (0x11442, 0x11442), (0x11446, 0x11446), (0x114c2, 0x114c3),
        (0x115bf, 0x115c0), (0x1163f, 0x1163f), (0x116b6, 0x116b7),
        (0x1172b, 0x1172b), (0x11a34, 0x11a34), (0x11a47, 0x11a47),
        (0x11a99, 0x11a99), (0x11c3f, 0x11c3f), (0x11d42, 0x11d42),
        (0x11d44, 0x11d45), (0x16af0, 0x16af4), (0x16b30, 0x16b36),
        (0x1bc9e, 0x1bc9e), (0x1d165, 0x1d169), (0x1d16d, 0x1d182),
        (0x1d185, 0x1d18b), (0x1d1aa, 0x1d1ad), (0x1d242, 0x1d244),
        (0x1e000, 0x1e006), (0x1e008, 0x1e018), (0x1e01b, 0x1e021),
        (0x1e023, 0x1e024), (0x1e026, 0x1e02a), (0x1e8d0, 0x1e8d6),
        (0x1e944, 0x1e94a), (0xe0001, 0xe0001), (0xe0020, 0xe007f),
        (0xe0100, 0xe01ef), )


# Handling of control chars rewritten.  Rest is JA's port of MK's C code.
# -Toshio Kuratomi
# NOTE: Removed unused functionality (see note in docstring) - subscription-manager developers
def _ucp_width(ucs):
    """Get the :term:`textual width` of a ucs character

    :arg ucs: integer representing a single unicode :term:`code point`

    :returns: :term:`textual width` of the character.

    .. note::

        It's important to remember this is :term:`textual width` and not the
        number of characters or bytes.

        Some modifications were made when importing into subscription-manager; namely:
         - control character handling simplified
    """
    if _interval_bisearch(ucs, _COMBINING):
        # Combining characters return 0 width as they will be combined with
        # the width from other characters
        return 0

    if ucs <= 0x1f:
        return 0

    # if we arrive here, ucs is not a combining character

    return (1 +
      (ucs >= 0x1100 and
       (ucs <= 0x115f or                      # Hangul Jamo init. consonants
        ucs == 0x2329 or ucs == 0x232a or
        (ucs >= 0x2e80 and ucs <= 0xa4cf and
         ucs != 0x303f) or                    # CJK ... Yi
        (ucs >= 0xac00 and ucs <= 0xd7a3) or  # Hangul Syllables
        (ucs >= 0xf900 and ucs <= 0xfaff) or  # CJK Compatibility Ideographs
        (ucs >= 0xfe10 and ucs <= 0xfe19) or  # Vertical forms
        (ucs >= 0xfe30 and ucs <= 0xfe6f) or  # CJK Compatibility Forms
        (ucs >= 0xff00 and ucs <= 0xff60) or  # Fullwidth Forms
        (ucs >= 0xffe0 and ucs <= 0xffe6) or
        (ucs >= 0x20000 and ucs <= 0x2fffd) or
        (ucs >= 0x30000 and ucs <= 0x3fffd))))


# Wholly rewritten by me (LGPLv2+) -Toshio Kuratomi
# NOTE: Removed unused functionality (see note in docstring) - subscription-manager developers
def textual_width(msg):
    """Get the :term:`textual width` of a string

    :arg msg: :class:`str` string or byte :class:`bytes` to get the width of

    :returns: :term:`Textual width` of the :attr:`msg`.  This is the amount of
        space that the string will consume on a monospace display.  It's
        measured in the number of cell positions or columns it will take up on
        a monospace display.  This is **not** the number of glyphs that are in
        the string.

    .. note::

        This function can be wrong sometimes because Unicode does not specify
        a strict width value for all of the :term:`code points`.  In
        particular, we've found that some Tamil characters take up to four
        character cells but we return a lesser amount.

        Some modifications were made when importing into subscription-manager; namely:
         - simplified implementation to be both Python 2 and Python 3 compatible
         - control character handling simplified
         - we always pass unicode to the function, so no need to convert to unicode
    """
    # Add the width of each char
    return sum(_ucp_width(ord(char)) for char in msg)
