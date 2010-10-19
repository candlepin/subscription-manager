#
# Copyright (c) 2010 Red Hat, Inc.
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

import unittest
from repolib import Repo


class RepoTests(unittest.TestCase):
    """
    Tests for the repolib Repo class
    """

    def test_valid_label_for_id(self):
        id = 'valid-label'
        repo = Repo(id)
        self.assertEquals(id, repo.id)

    def test_invalid_label_with_spaces(self):
        id = 'label with spaces'
        repo = Repo(id)
        self.assertEquals('label-with-spaces', repo.id)
