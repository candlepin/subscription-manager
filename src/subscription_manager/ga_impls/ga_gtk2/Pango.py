from __future__ import print_function, division, absolute_import

from pango import WEIGHT_BOLD, WRAP_WORD


class WrapMode(object):
    WORD = WRAP_WORD


class Weight(object):
    BOLD = WEIGHT_BOLD


__all__ = [Weight, WrapMode]
