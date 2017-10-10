from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2013 Red Hat, Inc.
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

# So we can use simplejson if it's available on rhel6, since
# is faster there, or fallback to builtin json.
#
# We can decide if the package should require it via the spec
# file.
try:
    from simplejson import *  # NOQA
except ImportError:
    from json import *  # NOQA


def encode(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(repr(obj) + " is not JSON serializable")
