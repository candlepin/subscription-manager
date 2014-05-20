#
# Copyright (c) 2014 Red Hat, Inc.
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

"""
Standalone script to fetch information about the current OSTree.

Uses pygobject3 to introspect. This does not work with gobject2 which
we use in a couple locations in core subscription-manager, so instead
we shell out to this script to get the required information.
"""

from optparse import OptionParser
from gi.repository import OSTree

parser = OptionParser()

parser.add_option("--deployed-origin", dest="deployed_origin",
    default=False, action="store_true",
    help="Print the path to the current deployed OSTree origin file.")

(options, args) = parser.parse_args()

if options.deployed_origin:
    sysroot = OSTree.Sysroot.new_default()
    sysroot.load(None)
    booted = sysroot.get_booted_deployment()
    #booted.get_osname()
    if booted:
        deploydir = sysroot.get_deployment_directory(booted)
        print(sysroot.get_deployment_origin_path(deploydir))

