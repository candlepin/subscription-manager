#
# Copyright (C) 2005-2008 Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# Jeff Ortel (jortel@redhat.com)
#

import sys
sys.path.append('/usr/share/subscription-manager/repomanagement')

from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE
from repolib import RepoLib

requires_api_version = '2.3'
plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)

def config_hook(conduit):
    try:
        rl = RepoLib()
        rl.update()
    except Exception, ex:
        conduit.error(0, str(ex))