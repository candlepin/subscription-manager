from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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
from subscription_manager.cli import CLI
from rct.cert_commands import CatCertCommand, StatCertCommand
from rct.manifest_commands import CatManifestCommand, DumpManifestCommand


class RctCLI(CLI):

    def __init__(self):
        commands = [CatCertCommand, CatManifestCommand, StatCertCommand, DumpManifestCommand]
        CLI.__init__(self, commands)


def xstr(value):
    if value is None:
        return ''
    elif isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return str(value)
