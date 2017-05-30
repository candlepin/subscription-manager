from __future__ import print_function, division, absolute_import

#
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
#


class ListingFile(object):
    def __init__(self, data=None):
        self.data = data
        self.releases = []

        self.parse()

    def get_releases(self):
        return self.releases

    def parse(self):
        if not self.data:
            return

        lines = self.data.split("\n")

        for line in lines:
            line = line.strip()

            # empty
            if not line:
                continue

            # ignore comments
            if line and line[0] == '#':
                continue

            self.releases.append(line)

        self.releases.sort()
