from __future__ import print_function, division, absolute_import

# Copyright (c) 2017 Red Hat, Inc.
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

from unittest import TestCase
import os
import subprocess


class CompletionTest(TestCase):
    def test_posix_compliance(self):
        _root_dir = os.getcwd()
        if not os.path.exists(os.path.join(_root_dir, 'etc-conf')):
            _root_dir = os.path.join(os.getcwd(), '..')
        for name in os.listdir(os.path.join(_root_dir, 'etc-conf')):
            full_name = os.path.join(_root_dir, 'etc-conf', name)
            if name.endswith('.completion.sh'):
                subprocess.check_call(['bash', '--posix', full_name])
